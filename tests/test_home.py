import unittest
from datetime import datetime
from unittest.mock import patch

from app import create_app


class HomeFeedTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False})
        self.client = self.app.test_client()
        with self.client.session_transaction() as session:
            session["user_id"] = 3
            session["username"] = "pixora_user"
        self.current_user = {
            "id": 3,
            "username": "pixora_user",
            "full_name": "Pixora User",
            "avatar_path": None,
            "created_at": datetime(2026, 1, 1),
        }

    def test_landing_page_hides_sidebar_for_authenticated_user(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'class="pixora-landing-no-sidebar"', response.data)
        self.assertNotIn(b'class="app-sidebar"', response.data)
        self.assertIn(b"Your moments", response.data)
        self.assertIn(b'href="/auth/register"', response.data)
        self.assertIn(b'href="/auth/login"', response.data)
        self.assertIn(b"Open your feed", response.data)

    def test_landing_page_keeps_public_navigation_for_logged_out_user(self):
        response = self.app.test_client().get("/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b'class="app-sidebar"', response.data)
        self.assertIn(b'class="topbar"', response.data)
        self.assertIn(b"Create account", response.data)

    def test_empty_feed_renders_discovery_layout(self):
        with (
            patch("routes.home_routes.get_feed", return_value=[]),
            patch("routes.home_routes.get_by_id", return_value=self.current_user),
            patch("routes.home_routes.active_stories", return_value=[]),
        ):
            response = self.client.get("/feed")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Your feed is quiet", response.data)
        self.assertIn(b'class="app-sidebar"', response.data)
        self.assertIn(b"Stories", response.data)
        self.assertIn(b"data-open-story-dialog", response.data)
        self.assertIn(b'action="/stories/" enctype="multipart/form-data"', response.data)
        self.assertIn(b'name="csrf_token"', response.data)
        self.assertIn(b'class="feed-header-icon"', response.data)
        self.assertIn(b'href="/notifications/"', response.data)
        self.assertIn(b'data-theme-toggle', response.data)
        self.assertEqual(response.data.count(b"data-theme-toggle"), 1)

    def test_populated_feed_keeps_post_actions_and_dynamic_content(self):
        posts = [
            {
                "id": 17,
                "user_id": 8,
                "image_path": "uploads/posts/photo.png",
                "caption": "A day out #PIXORA",
                "created_at": datetime(2026, 10, 30, 10, 0),
                "username": "creator",
                "full_name": "Creator Name",
                "avatar_path": None,
                "like_count": 4,
                "comment_count": 2,
                "liked": True,
            }
        ]
        with (
            patch("routes.home_routes.get_feed", return_value=posts),
            patch("routes.home_routes.get_by_id", return_value=self.current_user),
            patch("routes.home_routes.active_stories", return_value=[]),
        ):
            response = self.client.get("/feed")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"A day out #PIXORA", response.data)
        self.assertIn(b"uploads/posts/photo.png", response.data)
        self.assertIn(b"data-save-post=\"17\"", response.data)
        self.assertIn(b"data-share-url=", response.data)
        self.assertIn(b"/posts/17/comment", response.data)
        self.assertIn(b"/posts/17/like", response.data)
        self.assertIn(b"#PIXORA", response.data)

    def test_feed_stories_only_shows_people_with_active_stories(self):
        posts = [{
            "id": 17,
            "user_id": 8,
            "image_path": "uploads/posts/photo.png",
            "caption": "A post without a story",
            "created_at": datetime(2026, 10, 30, 10, 0),
            "username": "post_author",
            "full_name": "Post Author",
            "avatar_path": None,
            "like_count": 0,
            "comment_count": 0,
            "liked": False,
        }]
        stories = [{
            "id": 41,
            "user_id": 9,
            "media_path": "uploads/stories/story.png",
            "media_type": "image",
            "caption": "",
            "overlay_text": "",
            "created_at": datetime(2026, 10, 30, 11, 0),
            "expires_at": datetime(2026, 10, 31, 11, 0),
            "username": "story_author",
            "full_name": "Story Author",
            "avatar_path": None,
            "is_viewed": False,
            "view_count": 0,
        }]
        with (
            patch("routes.home_routes.get_feed", return_value=posts),
            patch("routes.home_routes.get_by_id", return_value=self.current_user),
            patch("routes.home_routes.active_stories", return_value=stories),
        ):
            response = self.client.get("/feed")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"story_author", response.data)
        self.assertIn(b'data-open-story-group="0"', response.data)
        self.assertNotIn(b'data-story-username="post_author"', response.data)


if __name__ == "__main__":
    unittest.main()
