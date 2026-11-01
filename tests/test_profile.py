import unittest
from unittest.mock import patch

from app import create_app


class ProfileRouteTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False})
        self.client = self.app.test_client()
        with self.client.session_transaction() as session:
            session["user_id"] = 2
            session["username"] = "viewer"

    def test_profile_renders_user_and_post_grid(self):
        user = {
            "id": 8,
            "username": "artist",
            "full_name": "A. Artist",
            "bio": "Hello",
            "website": "https://artist.example",
            "avatar_path": None,
        }
        with (
            patch("routes.profile_routes.get_by_username", return_value=user),
            patch("routes.profile_routes.counts", return_value=(3, 5)),
            patch("routes.profile_routes.is_following", return_value=False),
            patch("routes.profile_routes.get_by_user", return_value=[]),
        ):
            response = self.client.get("/profile/artist")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"A. Artist", response.data)
        self.assertIn(b"Hello", response.data)
        self.assertIn(b"Profile sections", response.data)
        self.assertIn(b"Tagged photos", response.data)
        self.assertIn(b"Share Profile", response.data)
        self.assertIn(b"Copy Profile Link", response.data)
        self.assertIn(b"QR Code", response.data)
        self.assertIn(b"Account Settings", response.data)
        self.assertIn(b"Privacy Settings", response.data)
        self.assertIn(b"Report User", response.data)
        self.assertIn(b'href="https://artist.example"', response.data)
        self.assertIn(b'class="app-sidebar"', response.data)
        self.assertIn(b'>Home</span>', response.data)
        self.assertIn(b'>Logout</span>', response.data)
        self.assertIn(b'data-page-header-actions', response.data)
        self.assertEqual(response.data.count(b'data-theme-toggle'), 1)
        self.assertEqual(response.data.count(b'href="/notifications/"'), 1)

    def test_own_profile_menu_does_not_offer_report(self):
        user = {
            "id": 2,
            "username": "viewer",
            "full_name": "Viewer",
            "bio": "",
            "avatar_path": None,
        }
        with (
            patch("routes.profile_routes.get_by_username", return_value=user),
            patch("routes.profile_routes.counts", return_value=(0, 0)),
            patch("routes.profile_routes.is_following", return_value=False),
            patch("routes.profile_routes.get_by_user", return_value=[]),
        ):
            response = self.client.get("/profile/viewer")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"Report User", response.data)

    def test_profile_qr_returns_png(self):
        user = {"id": 8, "username": "artist"}
        with patch("routes.profile_routes.get_by_username", return_value=user):
            response = self.client.get("/profile/artist/qr")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "image/png")
        self.assertTrue(response.data.startswith(b"\x89PNG\r\n\x1a\n"))

    def test_profile_report_is_saved_and_redirects(self):
        target = {"id": 8, "username": "artist"}
        with (
            patch("routes.profile_routes.get_by_username", return_value=target),
            patch("routes.profile_routes.fetch_one", return_value=None),
            patch("routes.profile_routes.execute") as save_report,
        ):
            response = self.client.post(
                "/profile/artist/report",
                data={"reason": "spam", "details": "Repeated links"},
            )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/profile/artist")
        save_report.assert_called_once_with(
            "INSERT INTO user_reports (reporter_id, reported_user_id, reason, details) "
            "VALUES (%s, %s, %s, %s)",
            (2, 8, "spam", "Repeated links"),
        )

    def test_profile_report_rejects_self_report(self):
        target = {"id": 2, "username": "viewer"}
        with (
            patch("routes.profile_routes.get_by_username", return_value=target),
            patch("routes.profile_routes.execute") as save_report,
        ):
            response = self.client.post(
                "/profile/viewer/report",
                data={"reason": "spam", "details": ""},
            )
        self.assertEqual(response.status_code, 404)
        save_report.assert_not_called()

    def test_profile_report_rejects_invalid_reason(self):
        target = {"id": 8, "username": "artist"}
        with (
            patch("routes.profile_routes.get_by_username", return_value=target),
            patch("routes.profile_routes.execute") as save_report,
        ):
            response = self.client.post(
                "/profile/artist/report",
                data={"reason": "invalid", "details": ""},
            )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/profile/artist")
        save_report.assert_not_called()

    def test_profile_grid_keeps_dynamic_post_metrics(self):
        user = {
            "id": 8,
            "username": "artist",
            "full_name": "A. Artist",
            "bio": "Hello",
            "avatar_path": None,
        }
        posts = [{
            "id": 31,
            "image_path": "uploads/posts/art.png",
            "caption": "A photo",
            "like_count": 12,
            "comment_count": 3,
        }]
        with (
            patch("routes.profile_routes.get_by_username", return_value=user),
            patch("routes.profile_routes.counts", return_value=(3, 5)),
            patch("routes.profile_routes.is_following", return_value=False),
            patch("routes.profile_routes.get_by_user", return_value=posts),
        ):
            response = self.client.get("/profile/artist")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"uploads/posts/art.png", response.data)
        self.assertIn(b">12</span>", response.data)
        self.assertIn(b">3</span>", response.data)

    def test_edit_profile_saves_normalized_website(self):
        user = {
            "id": 2,
            "username": "viewer",
            "full_name": "Viewer",
            "bio": "",
            "website": None,
        }
        with (
            patch("routes.profile_routes.get_by_id", return_value=user),
            patch("routes.profile_routes.update_profile") as update_profile,
        ):
            response = self.client.post(
                "/profile/edit",
                data={
                    "full_name": "Viewer",
                    "bio": "Hello",
                    "website": "example.com",
                },
            )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(update_profile.call_args.args[-1], "https://example.com")

    def test_edit_profile_rejects_non_http_website(self):
        user = {
            "id": 2,
            "username": "viewer",
            "full_name": "Viewer",
            "bio": "",
            "website": None,
        }
        with (
            patch("routes.profile_routes.get_by_id", return_value=user),
            patch("routes.profile_routes.update_profile") as update_profile,
        ):
            response = self.client.post(
                "/profile/edit",
                data={
                    "full_name": "Viewer",
                    "bio": "",
                    "website": "javascript:alert(1)",
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Enter a valid website URL", response.data)
        update_profile.assert_not_called()

    def test_profile_index_redirects_to_the_authenticated_users_profile(self):
        user = {"id": 2, "username": "viewer"}
        with patch("routes.profile_routes.get_by_id", return_value=user):
            response = self.client.get("/profile/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/profile/viewer")

    def test_following_page_uses_existing_relationships(self):
        user = {"id": 2, "username": "viewer", "full_name": "Viewer"}
        following = [{
            "id": 8,
            "username": "artist",
            "full_name": "A. Artist",
            "avatar_path": None,
        }]
        with (
            patch("routes.profile_routes.get_by_username", return_value=user),
            patch("routes.profile_routes.get_following", return_value=following),
        ):
            response = self.client.get("/profile/viewer/following")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"A. Artist", response.data)

    def test_saved_posts_page_is_limited_to_the_signed_in_user(self):
        user = {"id": 2, "username": "viewer", "full_name": "Viewer"}
        with (
            patch("routes.profile_routes.get_by_id", return_value=user),
            patch("routes.profile_routes.counts", return_value=(3, 5)),
            patch("routes.profile_routes.get_saved_by_user", return_value=[]) as saved,
        ):
            response = self.client.get("/profile/saved")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"No saved posts yet", response.data)
        saved.assert_called_once_with(2)

    def test_follow_action_returns_to_safe_local_destination(self):
        target = {"id": 8, "username": "artist"}
        with (
            patch("routes.profile_routes.get_by_username", return_value=target),
            patch("routes.profile_routes.toggle_follow", return_value=True),
            patch("routes.profile_routes.create_notification"),
        ):
            response = self.client.post(
                "/profile/artist/follow",
                data={"next": "/reels/#reel-13"},
            )
        self.assertEqual(response.headers["Location"], "/reels/#reel-13")

    def test_follow_action_ignores_external_redirect(self):
        target = {"id": 8, "username": "artist"}
        with (
            patch("routes.profile_routes.get_by_username", return_value=target),
            patch("routes.profile_routes.toggle_follow", return_value=True),
            patch("routes.profile_routes.create_notification"),
        ):
            response = self.client.post(
                "/profile/artist/follow",
                data={"next": "https://example.com"},
            )
        self.assertEqual(response.headers["Location"], "/profile/artist")


if __name__ == "__main__":
    unittest.main()
