import unittest
from unittest.mock import patch

from app import create_app


class ReelRouteTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False})
        self.client = self.app.test_client()
        with self.client.session_transaction() as session:
            session["user_id"] = 4
            session["username"] = "viewer"

    def test_reels_page_renders_dynamic_reels_and_comments(self):
        reel = {
            "id": 13,
            "user_id": 8,
            "video_path": "uploads/reels/clip.mp4",
            "caption": "A little moment #PIXORA",
            "created_at": "today",
            "username": "creator",
            "avatar_path": None,
            "like_count": 5,
            "comment_count": 1,
            "liked": True,
            "saved": False,
            "is_following": False,
        }
        comment = {
            "id": 2,
            "reel_id": 13,
            "username": "friend",
            "avatar_path": None,
            "body": "Love this!",
            "created_at": "today",
        }
        with (
            patch("routes.reel_routes.get_reels", return_value=[reel]),
            patch("routes.reel_routes.get_comments_for_reels", return_value=[comment]),
        ):
            response = self.client.get("/reels/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"uploads/reels/clip.mp4", response.data)
        self.assertIn(b"A little moment #PIXORA", response.data)
        self.assertIn(b"Love this!", response.data)
        self.assertIn(b"/reels/13/like", response.data)
        self.assertIn(b"/reels/13/save", response.data)
        self.assertIn(b"/reels/13/comment", response.data)
        self.assertIn(b"Unmute video", response.data)
        self.assertIn(b'data-page-header-actions', response.data)
        self.assertEqual(response.data.count(b'data-theme-toggle'), 1)
        self.assertEqual(response.data.count(b'href="/notifications/"'), 1)

    def test_like_save_and_comment_actions_redirect_to_reel(self):
        reel = {"id": 13, "user_id": 8}
        with (
            patch("routes.reel_routes.get_reel", return_value=reel),
            patch("routes.reel_routes.toggle_like") as like,
            patch("routes.reel_routes.toggle_save") as save,
            patch("routes.reel_routes.add_comment") as add_comment,
        ):
            like_response = self.client.post("/reels/13/like")
            save_response = self.client.post("/reels/13/save")
            comment_response = self.client.post(
                "/reels/13/comment", data={"body": "Nice video"}
            )
        self.assertEqual(like_response.headers["Location"], "/reels/#reel-13")
        self.assertEqual(save_response.headers["Location"], "/reels/#reel-13")
        self.assertEqual(comment_response.headers["Location"], "/reels/#comments-13")
        like.assert_called_once_with(4, 13)
        save.assert_called_once_with(4, 13)
        add_comment.assert_called_once_with(4, 13, "Nice video")

    def test_comment_rejects_empty_body(self):
        with (
            patch("routes.reel_routes.get_reel", return_value={"id": 13}),
            patch("routes.reel_routes.add_comment") as add_comment,
        ):
            response = self.client.post("/reels/13/comment", data={"body": "  "})
        self.assertEqual(response.status_code, 302)
        add_comment.assert_not_called()


if __name__ == "__main__":
    unittest.main()
