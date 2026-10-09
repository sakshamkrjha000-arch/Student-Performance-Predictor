"""
app.py
AI-Based Student Performance & Placement Prediction System
Flask application: routes, authentication, MySQL access, ML predictions.

Run:  python app.py      (then open http://127.0.0.1:5000)
"""
import json
import os
from functools import wraps

import mysql.connector
import joblib
from flask import (Flask, flash, g, redirect, render_template, request,
                   session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash
from config import Config
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------
# App + configuration
# ---------------------------------------------------------------
app = Flask(__name__)
app.config.from_object(Config)
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "student_prediction_db"),
}

MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "saved_models")
PERFORMANCE_MODEL_PATH = os.path.join(MODEL_DIR, "performance_model.pkl")
PLACEMENT_MODEL_PATH = os.path.join(MODEL_DIR, "placement_model.pkl")

_models = {}


def get_model(kind):
    """Lazy-load a saved ML model once, then reuse it."""
    if kind not in _models:
        path = (PERFORMANCE_MODEL_PATH if kind == "performance"
                else PLACEMENT_MODEL_PATH)
        if not os.path.exists(path):
            return None
        try:
            _models[kind] = joblib.load(path)
        except Exception as exc:
            print(f"[model] failed to load {path}: {exc}")
            return None
    return _models[kind]


# ---------------------------------------------------------------
# Database helpers (mysql-connector, parameterised -> no SQL injection)
# ---------------------------------------------------------------
def get_db():
    if "db" not in g:
        g.db = mysql.connector.connect(**DB_CONFIG)
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def db_query(sql, params=(), one=False):
    cur = get_db().cursor(dictionary=True)
    try:
        cur.execute(sql, params)
        rows = cur.fetchall()
        return (rows[0] if rows else None) if one else rows
    finally:
        cur.close()


def db_execute(sql, params=()):
    db = get_db()
    cur = db.cursor()
    try:
        cur.execute(sql, params)
        db.commit()
        return cur.lastrowid
    except Exception:
        db.rollback()
        raise
    finally:
        cur.close()


# ---------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------
def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "error")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("role") != "admin":
            flash("Unauthorized - admin access only.", "error")
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)
    return wrapped


def current_student():
    """Fetch the logged-in student joined with their academic profile."""
    return db_query(
        """SELECT u.user_id, u.full_name, u.email,
                  s.student_id, s.roll_number, s.course, s.semester,
                  s.cgpa, s.attendance
           FROM users u LEFT JOIN students s ON s.user_id = u.user_id
           WHERE u.user_id = %s""",
        (session["user_id"],), one=True)


# ---------------------------------------------------------------
# Input validation helpers
# ---------------------------------------------------------------
def to_float(value, lo, hi):
    """Convert a form field to float inside [lo, hi], else None."""
    try:
        v = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return v if lo <= v <= hi else None


def to_int(value, lo, hi):
    try:
        v = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    return v if lo <= v <= hi else None


def valid_email(email):
    if not 5 <= len(email) <= 120 or "@" not in email:
        return False
    local, _, domain = email.partition("@")
    return bool(local and domain and "." in domain
                and not domain.startswith(".")
                and not domain.endswith(".")
                and ".." not in domain)


