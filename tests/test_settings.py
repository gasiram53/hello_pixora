import unittest
from unittest.mock import patch

from app import create_app


class PrivacySettingsTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False})
        self.client = self.app.test_client()
        with self.client.session_transaction() as session:
            session["user_id"] = 3

    def test_private_account_setting_is_saved(self):
        with patch("routes.settings_routes.execute") as execute:
            response = self.client.post(
                "/settings/privacy", data={"is_private": "1"}
            )

        self.assertEqual(response.status_code, 302)
        execute.assert_called_once_with(
            "UPDATE users SET is_private = %s WHERE id = %s",
            (True, 3),
        )

    def test_unchecked_privacy_setting_restores_public_account(self):
        with patch("routes.settings_routes.execute") as execute:
            response = self.client.post("/settings/privacy", data={})

        self.assertEqual(response.status_code, 302)
        execute.assert_called_once_with(
            "UPDATE users SET is_private = %s WHERE id = %s",
            (False, 3),
        )

    def test_account_settings_include_username_and_password_forms(self):
        account = {
            "username": "pixora_user",
            "email": "user@example.com",
            "password_hash": "hashed-password",
            "is_private": False,
        }
        with patch("routes.settings_routes.get_user_for_id", return_value=account):
            response = self.client.get("/settings/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'name="username"', response.data)
        self.assertIn(b'name="new_password"', response.data)
        self.assertIn(b"Update username", response.data)
        self.assertIn(b"Update password", response.data)
        self.assertIn(b'action="/auth/logout"', response.data)
        self.assertIn(b">Log out</button>", response.data)
        self.assertIn(b"Settings", response.data)

    def test_settings_logout_clears_session(self):
        response = self.client.post("/auth/logout")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/auth/login")
        with self.client.session_transaction() as session:
            self.assertNotIn("user_id", session)

    def test_username_change_requires_current_password_and_updates_session(self):
        account = {
            "username": "old_name",
            "password_hash": "hashed-password",
        }
        with (
            patch("routes.settings_routes.get_user_for_id", return_value=account),
            patch("routes.settings_routes.check_password_hash", return_value=True),
            patch("routes.settings_routes.user_model.get_by_username", return_value=None),
            patch("routes.settings_routes.user_model.update_username") as update_username,
        ):
            response = self.client.post(
                "/settings/username",
                data={"username": "New_Name", "current_password": "correct-password"},
            )

        self.assertEqual(response.status_code, 302)
        update_username.assert_called_once_with(3, "new_name")
        with self.client.session_transaction() as session:
            self.assertEqual(session["username"], "new_name")

    def test_username_change_rejects_invalid_username(self):
        account = {"username": "old_name", "password_hash": "hashed-password"}
        with (
            patch("routes.settings_routes.get_user_for_id", return_value=account),
            patch("routes.settings_routes.user_model.update_username") as update_username,
        ):
            response = self.client.post(
                "/settings/username",
                data={"username": "not valid!", "current_password": "correct-password"},
            )

        self.assertEqual(response.status_code, 302)
        update_username.assert_not_called()
        with self.client.session_transaction() as session:
            self.assertTrue(
                any(
                    message.startswith("Username must be 3")
                    for _, message in session["_flashes"]
                )
            )

    def test_username_change_rejects_taken_username(self):
        account = {"username": "old_name", "password_hash": "hashed-password"}
        with (
            patch("routes.settings_routes.get_user_for_id", return_value=account),
            patch("routes.settings_routes.check_password_hash", return_value=True),
            patch(
                "routes.settings_routes.user_model.get_by_username",
                return_value={"id": 8, "username": "new_name"},
            ),
            patch("routes.settings_routes.user_model.update_username") as update_username,
        ):
            response = self.client.post(
                "/settings/username",
                data={"username": "new_name", "current_password": "correct-password"},
            )

        self.assertEqual(response.status_code, 302)
        update_username.assert_not_called()
        with self.client.session_transaction() as session:
            self.assertIn(
                "That username is already taken.",
                [message for _, message in session["_flashes"]],
            )

    def test_username_change_rejects_wrong_current_password(self):
        account = {"username": "old_name", "password_hash": "hashed-password"}
        with (
            patch("routes.settings_routes.get_user_for_id", return_value=account),
            patch("routes.settings_routes.check_password_hash", return_value=False),
            patch("routes.settings_routes.user_model.get_by_username") as get_by_username,
            patch("routes.settings_routes.user_model.update_username") as update_username,
        ):
            response = self.client.post(
                "/settings/username",
                data={"username": "new_name", "current_password": "wrong-password"},
            )

        self.assertEqual(response.status_code, 302)
        get_by_username.assert_not_called()
        update_username.assert_not_called()


if __name__ == "__main__":
    unittest.main()
