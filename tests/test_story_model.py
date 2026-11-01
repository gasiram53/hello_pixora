import unittest
from unittest.mock import patch

from models.story_model import active_stories, get_story_for_viewer


class StoryAccessQueryTests(unittest.TestCase):
    def test_active_story_query_includes_public_and_followed_private_stories(self):
        with patch("models.story_model.fetch_all", return_value=[]) as fetch_all:
            active_stories(14)

        sql, params = fetch_all.call_args.args
        self.assertIn("s.expires_at > NOW()", sql)
        self.assertIn("u.is_private = FALSE", sql)
        self.assertIn("f.follower_id = %s", sql)
        self.assertEqual(params, (14, 14, 14, 14, 14))

    def test_individual_story_access_uses_same_privacy_rules(self):
        with patch("models.story_model.fetch_one", return_value=None) as fetch_one:
            get_story_for_viewer(51, 14)

        sql, params = fetch_one.call_args.args
        self.assertIn("s.expires_at > NOW()", sql)
        self.assertIn("u.is_private = FALSE", sql)
        self.assertIn("f.follower_id = %s", sql)
        self.assertEqual(params, (51, 14, 14))


if __name__ == "__main__":
    unittest.main()
