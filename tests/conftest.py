"""
tests/conftest.py
Shared pytest fixtures. The real app is imported (with the real dev MySQL
database) and every test runs through Flask's test client, exactly like the
curl smoke tests, so the suite exercises the true routes + DB.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402

STUDENT_EMAIL = "rahul@student.com"
STUDENT_PASSWORD = "student123"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

PERF_DATA = {
    "attendance_pct": "88", "assignment_marks": "82", "internal_marks": "79",
    "prev_semester_marks": "84", "study_hours": "5.5",
    "assignments_completed": "22", "participation_score": "8.5",
}
PLACE_DATA = {
    "cgpa": "8.2", "attendance": "86", "technical_score": "76",
    "communication_score": "71", "projects_completed": "5",
    "internship_months": "2", "certifications": "2", "aptitude_score": "74",
}


# ---------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------
@pytest.fixture(scope="session")
def app():
    yield app_module.app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture(scope="session")
def student_client():
    """One client logged in as the seeded student for the whole session."""
    c = app_module.app.test_client()
    r = c.post("/login", data={"email": STUDENT_EMAIL,
                               "password": STUDENT_PASSWORD})
    assert r.status_code == 302, "seeded student login failed - check DB"
    return c


@pytest.fixture(scope="session")
def admin_client():
    """One client logged in as the seeded admin for the whole session."""
    c = app_module.app.test_client()
    r = c.post("/admin/login", data={"username": ADMIN_USERNAME,
                                     "password": ADMIN_PASSWORD})
    assert r.status_code == 302, "seeded admin login failed - check DB"
    return c


@pytest.fixture()
def new_student():
    """
    Register a unique student through the real signup route and yield
    (client, email). If signup fails, the test itself will show why.
    """
    import time
    stamp = str(int(time.time() * 1000))[-9:]
    email = f"pytest_{stamp}@test.com"
    roll = f"PY{stamp}"
    payload = {
        "full_name": "Pytest Student", "email": email,
        "password": "test123", "confirm_password": "test123",
        "roll_number": roll, "course": "BSc AI & ML",
        "semester": "4", "cgpa": "7.5", "attendance": "80",
    }
    c = app_module.app.test_client()
    r = c.post("/register", data=payload, follow_redirects=False)
    assert r.status_code == 302, f"signup failed: {r.status_code}"
    yield c, email
    _delete_student_by_email(email)


@pytest.fixture(autouse=True)
def _rollback_flash():
    """Placeholder hook - individual tests clean up via _delete_student_by_email."""
    yield


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------
def _delete_student_by_email(email):
    try:
        with app_module.app.app_context():
            app_module.db_execute(
                "DELETE FROM users WHERE email = %s", (email,))
    except Exception as exc:  # pragma: no cover - best effort cleanup
        print(f"[cleanup] could not delete {email}: {exc}")
