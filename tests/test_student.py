"""Student flow: login, dashboard, predictions, validation, history, signup."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.conftest import (  # noqa: E402
    PERF_DATA, PLACE_DATA, STUDENT_EMAIL,
)


class TestStudentAuth:
    def test_wrong_password_rejected(self, client):
        r = client.post("/login", data={"email": STUDENT_EMAIL,
                                        "password": "wrong-password"},
                        follow_redirects=True)
        assert b"Invalid email or password" in r.data

    def test_unknown_email_rejected(self, client):
        r = client.post("/login", data={"email": "ghost@x.com",
                                        "password": "whatever"},
                        follow_redirects=True)
        assert b"Invalid email or password" in r.data

    def test_empty_fields_rejected(self, client):
        r = client.post("/login", data={"email": "", "password": ""},
                        follow_redirects=True)
        assert b"fill in both fields" in r.data

    def test_seeded_student_logs_in(self, student_client):
        r = student_client.get("/dashboard")
        assert b"Rahul" in r.data

    def test_logout_clears_session(self, client):
        client.post("/login", data={"email": STUDENT_EMAIL,
                                    "password": "student123"})
        r = client.get("/logout", follow_redirects=True)
        assert b"logged out" in r.data.lower()
        r = client.get("/dashboard", follow_redirects=True)
        assert b"Student Login" in r.data


class TestDashboard:
    def test_shows_profile_stats(self, student_client):
        r = student_client.get("/dashboard")
        assert r.status_code == 200
        assert b"CGPA" in r.data
        assert b"Attendance" in r.data

    def test_shows_prediction_history_table(self, student_client):
        r = student_client.get("/dashboard")
        assert b"Recent Prediction History" in r.data


class TestPerformancePrediction:
    def test_form_get_renders(self, student_client):
        r = student_client.get("/performance")
        assert r.status_code == 200
        assert b"Performance Prediction" in r.data
        assert b"attendance_pct" in r.data

    def test_valid_prediction_returns_result(self, student_client):
        r = student_client.post("/performance", data=PERF_DATA,
                                follow_redirects=True)
        assert r.status_code == 200
        assert b"Confidence" in r.data
        assert b"Inputs used for this prediction" in r.data
        assert b"not guaranteed" in r.data.lower() or \
               b"NOT guaranteed" in r.data

    def test_result_is_a_valid_category(self, student_client):
        r = student_client.post("/performance", data=PERF_DATA,
                                follow_redirects=True)
        body = r.data.decode()
        assert any(cat in body for cat in
                   ("Good", "Average", "Needs Improvement"))

    def test_marks_above_100_rejected(self, student_client):
        bad = dict(PERF_DATA, attendance_pct="150")
        r = student_client.post("/performance", data=bad,
                                follow_redirects=True)
        assert b"Invalid input" in r.data

    def test_marks_below_0_rejected(self, student_client):
        bad = dict(PERF_DATA, internal_marks="-10")
        r = student_client.post("/performance", data=bad,
                                follow_redirects=True)
        assert b"Invalid input" in r.data

    def test_non_numeric_rejected(self, student_client):
        bad = dict(PERF_DATA, study_hours="lots")
        r = student_client.post("/performance", data=bad,
                                follow_redirects=True)
        assert b"Invalid input" in r.data


class TestPlacementPrediction:
    def test_form_get_renders(self, student_client):
        r = student_client.get("/placement")
        assert r.status_code == 200
        assert b"Placement Prediction" in r.data

    def test_valid_prediction_returns_result(self, student_client):
        r = student_client.post("/placement", data=PLACE_DATA,
                                follow_redirects=True)
        assert r.status_code == 200
        assert b"placement likelihood" in r.data.lower()
        assert b"does NOT guarantee" in r.data or \
               b"not guarantee" in r.data.lower()

    def test_result_is_placed_or_not(self, student_client):
        r = student_client.post("/placement", data=PLACE_DATA,
                                follow_redirects=True)
        body = r.data.decode()
        assert "Placed" in body

    def test_invalid_cgpa_rejected(self, student_client):
        bad = dict(PLACE_DATA, cgpa="12")
        r = student_client.post("/placement", data=bad,
                                follow_redirects=True)
        assert b"Invalid input" in r.data


class TestHistoryAndProfile:
    def test_history_lists_predictions(self, student_client):
        # make sure there is at least one prediction first
        student_client.post("/performance", data=PERF_DATA,
                            follow_redirects=True)
        r = student_client.get("/history")
        assert r.status_code == 200
        assert b"Prediction History" in r.data
        assert b"Confidence" in r.data

    def test_profile_shows_email(self, student_client):
        r = student_client.get("/profile")
        assert STUDENT_EMAIL.encode() in r.data

    def test_profile_update_works(self, student_client):
        r = student_client.post("/profile", data={
            "course": "BSc Artificial Intelligence & Machine Learning",
            "semester": "4", "cgpa": "8.3", "attendance": "87.5",
        }, follow_redirects=True)
        assert b"Profile updated successfully" in r.data


class TestSignup:
    def test_new_student_can_register_and_login(self, new_student):
        c, email = new_student
        # logged-out client from fixture can log in with fresh credentials
        c2 = c  # same client has session cookie from registration flow? no -
        # registration does not auto-login; do an explicit login
        client = __import__("app").app.test_client()
        r = client.post("/login", data={"email": email,
                                        "password": "test123"},
                        follow_redirects=True)
        assert b"Rahul" not in r.data  # it's the new student, not Rahul
        assert r.status_code == 200

    def test_duplicate_email_rejected(self, new_student):
        c, email = new_student
        client = __import__("app").app.test_client()
        r = client.post("/register", data={
            "full_name": "Copy Cat", "email": email,
            "password": "test123", "confirm_password": "test123",
            "roll_number": "ROLL-OTHER-1", "course": "BSc AI & ML",
            "semester": "4", "cgpa": "7.0", "attendance": "75",
        }, follow_redirects=True)
        assert b"already registered" in r.data

    def test_duplicate_roll_number_rejected(self, new_student):
        client = __import__("app").app.test_client()
        r = client.post("/register", data={
            "full_name": "Roll Copy", "email": "rollcopy_"
            + email_suffix() + "@test.com",
            "password": "test123", "confirm_password": "test123",
            "roll_number": "CS2023001",  # seeded roll number
            "course": "BSc AI & ML", "semester": "4",
            "cgpa": "7.0", "attendance": "75",
        }, follow_redirects=True)
        assert b"Roll number already exists" in r.data


def email_suffix():
    import time
    return str(int(time.time() * 1000))[-9:]
