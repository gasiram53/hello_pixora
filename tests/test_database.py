import unittest
from unittest.mock import MagicMock, patch

from database.queries import fetch_one


class QueryHelperTests(unittest.TestCase):
    def test_fetch_one_executes_with_bound_parameters(self):
        context = MagicMock()
        cursor = context.__enter__.return_value
        cursor.fetchone.return_value = {"id": 3}
        with patch("database.queries.cursor", return_value=context) as cursor_factory:
            result = fetch_one("SELECT id FROM users WHERE email = %s", ("a@example.com",))
        self.assertEqual(result, {"id": 3})
        cursor_factory.assert_called_once_with(dictionary=True)
        cursor.execute.assert_called_once_with(
            "SELECT id FROM users WHERE email = %s", ("a@example.com",)
        )


if __name__ == "__main__":
    unittest.main()
