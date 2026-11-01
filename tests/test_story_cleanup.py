import os
import tempfile
import unittest
from unittest.mock import patch

from flask import Flask

from services.story_cleanup import cleanup_expired_story_media


class StoryCleanupTests(unittest.TestCase):
    def test_expired_story_media_is_removed_and_legacy_media_becomes_private(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            upload_root = os.path.join(temp_dir, "uploads")
            private_root = os.path.join(temp_dir, "private")
            story_root = os.path.join(upload_root, "stories")
            os.makedirs(story_root)
            os.makedirs(private_root)
            expired_path = os.path.join(story_root, "expired.png")
            legacy_path = os.path.join(story_root, "legacy.png")
            with open(expired_path, "wb") as file:
                file.write(b"expired")
            with open(legacy_path, "wb") as file:
                file.write(b"legacy")

            app = Flask(__name__)
            app.config.update(
                UPLOAD_FOLDER=upload_root,
                PRIVATE_UPLOAD_FOLDER=private_root,
            )
            with (
                patch(
                    "services.story_cleanup.get_expired_stories",
                    return_value=[{
                        "id": 21,
                        "media_path": "uploads/stories/expired.png",
                    }],
                ),
                patch("services.story_cleanup.delete_expired_story") as delete_expired,
                patch(
                    "services.story_cleanup.get_legacy_story_media",
                    return_value=[{"id": 22, "media_path": "uploads/stories/legacy.png"}],
                ),
                patch("services.story_cleanup.update_story_media_path") as update_path,
                app.app_context(),
            ):
                cleanup_expired_story_media()

            self.assertFalse(os.path.exists(expired_path))
            self.assertFalse(os.path.exists(legacy_path))
            self.assertTrue(os.path.exists(os.path.join(private_root, "stories", "legacy.png")))
            delete_expired.assert_called_once_with(21)
            update_path.assert_called_once_with(22, "uploads/stories/legacy.png", "stories/legacy.png")


if __name__ == "__main__":
    unittest.main()
