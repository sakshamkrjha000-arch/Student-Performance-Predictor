# AI-Based Student Performance & Placement Prediction System

A Flask + MySQL web application that uses machine learning (Scikit-learn)
to estimate a student's **academic performance** (Good / Average /
Needs Improvement) and **placement likelihood** (Placed / Not Placed).

> All predictions are **educational estimates only** and are **not
> guaranteed**.

---

## 1. Introduction

Second-year BSc (AI & ML) academic project. Students register, log in,
and submit academic details through normal HTML forms. Two trained
Scikit-learn models return predictions, which are stored in MySQL along
with their inputs. An admin panel provides student management and
chart-based analytics.

## 2. Problem Statement

Colleges track marks manually and cannot systematically identify
students who need academic help early, nor estimate placement readiness
objectively. This system applies machine learning to routinely
collected academic data to give early, data-driven estimates.

## 3. Objectives

- Predict performance category (Good / Average / Needs Improvement)
- Estimate placement likelihood (Placed / Not Placed + confidence)
- Persist students, records and predictions in MySQL
- Provide admin management and analytics with server-generated charts
- Demonstrate a full ML pipeline: data → cleaning → training →
  evaluation → model selection → deployment in a web app

## 4. Features

- Student register / login / logout (hashed passwords, sessions)
- Dashboard with profile stats and latest predictions
- Performance & placement prediction forms with validation
- Prediction history with stored inputs
- Admin login (separate table), dashboard, student search/management
- Analytics: 5 chart types, all Matplotlib PNGs (zero JavaScript)
- Friendly HTML error pages (404 / 403 / 500)

## 5. Technology Stack

| Layer     | Technology |
|-----------|------------|
| Frontend  | HTML5, CSS3 (no JavaScript anywhere) |
| Backend   | Python 3, Flask 3, Jinja2 templates |
| Database  | MySQL 8 (mysql-connector-python) |
| ML        | Pandas, NumPy, Scikit-learn, Joblib |
| Charts    | Matplotlib (PNG in `static/images/`) |

## 6. System Architecture

```
Browser (HTML forms)
   │  HTTP GET/POST
   ▼
Flask app (app.py)  ── sessions for auth, Jinja2 for pages
   │                └─► saved_models/*.pkl  (Joblib models)
   ▼
mysql-connector  ──►  MySQL: student_prediction_db
   ▲
Matplotlib charts saved to static/images/*.png
```

## 7. Database Design

Six tables in `student_prediction_db` (see `database.sql`):

- **users** — student accounts (hashed passwords, unique email)
- **admins** — separate admin accounts
- **students** — academic profile, FK → users(user_id), CHECK
  constraints on semester/CGPA/attendance
- **performance_records** — inputs of every performance prediction,
  FK → students(student_id)
- **placement_records** — inputs of every placement prediction
- **predictions** — unified results log: type, label, probability,
  JSON of inputs, FK → students(student_id)

All FKs use `ON DELETE CASCADE`, and every table has `created_at`.

## 8. ML Methodology

1. `ml/generate_data.py` creates 600 synthetic rows per dataset
   (no real student data) with a few missing values on purpose.
2. Training scripts load, explore, clean (dedupe, range filter,
   median imputation), and split 80/20 with stratification.
3. Four algorithms are trained and compared:
   **Logistic Regression, Decision Tree, Random Forest, KNN**.
4. Metrics: accuracy, precision, recall, F1 (macro for 3-class),
   confusion matrix; ROC-AUC and curves for placement.
5. The best model by F1 is saved with Joblib to `saved_models/`
   together with feature columns and label names.
6. `app.py` lazy-loads the `.pkl` bundle once and calls
   `predict()` + `predict_proba()` per request.

Achieved on the synthetic datasets (yours will match closely):
Performance — Logistic Regression, macro-F1 **0.967**;
Placement — Logistic Regression, F1 **0.932**, ROC-AUC **0.967**.

## 9. Algorithms Used (one-liners)

- **Logistic Regression** — linear decision boundary via the sigmoid;
  fast, interpretable, probabilistic.
- **Decision Tree** — recursive if/else splits; captures non-linear
  rules; can overfit without depth limits.
- **Random Forest** — many trees on bootstrapped samples + feature
  sampling; more stable than a single tree.
- **KNN** — majority vote among k nearest (standardised) points;
  no real training phase, slower at predict time.

## 10. Installation

```bash
# 1. Python environment (3.10+)
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac

pip install -r requirements.txt
```

## 11. MySQL Setup

```bash
mysql -u root -p
SOURCE database.sql;   # from inside the project folder
```

Then copy `.env.example` to `.env` and set your real credentials:

```
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_password_here
DB_NAME=student_prediction_db
SECRET_KEY=some-long-random-string
```

## 12. Model Training

```bash
python ml/generate_data.py     # create datasets
python ml/train_performance.py # train + evaluate + save + graphs
python ml/train_placement.py
```

## 13. Running Flask

```bash
python app.py
# open http://127.0.0.1:5000
```

Default logins (from database.sql seeds):
- Student — `rahul@student.com` / `student123`
- Admin — `admin` / `admin123`

## 14. Testing

An automated pytest suite lives in `tests/` (62 tests) and covers:
validation helpers, public pages, static assets, auth guards, the full
student flow (login, dashboard, both predictions, invalid-input
handling, history, profile, signup + duplicate rejection), the admin
flow (login, stats, search, delete with cascade check, analytics
charts), and the saved model metrics files.

```bash
python -m pytest            # run the whole suite (~5 s)
python -m pytest -q         # quieter output
python -m pytest -k admin   # just the admin tests
```

The suite uses Flask's test client against the real dev database and
cleans up every student it registers, so it is safe to re-run.

Manual browser checklist:

- Register a new student (try duplicate email → friendly error)
- Login with wrong password → friendly error
- Submit marks of 150 → validation error
- Run both predictions → result page + rows in `predictions`
- Admin login → dashboard counts, search "rahul", delete flow
- Visit `/nope` → custom 404

## 15. Limitations

- Synthetic dataset: metrics are optimistic; real data is messier
- Self-reported inputs can be inaccurate
- No re-training or drift monitoring from the web UI
- Placement outcome in reality depends on many external factors

## 16. Future Scope

- Real anonymised college data; periodic re-training
- Resume parsing and interview feedback as extra features
- Email alerts for "Needs Improvement" students
- Deployment with Gunicorn + Nginx and a cloud MySQL
