"""Admin flow: auth, dashboard, student management, search, delete, analytics."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402


def _unique(prefix):
    return f"{prefix}{str(int(time.time() * 1000))[-9:]}"


class TestAdminAuth:
    def test_wrong_password_rejected(self, client):
        r = client.post("/admin/login",
                        data={"username": "admin", "password": "nope"},
                        follow_redirects=True)
        assert b"Invalid admin credentials" in r.data

    def test_student_cannot_access_admin_pages(self):
        c = app_module.app.test_client()
        c.post("/login", data={"email": "rahul@student.com",
                               "password": "student123"})
        r = c.get("/admin", follow_redirects=True)
        assert b"Unauthorized" in r.data or b"Admin Login" in r.data

    def test_admin_login_succeeds(self, admin_client):
        r = admin_client.get("/admin")
        assert b"Admin Dashboard" in r.data


class TestAdminDashboard:
    def test_stats_cards_render(self, admin_client):
        r = admin_client.get("/admin")
        assert b"Total Students" in r.data
        assert b"Total Predictions" in r.data

    def test_recent_predictions_table(self, admin_client):
        r = admin_client.get("/admin")
        assert b"Recent Predictions" in r.data


class TestStudentManagement:
    def test_students_list_renders(self, admin_client):
        r = admin_client.get("/admin/students")
        assert r.status_code == 200
        assert b"Student Management" in r.data
        assert b"rahul" in r.data.lower()

    def test_search_by_name(self, admin_client):
        r = admin_client.get("/admin/students", query_string={"q": "rahul"})
        assert b"rahul" in r.data.lower()

    def test_search_no_results_message(self, admin_client):
        r = admin_client.get("/admin/students", query_string={"q": "zzzznope"})
        assert b"No students found" in r.data

    def test_student_detail(self, admin_client):
        r = admin_client.get("/admin/students/1")
        assert r.status_code == 200
        assert b"Student:" in r.data

    def test_student_detail_404(self, admin_client):
        r = admin_client.get("/admin/students/999999")
        assert r.status_code == 302  # flashed + redirected to list

    def test_delete_removes_student(self, admin_client):
        # create a victim through the real signup route
        email, roll = _unique("del_") + "@test.com", _unique("PY")
        c = app_module.app.test_client()
        c.post("/register", data={
            "full_name": "Delete Me", "email": email,
            "password": "test123", "confirm_password": "test123",
            "roll_number": roll, "course": "BSc AI & ML",
            "semester": "3", "cgpa": "6.5", "attendance": "70"})
        with app_module.app.app_context():
            student_id = app_module.db_query(
                "SELECT student_id FROM students WHERE roll_number=%s",
                (roll,), one=True)["student_id"]

        r = admin_client.post(
            f"/admin/students/{student_id}/delete", follow_redirects=True)
        assert b"deleted" in r.data.lower()

        with app_module.app.app_context():
            gone = app_module.db_query(
                "SELECT * FROM users WHERE email=%s", (email,), one=True)
            cascade = app_module.db_query(
                "SELECT * FROM students WHERE student_id=%s", (student_id,),
                one=True)
        assert gone is None, "user row must be gone"
        assert cascade is None, "students row must cascade"


class TestAnalytics:
    def test_page_renders(self, admin_client):
        r = admin_client.get("/admin/analytics")
        assert r.status_code == 200
        assert b"Analytics" in r.data

    def test_all_five_charts_referenced(self, admin_client):
        r = admin_client.get("/admin/analytics")
        body = r.data.decode()
        for png in ("analytics_performance_dist.png",
                    "analytics_placement_dist.png",
                    "analytics_attendance_perf.png",
                    "analytics_cgpa_placement.png",
                    "analytics_model_eval.png"):
            assert png in body, f"{png} missing from analytics page"

    def test_charts_actually_exist_on_disk(self):
        import os
        img_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "static", "images")
        for png in ("analytics_performance_dist.png",
                    "analytics_placement_dist.png",
                    "analytics_attendance_perf.png",
                    "analytics_cgpa_placement.png",
                    "analytics_model_eval.png"):
            path = os.path.join(img_dir, png)
            assert os.path.exists(path), f"{png} not found on disk"
            with open(path, "rb") as f:
                assert f.read(4) == b"\x89PNG"


class TestModelMetricsFiles:
    def test_metrics_json_valid_and_complete(self):
        import json
        import os
        model_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "saved_models")
        for name in ("performance_metrics.json", "placement_metrics.json"):
            with open(os.path.join(model_dir, name)) as f:
                data = json.load(f)
            assert "best_algorithm" in data
            assert "Logistic Regression" in data["metrics"]
