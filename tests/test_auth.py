import unittest
from unittest.mock import patch

from werkzeug.security import generate_password_hash

from app import create_app
from services.otp_service import OtpRateLimitError, issue_otp


class AuthRouteTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False})
        self.client = self.app.test_client()

    def test_login_page_hides_sidebar_for_authenticated_user(self):
        with self.client.session_transaction() as session:
            session["user_id"] = 7
            session["username"] = "pixora_user"

        response = self.client.get("/auth/login")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'class="pixora-login-no-sidebar"', response.data)
        self.assertNotIn(b'class="app-sidebar"', response.data)
        self.assertIn(b"Welcome back", response.data)

    def test_login_page_keeps_public_navigation_for_logged_out_user(self):
        response = self.client.get("/auth/login")

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b'class="app-sidebar"', response.data)
        self.assertIn(b'class="topbar"', response.data)

    def test_forgot_password_page_hides_sidebar_for_authenticated_user(self):
        with self.client.session_transaction() as session:
            session["user_id"] = 7
            session["username"] = "pixora_user"

        response = self.client.get("/auth/forgot-password")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'class="pixora-forgot-password-no-sidebar"', response.data)
        self.assertNotIn(b'class="app-sidebar"', response.data)
        self.assertIn(b"Forgot your password?", response.data)

    def test_forgot_password_page_keeps_public_header_for_logged_out_user(self):
        response = self.client.get("/auth/forgot-password")

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b'class="app-sidebar"', response.data)
        self.assertIn(b'class="topbar"', response.data)

    def test_register_page_hides_sidebar_for_authenticated_user(self):
        with self.client.session_transaction() as session:
            session["user_id"] = 7
            session["username"] = "pixora_user"

        response = self.client.get("/auth/register")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'class="pixora-register-no-sidebar"', response.data)
        self.assertNotIn(b'class="app-sidebar"', response.data)
        self.assertIn(b"Create your account", response.data)

    def test_register_page_keeps_public_header_for_logged_out_user(self):
        response = self.client.get("/auth/register")

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b'class="app-sidebar"', response.data)
        self.assertIn(b'class="topbar"', response.data)

    def test_reset_password_page_hides_sidebar_for_authenticated_user(self):
        with self.client.session_transaction() as session:
            session["user_id"] = 7
            session["reset_user_id"] = 7

        response = self.client.get("/auth/reset-password")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'class="pixora-reset-password-no-sidebar"', response.data)
        self.assertNotIn(b'class="app-sidebar"', response.data)
        self.assertIn(b"Choose a new password", response.data)

    def test_reset_password_page_keeps_public_header_for_logged_out_user(self):
        with self.client.session_transaction() as session:
            session["reset_user_id"] = 7

        response = self.client.get("/auth/reset-password")

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b'class="app-sidebar"', response.data)
        self.assertIn(b'class="topbar"', response.data)

    def test_reset_password_without_reset_session_explains_next_step(self):
        response = self.client.get("/auth/reset-password", follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Request a password reset code first", response.data)
        self.assertIn(b'name="email"', response.data)

    def test_login_success_creates_session(self):
        user = {
            "id": 7,
            "username": "pixora_user",
            "password_hash": generate_password_hash("correct-horse"),
            "is_verified": True,
        }
        with patch("routes.auth_routes.user_model.get_by_email", return_value=user):
            response = self.client.post(
                "/auth/login",
                data={"email": "person@example.com", "password": "correct-horse"},
            )
        self.assertEqual(response.status_code, 302)
        with self.client.session_transaction() as session:
            self.assertEqual(session["user_id"], 7)
            self.assertEqual(session["username"], "pixora_user")

    def test_bad_login_does_not_create_session(self):
        with patch("routes.auth_routes.user_model.get_by_email", return_value=None):
            response = self.client.post(
                "/auth/login",
                data={"email": "person@example.com", "password": "incorrect"},
            )
        self.assertEqual(response.status_code, 200)
        with self.client.session_transaction() as session:
            self.assertNotIn("user_id", session)

    def test_registration_redirects_to_otp_verification(self):
        with (
            patch("routes.auth_routes.user_model.get_by_email", return_value=None),
            patch("routes.auth_routes.user_model.get_by_username", return_value=None),
            patch("routes.auth_routes.user_model.create_user", return_value=7),
            patch("routes.auth_routes._send_code"),
        ):
            response = self.client.post(
                "/auth/register",
                data={
                    "full_name": "Test User",
                    "username": "test_user",
                    "email": "person@example.com",
                    "password": "correct-horse",
                },
            )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/auth/verify")

    def test_feed_requires_login(self):
        response = self.client.get("/feed")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/auth/login", response.headers["Location"])

    def test_otp_issue_obeys_cooldown_without_saving_another_code(self):
        from datetime import datetime, timedelta

        with (
            patch(
                "services.otp_service.get_otp_request_stats",
                return_value={
                    "request_count": 1,
                    "latest_request_at": datetime.now() - timedelta(seconds=20),
                },
            ),
            patch("services.otp_service.log_otp_request") as log_request,
            patch("services.otp_service.save_otp") as save_otp,
        ):
            with self.assertRaises(OtpRateLimitError):
                issue_otp(7)

        log_request.assert_not_called()
        save_otp.assert_not_called()


if __name__ == "__main__":
    unittest.main()
