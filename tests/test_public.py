"""Public pages, static assets, 404 and login guards (no session)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestPublicPages:
    def test_landing_page(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert b"Prediction" in r.data

    def test_login_page(self, client):
        r = client.get("/login")
        assert r.status_code == 200
        assert b"Student Login" in r.data

    def test_register_page(self, client):
        r = student_page = client.get("/register")
        assert r.status_code == 200
        assert b"Student Registration" in r.data

    def test_admin_login_page(self, client):
        r = client.get("/admin/login")
        assert r.status_code == 200
        assert b"Admin Login" in r.data


class TestStaticAssets:
    def test_css(self, client):
        r = client.get("/static/css/style.css")
        assert r.status_code == 200
        assert b"navbar" in r.data

    def test_model_comparison_chart(self, client):
        r = client.get("/static/images/performance_model_comparison.png")
        assert r.status_code == 200
        assert r.data[:4] == b"\x89PNG"  # real PNG magic bytes

    def test_confusion_matrix_chart(self, client):
        r = client.get("/static/images/performance_confusion_matrix.png")
        assert r.status_code == 200
        assert r.data[:4] == b"\x89PNG"


class TestAuthGuards:
    def test_dashboard_redirects_to_login(self, client):
        r = client.get("/dashboard")
        assert r.status_code == 302
        assert "/login" in r.headers["Location"]

    def test_admin_redirects_to_admin_login(self, client):
        r = client.get("/admin")
        assert r.status_code == 302
        assert "/admin/login" in r.headers["Location"]

    def test_history_redirects_when_anonymous(self, client):
        r = client.get("/history")
        assert r.status_code == 302
        assert "/login" in r.headers["Location"]


class TestNotFound:
    def test_custom_404_page(self, client):
        r = client.get("/no-such-page")
        assert r.status_code == 404
        assert b"Page not found" in r.data
