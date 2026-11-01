import unittest
from unittest.mock import patch

from app import create_app


class SearchRouteTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False})
        self.client = self.app.test_client()
        with self.client.session_transaction() as session:
            session["user_id"] = 3
            session["username"] = "viewer"

    def test_search_renders_people_posts_and_reels_results(self):
        users = [{
            "id": 8,
            "username": "creator",
            "full_name": "Creator Name",
            "bio": "A creative bio",
            "avatar_path": None,
            "is_following": False,
        }]
        posts = [{
            "id": 17,
            "user_id": 8,
            "image_path": "uploads/posts/photo.png",
            "caption": "A #travel moment",
            "username": "creator",
            "avatar_path": None,
            "like_count": 4,
            "comment_count": 2,
        }]
        reels = [{
            "id": 22,
            "user_id": 8,
            "video_path": "uploads/reels/clip.mp4",
            "caption": "A travel reel",
            "username": "creator",
            "like_count": 5,
            "comment_count": 1,
        }]
        with (
            patch("routes.search_routes.search_users", return_value=users),
            patch("routes.search_routes.search_posts", return_value=posts),
            patch("routes.search_routes.search_reels", return_value=reels),
        ):
            response = self.client.get("/search/?q=travel")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Creator Name", response.data)
        self.assertIn(b"A creative bio", response.data)
        self.assertIn(b"A #travel moment", response.data)
        self.assertIn(b"uploads/posts/photo.png", response.data)
        self.assertIn(b"uploads/reels/clip.mp4", response.data)
        self.assertIn(b'name="csrf_token"', response.data)
        self.assertIn(b'data-page-header-actions', response.data)
        self.assertEqual(response.data.count(b'data-theme-toggle'), 1)
        self.assertEqual(response.data.count(b'href="/notifications/"'), 1)

    def test_people_filter_only_searches_people(self):
        user = {
            "id": 9,
            "username": "maya",
            "full_name": "Maya",
            "bio": "",
            "avatar_path": None,
            "is_following": True,
        }
        with (
            patch("routes.search_routes.search_users", return_value=[user]) as search_users,
            patch("routes.search_routes.search_posts") as search_posts,
            patch("routes.search_routes.search_reels") as search_reels,
        ):
            response = self.client.get("/search/?q=maya&type=people")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Following", response.data)
        self.assertIn(b"people", response.data)
        search_users.assert_called_once_with("maya", 3)
        search_posts.assert_not_called()
        search_reels.assert_not_called()

    def test_hashtag_filter_queries_caption_hashtags(self):
        with (
            patch("routes.search_routes.search_posts", return_value=[]) as search_posts,
            patch("routes.search_routes.search_users") as search_users,
        ):
            response = self.client.get("/search/?q=%23travel&type=hashtags")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Posts tagged #travel", response.data)
        search_posts.assert_called_once_with("#travel", 3, hashtags_only=True)
        search_users.assert_not_called()

    def test_suggestions_returns_profile_data_and_safe_profile_url(self):
        user = {
            "id": 8,
            "username": "creator",
            "full_name": "Creator Name",
            "bio": "Creative",
            "avatar_path": "uploads/profile_pictures/avatar.png",
            "is_following": False,
        }
        with patch("routes.search_routes.search_users", return_value=[user]) as search_users:
            response = self.client.get("/search/suggestions?q=creator")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json(),
            [{
                "username": "creator",
                "full_name": "Creator Name",
                "bio": "Creative",
                "avatar_url": "/static/uploads/profile_pictures/avatar.png",
                "profile_url": "/profile/creator",
            }],
        )
        search_users.assert_called_once_with("creator", 3, limit=6)

    def test_suggestions_skips_short_terms(self):
        with patch("routes.search_routes.search_users") as search_users:
            response = self.client.get("/search/suggestions?q=a")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), [])
        search_users.assert_not_called()


if __name__ == "__main__":
    unittest.main()
