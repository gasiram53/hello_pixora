import tempfile
import unittest
from datetime import datetime
from io import BytesIO
from unittest.mock import MagicMock, patch

from app import create_app
from models.post_model import create_post


class PostRouteTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.app = create_app(
            {
                "TESTING": True,
                "WTF_CSRF_ENABLED": False,
                "UPLOAD_FOLDER": self.temp_dir.name,
            }
        )
        self.client = self.app.test_client()
        with self.client.session_transaction() as session:
            session["user_id"] = 4
            session["username"] = "creator"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_post_detail_renders_media_panel_and_comments(self):
        post = {
            "id": 21,
            "user_id": 8,
            "username": "creator",
            "full_name": "Creator",
            "avatar_path": None,
            "image_path": "uploads/posts/photo.png",
            "media_type": "image",
            "caption": "A sunny day",
            "created_at": datetime(2026, 10, 30, 11, 34),
        }
        comments = [{"username": "friend", "body": "Looks great!"}]
        with (
            patch("routes.post_routes.get_by_id", return_value=post),
            patch("routes.post_routes.get_for_post", return_value=comments),
            patch("routes.post_routes.count_for_post", return_value=2),
        ):
            response = self.client.get("/posts/21")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"post-detail-container", response.data)
        self.assertIn(b"detail-media", response.data)
        self.assertIn(b"detail-comment-list", response.data)
        self.assertIn(b"uploads/posts/photo.png", response.data)
        self.assertIn(b"Looks great!", response.data)
        self.assertIn(b'action="/posts/21/comment"', response.data)

    def test_create_post_stores_uploaded_image(self):
        with patch("routes.post_routes.create_post") as create_post:
            response = self.client.post(
                "/posts/create",
                data={
                    "caption": "A first post",
                    "image": (BytesIO(b"\x89PNG\r\n\x1a\nmore-image-data"), "photo.png"),
                },
                content_type="multipart/form-data",
            )
        self.assertEqual(response.status_code, 302)
        create_post.assert_called_once()
        self.assertEqual(create_post.call_args.args[0], 4)
        self.assertTrue(create_post.call_args.args[1].startswith("uploads/posts/"))
        self.assertEqual(create_post.call_args.args[2:], ("A first post", "image"))

    def test_create_post_accepts_supported_video_and_stores_media_type(self):
        with patch("routes.post_routes.create_post") as create_post:
            response = self.client.post(
                "/posts/create",
                data={
                    "caption": "A short clip",
                    "media": (BytesIO(b"\x00\x00\x00\x18ftypmp42more-video-data"), "clip.mp4"),
                },
                content_type="multipart/form-data",
            )

        self.assertEqual(response.status_code, 302)
        create_post.assert_called_once()
        self.assertEqual(create_post.call_args.args[2:], ("A short clip", "video"))

    def test_create_post_rejects_mismatched_media_signature(self):
        with patch("routes.post_routes.create_post") as create_post:
            response = self.client.post(
                "/posts/create",
                data={"media": (BytesIO(b"not an image"), "fake.png")},
                content_type="multipart/form-data",
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"content does not match", response.data)
        create_post.assert_not_called()

    def test_create_post_rejects_files_over_limit(self):
        large_media = b"\x89PNG\r\n\x1a\n" + b"x" * (20 * 1024 * 1024)
        with patch("routes.post_routes.create_post") as create_post:
            response = self.client.post(
                "/posts/create",
                data={"media": (BytesIO(large_media), "large.png")},
                content_type="multipart/form-data",
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"20 MB upload limit", response.data)
        create_post.assert_not_called()

    def test_create_post_rejects_unsupported_file(self):
        response = self.client.post(
            "/posts/create",
            data={"image": (BytesIO(b"not an image"), "payload.exe")},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"file type is not supported", response.data)

    def test_save_action_requires_an_existing_post_and_returns_saved_state(self):
        with (
            patch("routes.post_routes.get_by_id", return_value={"id": 13}),
            patch("routes.post_routes.toggle_save", return_value=True) as toggle_save,
        ):
            response = self.client.post("/posts/13/save")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"saved": True})
        toggle_save.assert_called_once_with(4, 13)

    def test_create_post_indexes_unique_normalized_hashtags_in_same_transaction(self):
        context = MagicMock()
        db_cursor = context.__enter__.return_value
        db_cursor.lastrowid = 41
        with patch("models.post_model.cursor", return_value=context):
            post_id = create_post(
                4, "uploads/posts/photo.png", "A #Pixora day with #MCA #pixora"
            )

        self.assertEqual(post_id, 41)
        self.assertEqual(db_cursor.execute.call_count, 5)
        inserted_tags = {
            call.args[1][0]
            for call in db_cursor.execute.call_args_list
            if call.args[0].startswith("INSERT INTO hashtags")
        }
        self.assertEqual(inserted_tags, {"pixora", "mca"})


if __name__ == "__main__":
    unittest.main()