# ===============================================================
# PUBLIC ROUTES
# ===============================================================
@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = (request.form.get("full_name") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        confirm = request.form.get("confirm_password") or ""
        roll_number = (request.form.get("roll_number") or "").strip()
        course = (request.form.get("course") or "").strip()
        semester = to_int(request.form.get("semester"), 1, 8)
        cgpa = to_float(request.form.get("cgpa"), 0, 10)
        attendance = to_float(request.form.get("attendance"), 0, 100)

        errors = []
        if len(full_name) < 3:
            errors.append("Full name must be at least 3 characters.")
        if not valid_email(email):
            errors.append("Please enter a valid email address.")
        if len(password) < 6:
            errors.append("Password must be at least 6 characters.")
        if password != confirm:
            errors.append("Passwords do not match.")
        if not roll_number:
            errors.append("Roll number is required.")
        if not course:
            errors.append("Course is required.")
        if semester is None:
            errors.append("Semester must be a number between 1 and 8.")
        if cgpa is None:
            errors.append("CGPA must be a number between 0 and 10.")
        if attendance is None:
            errors.append("Attendance must be between 0 and 100.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("register.html", form=request.form)

        try:
            existing = db_query("SELECT user_id FROM users WHERE email = %s",
                                (email,), one=True)
            if existing:
                flash("Email already registered. Please log in instead.",
                      "error")
                return redirect(url_for("login"))

            existing_roll = db_query(
                "SELECT student_id FROM students WHERE roll_number = %s",
                (roll_number,), one=True)
            if existing_roll:
                flash("Roll number already exists.", "error")
                return render_template("register.html", form=request.form)

            user_id = db_execute(
                "INSERT INTO users (full_name, email, password_hash) "
                "VALUES (%s, %s, %s)",
                (full_name, email, generate_password_hash(password)))
            db_execute(
                """INSERT INTO students
                       (user_id, roll_number, course, semester, cgpa,
                        attendance)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (user_id, roll_number, course, semester, cgpa, attendance))
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for("login"))
        except mysql.connector.Error as exc:
            flash(f"Database error: {exc.msg}", "error")
    return render_template("register.html", form={})


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        if not email or not password:
            flash("Please fill in both fields.", "error")
            return render_template("login.html")
        try:
            user = db_query("SELECT * FROM users WHERE email = %s",
                            (email,), one=True)
        except mysql.connector.Error:
            flash("Database connection problem. Is MySQL running?",
                  "error")
            return render_template("login.html")
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["user_id"]
            session["full_name"] = user["full_name"]
            session["role"] = "student"
            return redirect(url_for("dashboard"))
        flash("Invalid email or password.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


# ===============================================================
# STUDENT ROUTES
# ===============================================================
@app.route("/dashboard")
@login_required
def dashboard():
    student = current_student()
    if not student or not student["student_id"]:
        flash("Student profile missing. Please contact the admin.", "error")
        return redirect(url_for("logout"))

    history = db_query(
        """SELECT * FROM predictions
           WHERE student_id = %s
           ORDER BY created_at DESC LIMIT 10""",
        (student["student_id"],))
    latest_perf = next((h for h in history
                        if h["prediction_type"] == "performance"), None)
    latest_place = next((h for h in history
                         if h["prediction_type"] == "placement"), None)
    return render_template("dashboard.html", student=student,
                           latest_perf=latest_perf, latest_place=latest_place,
                           history=history)


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    student = current_student()
    if request.method == "POST":
        course = (request.form.get("course") or "").strip()
        semester = to_int(request.form.get("semester"), 1, 8)
        cgpa = to_float(request.form.get("cgpa"), 0, 10)
        attendance = to_float(request.form.get("attendance"), 0, 100)
        if not course or semester is None or cgpa is None \
                or attendance is None:
            flash("Please correct the highlighted fields "
                  "(semester 1-8, CGPA 0-10, attendance 0-100).", "error")
        else:
            db_execute(
                """UPDATE students SET course=%s, semester=%s,
                       cgpa=%s, attendance=%s WHERE user_id=%s""",
                (course, semester, cgpa, attendance, session["user_id"]))
            flash("Profile updated successfully.", "success")
            student = current_student()
    return render_template("profile.html", student=student)


@app.route("/performance", methods=["GET", "POST"])
@login_required
def performance():
    """Performance prediction form + result."""
    if request.method == "POST":
        values = {
            "attendance_pct": to_float(request.form.get("attendance_pct"),
                                       0, 100),
            "assignment_marks": to_float(request.form.get("assignment_marks"),
                                         0, 100),
            "internal_marks": to_float(request.form.get("internal_marks"),
                                       0, 100),
            "prev_semester_marks": to_float(
                request.form.get("prev_semester_marks"), 0, 100),
            "study_hours": to_float(request.form.get("study_hours"), 0, 16),
            "assignments_completed": to_int(
                request.form.get("assignments_completed"), 0, 50),
            "participation_score": to_float(
                request.form.get("participation_score"), 0, 10),
        }
        bad = [k for k, v in values.items() if v is None]
        if bad:
            flash("Invalid input in: " + ", ".join(bad) +
                  ". Please check the allowed ranges and try again.", "error")
            return render_template("performance.html", form=request.form)

        bundle = get_model("performance")
        if bundle is None:
            flash("ML model not found. Run: python ml/train_performance.py",
                  "error")
            return render_template("performance.html", form=request.form)

        X = [[values[c] for c in bundle["feature_columns"]]]
        try:
            pred_idx = int(bundle["model"].predict(X)[0])
            proba = bundle["model"].predict_proba(X)[0]
            label = bundle["label_names"][pred_idx]
            confidence = float(proba[pred_idx])
        except Exception as exc:
            flash(f"Prediction failed: {exc}", "error")
            return render_template("performance.html", form=request.form)

        student = current_student()
        inputs_json = json.dumps(values, sort_keys=True)
        try:
            db_execute(
                """INSERT INTO performance_records
                       (student_id, attendance_pct, assignment_marks,
                        internal_marks, prev_semester_marks, study_hours,
                        assignments_completed, participation_score)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                (student["student_id"], values["attendance_pct"],
                 values["assignment_marks"], values["internal_marks"],
                 values["prev_semester_marks"], values["study_hours"],
                 values["assignments_completed"],
                 values["participation_score"]))
            db_execute(
                """INSERT INTO predictions
                       (student_id, prediction_type, result_label,
                        probability, inputs_json)
                   VALUES (%s,'performance',%s,%s,%s)""",
                (student["student_id"], label, round(confidence, 4),
                 inputs_json))
        except mysql.connector.Error as exc:
            flash(f"Could not save record: {exc.msg}", "error")

        return render_template("result.html",
                               kind="performance", label=label,
                               confidence=round(confidence * 100, 1),
                               values=values, student=student,
                               disclaimer=("This performance prediction is "
                                           "an educational estimate only "
                                           "and is NOT guaranteed."))
    return render_template("performance.html", form={})


@app.route("/placement", methods=["GET", "POST"])
@login_required
def placement():
    """Placement prediction form + result."""
    if request.method == "POST":
        values = {
            "cgpa": to_float(request.form.get("cgpa"), 0, 10),
            "attendance": to_float(request.form.get("attendance"), 0, 100),
            "technical_score": to_float(
                request.form.get("technical_score"), 0, 100),
            "communication_score": to_float(
                request.form.get("communication_score"), 0, 100),
            "projects_completed": to_int(
                request.form.get("projects_completed"), 0, 30),
            "internship_months": to_int(
                request.form.get("internship_months"), 0, 24),
            "certifications": to_int(request.form.get("certifications"),
                                     0, 20),
            "aptitude_score": to_float(request.form.get("aptitude_score"),
                                       0, 100),
        }
        bad = [k for k, v in values.items() if v is None]
        if bad:
            flash("Invalid input in: " + ", ".join(bad) +
                  ". Please check the allowed ranges and try again.", "error")
            return render_template("placement.html", form=request.form)

        bundle = get_model("placement")
        if bundle is None:
            flash("ML model not found. Run: python ml/train_placement.py",
                  "error")
            return render_template("placement.html", form=request.form)

        X = [[values[c] for c in bundle["feature_columns"]]]
        try:
            pred_idx = int(bundle["model"].predict(X)[0])
            proba = bundle["model"].predict_proba(X)[0]
            label = bundle["label_names"][pred_idx]
            confidence = float(proba[pred_idx])
        except Exception as exc:
            flash(f"Prediction failed: {exc}", "error")
            return render_template("placement.html", form=request.form)

        student = current_student()
        inputs_json = json.dumps(values, sort_keys=True)
        try:
            db_execute(
                """INSERT INTO placement_records
                       (student_id, cgpa, attendance, technical_score,
                        communication_score, projects_completed,
                        internship_months, certifications, aptitude_score)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (student["student_id"], values["cgpa"], values["attendance"],
                 values["technical_score"], values["communication_score"],
                 values["projects_completed"], values["internship_months"],
                 values["certifications"], values["aptitude_score"]))
            db_execute(
                """INSERT INTO predictions
                       (student_id, prediction_type, result_label,
                        probability, inputs_json)
                   VALUES (%s,'placement',%s,%s,%s)""",
                (student["student_id"], label, round(confidence, 4),
                 inputs_json))
        except mysql.connector.Error as exc:
            flash(f"Could not save record: {exc.msg}", "error")

        likelihood = round(confidence * 100, 1)
        return render_template("result.html",
                               kind="placement",
                               label=("Placed" if label == "Placed"
                                      else "Not Placed"),
                               confidence=likelihood,
                               values=values, student=student,
                               disclaimer=("This placement estimate does NOT "
                                           "guarantee employment. Actual "
                                           "outcomes depend on company "
                                           "criteria and interviews."))
    return render_template("placement.html", form={})


@app.route("/history")
@login_required
def history():
    student = current_student()
    rows = db_query(
        """SELECT * FROM predictions WHERE student_id = %s
           ORDER BY created_at DESC LIMIT 100""",
        (student["student_id"],))
    # decode the stored input JSON so the table can show the details
    for r in rows:
        try:
            r["inputs"] = json.loads(r["inputs_json"] or "{}")
        except json.JSONDecodeError:
            r["inputs"] = {}
    return render_template("history.html", student=student, rows=rows)


# ===============================================================
# ADMIN ROUTES
# ===============================================================
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        try:
            admin = db_query("SELECT * FROM admins WHERE username = %s",
                             (username,), one=True)
        except mysql.connector.Error:
            flash("Database connection problem. Is MySQL running?", "error")
            return render_template("admin/login.html")
        if admin and check_password_hash(admin["password_hash"], password):
            session.clear()
            session["admin_id"] = admin["admin_id"]
            session["full_name"] = admin["username"]
            session["role"] = "admin"
            return redirect(url_for("admin_dashboard"))
        flash("Invalid admin credentials.", "error")
    return render_template("admin/login.html")


@app.route("/admin")
@admin_required
def admin_dashboard():
    stats = {
        "students": db_query("SELECT COUNT(*) AS c FROM students",
                             one=True)["c"],
        "users": db_query("SELECT COUNT(*) AS c FROM users", one=True)["c"],
        "predictions": db_query("SELECT COUNT(*) AS c FROM predictions",
                                one=True)["c"],
        "placed": db_query(
            """SELECT COUNT(*) AS c FROM predictions
               WHERE prediction_type='placement' AND result_label='Placed'""",
            one=True)["c"],
    }
    recent = db_query(
        """SELECT p.*, s.roll_number, u.full_name
           FROM predictions p
           JOIN students s ON s.student_id = p.student_id
           JOIN users u ON u.user_id = s.user_id
           ORDER BY p.created_at DESC LIMIT 15""")
    return render_template("admin/dashboard.html", stats=stats,
                           recent=recent)


@app.route("/admin/students", methods=["GET", "POST"])
@admin_required
def admin_students():
    q = (request.args.get("q") or request.form.get("q") or "").strip()
    if q:
        like = f"%{q}%"
        students = db_query(
            """SELECT s.*, u.full_name, u.email
               FROM students s JOIN users u ON u.user_id = s.user_id
               WHERE u.full_name LIKE %s OR u.email LIKE %s
                  OR s.roll_number LIKE %s OR s.course LIKE %s
               ORDER BY s.student_id DESC""",
            (like, like, like, like))
    else:
        students = db_query(
            """SELECT s.*, u.full_name, u.email
               FROM students s JOIN users u ON u.user_id = s.user_id
               ORDER BY s.student_id DESC""")
    return render_template("admin/students.html", students=students, q=q)


@app.route("/admin/students/<int:student_id>")
@admin_required
def admin_student_detail(student_id):
    student = db_query(
        """SELECT s.*, u.full_name, u.email
           FROM students s JOIN users u ON u.user_id = s.user_id
           WHERE s.student_id = %s""", (student_id,), one=True)
    if not student:
        flash("Student not found.", "error")
        return redirect(url_for("admin_students"))
    preds = db_query(
        """SELECT * FROM predictions WHERE student_id = %s
           ORDER BY created_at DESC""", (student_id,))
    return render_template("admin/student_detail.html", student=student,
                           preds=preds)


@app.route("/admin/students/<int:student_id>/delete", methods=["POST"])
@admin_required
def admin_student_delete(student_id):
    try:
        # remove the login account; students row cascades
        db_execute("DELETE FROM users WHERE user_id = "
                   "(SELECT user_id FROM students WHERE student_id = %s)",
                   (student_id,))
        flash("Student record deleted.", "success")
    except mysql.connector.Error as exc:
        flash(f"Delete failed: {exc.msg}", "error")
    return redirect(url_for("admin_students"))


@app.route("/admin/analytics")
@admin_required
def admin_analytics():
    """Read numbers from MySQL, draw charts with Matplotlib, show PNGs."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    image_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "static", "images")
    os.makedirs(image_dir, exist_ok=True)

    # ---- 1. performance distribution ----
    perf = db_query(
        """SELECT result_label, COUNT(*) AS c FROM predictions
           WHERE prediction_type='performance'
           GROUP BY result_label""")
    labels = [r["result_label"] for r in perf] or ["No data"]
    counts = [r["c"] for r in perf] or [0]
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(labels, counts, color=["#e53935", "#fdd835", "#43a047"][:len(counts)])
    ax.set_title("Performance Prediction Distribution")
    ax.set_ylabel("Count")
    fig.tight_layout()
    fig.savefig(os.path.join(image_dir, "analytics_performance_dist.png"),
                dpi=130)
    plt.close(fig)

    # ---- 2. placement distribution ----
    place = db_query(
        """SELECT result_label, COUNT(*) AS c FROM predictions
           WHERE prediction_type='placement' GROUP BY result_label""")
    labels = [r["result_label"] for r in place] or ["No data"]
    counts = [r["c"] for r in place] or [0]
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(labels, counts, color=["#43a047", "#e53935"][:len(counts)])
    ax.set_title("Placement Prediction Distribution")
    ax.set_ylabel("Count")
    fig.tight_layout()
    fig.savefig(os.path.join(image_dir, "analytics_placement_dist.png"),
                dpi=130)
    plt.close(fig)

    # ---- 3. attendance vs performance ----
    att_rows = db_query(
        """SELECT attendance_pct, assignment_marks, internal_marks
           FROM performance_records ORDER BY perf_id DESC LIMIT 200""")
    if att_rows:
        att = [float(r["attendance_pct"]) for r in att_rows]
        marks = [float(r["internal_marks"]) for r in att_rows]
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.scatter(att, marks, alpha=0.6, s=18, color="#1e88e5")
        ax.set_xlabel("Attendance %")
        ax.set_ylabel("Internal Marks")
        ax.set_title("Attendance vs Internal Marks")
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(os.path.join(image_dir,
                                 "analytics_attendance_perf.png"), dpi=130)
        plt.close(fig)

    # ---- 4. CGPA vs placement ----
    cg_rows = db_query(
        """SELECT pr.cgpa, pr.technical_score
           FROM placement_records pr ORDER BY pr.place_id DESC LIMIT 200""")
    if cg_rows:
        cgpa = [float(r["cgpa"]) for r in cg_rows]
        tech = [float(r["technical_score"]) for r in cg_rows]
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.scatter(cgpa, tech, alpha=0.6, s=18, color="#8e24aa")
        ax.set_xlabel("CGPA")
        ax.set_ylabel("Technical Score")
        ax.set_title("CGPA vs Technical Score (Placement Records)")
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(os.path.join(image_dir, "analytics_cgpa_placement.png"),
                    dpi=130)
        plt.close(fig)

    # ---- 5. model evaluation graph (training results, from metrics json) --
    try:
        with open(os.path.join(MODEL_DIR,
                               "performance_metrics.json")) as f:
            perf_metrics = json.load(f)
        algos = list(perf_metrics["metrics"].keys())
        f1s = [perf_metrics["metrics"][a]["f1"] for a in algos]
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.bar(algos, f1s, color="#00897b")
        ax.set_ylim(0, 1.05)
        ax.set_ylabel("Macro F1")
        ax.set_title("Model Evaluation - Performance (Test F1)")
        fig.tight_layout()
        fig.savefig(os.path.join(image_dir, "analytics_model_eval.png"),
                    dpi=130)
        plt.close(fig)
    except (OSError, json.JSONDecodeError, KeyError):
        pass

    perf_metrics = json.load(open(os.path.join(MODEL_DIR,
                                               "performance_metrics.json"))) \
        if os.path.exists(os.path.join(MODEL_DIR,
                                       "performance_metrics.json")) else None
    place_metrics = json.load(open(os.path.join(MODEL_DIR,
                                                "placement_metrics.json"))) \
        if os.path.exists(os.path.join(MODEL_DIR,
                                       "placement_metrics.json")) else None
    return render_template("admin/analytics.html",
                           perf_metrics=perf_metrics,
                           place_metrics=place_metrics)


# ===============================================================
# ERROR HANDLERS - friendly pages instead of stack traces
# ===============================================================
@app.errorhandler(404)
def not_found(exc):
    return render_template("errors/404.html"), 404


@app.errorhandler(403)
def forbidden(exc):
    return render_template("errors/403.html"), 403


@app.errorhandler(500)
def server_error(exc):
    try:
        get_db().rollback()
    except Exception:
        pass
    return render_template("errors/500.html"), 500


@app.errorhandler(mysql.connector.Error)
def db_error(exc):
    flash(f"Database error: {getattr(exc, 'msg', exc)}", "error")
    return render_template("errors/500.html"), 500


# ---------------------------------------------------------------
    # ---- Bind so the app accepts external requests on a cloud host ----
if __name__ == "__main__":
    # Bind so the app accepts external requests on a cloud host
    app.run(
        debug=False,
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "5000")),
    )
