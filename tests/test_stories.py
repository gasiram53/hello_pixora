import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from io import BytesIO
from unittest.mock import patch

from app import create_app


class StoryRouteTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.app = create_app({
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "UPLOAD_FOLDER": os.path.join(self.temp_dir.name, "uploads"),
            "PRIVATE_UPLOAD_FOLDER": os.path.join(self.temp_dir.name, "private"),
        })
        self.client = self.app.test_client()
        with self.client.session_transaction() as session:
            session["user_id"] = 3
            session["username"] = "viewer"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_story_page_renders_upload_and_viewer_controls(self):
        current_user = {
            "id": 3,
            "username": "viewer",
            "full_name": "Viewer",
            "avatar_path": None,
        }
        with (
            patch("routes.story_routes.get_by_id", return_value=current_user),
            patch("routes.story_routes.active_stories", return_value=[]),
        ):
            response = self.client.get("/stories/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Add to your story", response.data)
        self.assertIn(b"data-story-viewer", response.data)
        self.assertIn(b"name=\"overlay_text\"", response.data)
        self.assertIn(b"Share to Story", response.data)

    def test_story_feed_uses_active_database_story_groups(self):
        current_user = {
            "id": 3,
            "username": "viewer",
            "full_name": "Viewer",
            "avatar_path": None,
        }
        story = {
            "id": 12,
            "user_id": 9,
            "media_path": "uploads/stories/real-story.png",
            "media_type": "image",
            "caption": "A <safe> caption",
            "overlay_text": "Hello",
            "created_at": datetime(2026, 10, 30, 12, 0),
            "expires_at": datetime(2026, 10, 31, 12, 0),
            "username": "creator",
            "full_name": "A Creator",
            "avatar_path": None,
            "is_viewed": False,
            "view_count": 1,
        }
        with (
            patch("routes.story_routes.get_by_id", return_value=current_user),
            patch("routes.story_routes.active_stories", return_value=[story]),
        ):
            response = self.client.get("/stories/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"@creator", response.data)
        self.assertIn(b"data-open-story-group=\"0\"", response.data)
        self.assertIn(b"/stories/12/media", response.data)
        self.assertNotIn(b"uploads/stories/real-story.png", response.data)
        self.assertIn(b"A \\u003csafe\\u003e caption", response.data)

    def test_valid_story_upload_saves_metadata_and_expires_after_24_hours(self):
        current_user = {
            "id": 3,
            "username": "viewer",
            "full_name": "Viewer",
            "avatar_path": None,
        }
        with (
            patch("routes.story_routes.create_story") as create_story,
            patch("routes.story_routes.get_by_id", return_value=current_user),
            patch("routes.story_routes.active_stories", return_value=[]),
        ):
            response = self.client.post(
                "/stories/",
                data={
                    "caption": "A little moment 😊",
                    "overlay_text": "Hello world",
                    "media": (BytesIO(b"\x89PNG\r\n\x1a\nmore-image-data"), "moment.png"),
                },
                content_type="multipart/form-data",
            )

        self.assertEqual(response.status_code, 302)
        create_story.assert_called_once()
        args = create_story.call_args.args
        self.assertEqual(args[:5], (3, args[1], "image", "A little moment 😊", "Hello world"))
        self.assertTrue(args[1].startswith("stories/"))
        remaining = args[5] - datetime.now(timezone.utc).replace(tzinfo=None)
        self.assertLessEqual(abs(remaining - timedelta(hours=24)), timedelta(seconds=1))

    def test_story_upload_rejects_mismatched_file_content(self):
        current_user = {
            "id": 3,
            "username": "viewer",
            "full_name": "Viewer",
            "avatar_path": None,
        }
        with (
            patch("routes.story_routes.create_story") as create_story,
            patch("routes.story_routes.get_by_id", return_value=current_user),
            patch("routes.story_routes.active_stories", return_value=[]),
        ):
            response = self.client.post(
                "/stories/",
                data={"media": (BytesIO(b"not an image"), "fake.png")},
                content_type="multipart/form-data",
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"content does not match", response.data)
        create_story.assert_not_called()

    def test_story_view_requires_follow_access_and_records_view(self):
        story = {"id": 12, "user_id": 9}
        with (
            patch("routes.story_routes.get_story_for_viewer", return_value=story),
            patch("routes.story_routes.record_story_view") as record_view,
        ):
            response = self.client.post("/stories/12/view")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"viewed": True})
        record_view.assert_called_once_with(12, 3)

    def test_owner_view_does_not_count_as_a_story_view(self):
        story = {"id": 12, "user_id": 3}
        with (
            patch("routes.story_routes.get_story_for_viewer", return_value=story),
            patch("routes.story_routes.record_story_view") as record_view,
        ):
            response = self.client.post("/stories/12/view")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"viewed": True})
        record_view.assert_not_called()

    def test_story_media_requires_story_access(self):
        with patch("routes.story_routes.get_story_for_viewer", return_value=None):
            response = self.client.get("/stories/12/media")

        self.assertEqual(response.status_code, 404)

    def test_authorized_story_media_is_served_from_private_storage(self):
        private_story = os.path.join(self.temp_dir.name, "private", "stories")
        os.makedirs(private_story, exist_ok=True)
        media_path = os.path.join(private_story, "private.png")
        with open(media_path, "wb") as file:
            file.write(b"private story media")
        with patch(
            "routes.story_routes.get_story_for_viewer",
            return_value={"id": 12, "media_path": "stories/private.png"},
        ):
            response = self.client.get("/stories/12/media")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b"private story media")
        response.close()

    def test_viewers_endpoint_only_returns_owner_visible_data(self):
        viewers = [{
            "username": "follower",
            "full_name": "A Follower",
            "avatar_path": None,
            "viewed_at": datetime(2026, 10, 30, 12, 0),
        }]
        with (
            patch("routes.story_routes.get_owned_story", return_value={"id": 12}),
            patch("routes.story_routes.get_story_viewers", return_value=viewers),
        ):
            response = self.client.get("/stories/12/viewers")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()[0]["username"], "follower")

    def test_delete_requires_ownership_and_removes_media(self):
        media_file = BytesIO(b"story image")
        media_path = os.path.join(self.temp_dir.name, "uploads", "stories", "story.png")
        os.makedirs(os.path.dirname(media_path), exist_ok=True)
        with open(media_path, "wb") as file:
            file.write(media_file.getvalue())
        with patch("routes.story_routes.delete_story", return_value="uploads/stories/story.png"):
            response = self.client.post("/stories/12/delete")

        self.assertEqual(response.status_code, 302)
        self.assertFalse(os.path.exists(media_path))

    def test_story_reply_sends_existing_direct_message(self):
        story = {"id": 12, "user_id": 9, "username": "creator"}
        with (
            patch("routes.story_routes.get_story_for_viewer", return_value=story),
            patch("routes.story_routes.send_message") as send_message,
        ):
            response = self.client.post("/stories/12/reply", data={"body": "  Nice story!  "})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/messages/?user_id=9")
        send_message.assert_called_once_with(3, 9, "Nice story!")


if __name__ == "__main__":
    unittest.main()
