import unittest
from datetime import datetime
from io import BytesIO
import tempfile
from unittest.mock import patch

from app import create_app
from services.realtime import socketio


class MessageRouteTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.app = create_app({
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "UPLOAD_FOLDER": self.temp_dir.name,
            "PRIVATE_UPLOAD_FOLDER": self.temp_dir.name,
        })
        self.client = self.app.test_client()
        with self.client.session_transaction() as session:
            session["user_id"] = 2
            session["username"] = "viewer"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_messages_page_renders_dynamic_thread_and_conversations(self):
        viewer = {
            "id": 2,
            "username": "viewer",
            "full_name": "Current Viewer",
            "avatar_path": None,
        }
        recipient = {
            "id": 8,
            "username": "artist",
            "full_name": "A. Artist",
            "avatar_path": None,
        }
        thread = [
            {
                "id": 11,
                "sender_id": 8,
                "body": "<hello>",
                "created_at": datetime(2026, 10, 30, 12, 0),
            }
        ]
        conversations = [
            {
                "id": 8,
                "username": "artist",
                "full_name": "A. Artist",
                "avatar_path": None,
                "sender_id": 8,
                "body": "A first note",
                "created_at": datetime(2026, 10, 30, 12, 0),
            }
        ]
        with (
            patch(
                "routes.message_routes.get_by_id",
                side_effect=lambda user_id: viewer if user_id == 2 else recipient,
            ),
            patch("routes.message_routes.get_conversation", return_value=thread),
            patch("routes.message_routes.get_conversations", return_value=conversations),
            patch("routes.message_routes.mark_conversation_read") as mark_read,
        ):
            response = self.client.get("/messages/?user_id=8")

        self.assertEqual(response.status_code, 200)
        mark_read.assert_called_once_with(2, 8)
        self.assertIn(b"Messages", response.data)
        self.assertIn(b"A. Artist", response.data)
        self.assertIn(b"&lt;hello&gt;", response.data)
        self.assertIn(b"A first note", response.data)
        self.assertIn(b"static/css/message.css", response.data)
        self.assertIn(b"static/js/message.js", response.data)
        self.assertIn(b"static/css/message.css?v=2", response.data)
        self.assertIn(b"static/js/message.js?v=2", response.data)
        self.assertIn(b"static/js/socket-client.js", response.data)
        self.assertIn(b'data-start-call="audio"', response.data)
        self.assertIn(b'data-start-call="video"', response.data)
        self.assertIn(b'data-call-accept', response.data)
        self.assertIn(b'data-call-reject', response.data)
        self.assertIn(b'data-call-mute', response.data)
        self.assertIn(b'data-call-speaker', response.data)
        self.assertIn(b'data-call-camera', response.data)
        self.assertIn(b'data-call-end', response.data)
        self.assertNotIn(b'data-page-header-actions', response.data)
        self.assertNotIn(b'data-theme-toggle', response.data)
        self.assertNotIn(b'href="/notifications/"', response.data)

    def test_people_search_returns_limited_public_user_fields(self):
        person = {
            "id": 8,
            "username": "artist",
            "full_name": "A. Artist",
            "avatar_path": "uploads/profile_pictures/avatar.png",
        }
        with patch("routes.message_routes.search_users", return_value=[person]) as search:
            response = self.client.get("/messages/people?q=artist")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), [person])
        search.assert_called_once_with("artist", 2)

    def test_self_conversation_does_not_show_call_controls(self):
        viewer = {
            "id": 2,
            "username": "viewer",
            "full_name": "Current Viewer",
            "avatar_path": None,
        }
        with (
            patch("routes.message_routes.get_by_id", return_value=viewer),
            patch("routes.message_routes.get_conversation", return_value=[]),
            patch("routes.message_routes.get_conversations", return_value=[]),
        ):
            response = self.client.get("/messages/?user_id=2")

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b'data-start-call="audio"', response.data)
        self.assertNotIn(b'data-call-overlay', response.data)

    def test_message_rejects_empty_body(self):
        viewer = {"id": 2, "username": "viewer", "full_name": "Viewer", "avatar_path": None}
        recipient = {"id": 8, "username": "artist", "full_name": "Artist", "avatar_path": None}
        with (
            patch(
                "routes.message_routes.get_by_id",
                side_effect=lambda user_id: viewer if user_id == 2 else recipient,
            ),
            patch("routes.message_routes.get_conversation", return_value=[]),
            patch("routes.message_routes.get_conversations", return_value=[]),
            patch("routes.message_routes.send_message") as send_message,
            patch("routes.message_routes.mark_conversation_read"),
        ):
            response = self.client.post(
                "/messages/",
                data={"user_id": "8", "body": "   "},
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Text is limited to 2,000 characters", response.data)
        send_message.assert_not_called()

    def test_valid_message_uses_existing_storage_and_redirects(self):
        recipient = {"id": 8, "username": "artist", "full_name": "Artist", "avatar_path": None}
        with (
            patch("routes.message_routes.get_by_id", return_value=recipient),
            patch("routes.message_routes.send_message", return_value=15) as send_message,
            patch("routes.message_routes.create_notification"),
        ):
            response = self.client.post(
                "/messages/",
                data={"user_id": "8", "body": "  A hello  "},
            )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/messages/?user_id=8")
        send_message.assert_called_once_with(2, 8, "A hello", None)

    def test_image_message_is_saved_and_socket_connection_is_authenticated(self):
        sender = {"id": 2, "username": "viewer", "full_name": "Viewer", "avatar_path": None}
        recipient = {"id": 8, "username": "artist", "full_name": "Artist", "avatar_path": None}
        recipient_session = self.app.test_client()
        with recipient_session.session_transaction() as session:
            session["user_id"] = 8
            session["username"] = "artist"
        receiver = socketio.test_client(
            self.app, namespace="/messages", flask_test_client=recipient_session
        )
        self.assertTrue(receiver.is_connected(namespace="/messages"))
        with (
            patch(
                "routes.message_routes.get_by_id",
                side_effect=lambda user_id: sender if user_id == 2 else recipient,
            ),
            patch("routes.message_routes.send_message", return_value=19) as send_message,
            patch("routes.message_routes.create_notification"),
        ):
            response = self.client.post(
                "/messages/",
                data={
                    "user_id": "8",
                    "body": "",
                    "media": (BytesIO(b"\x89PNG\r\n\x1a\nimage-data"), "photo.png"),
                },
                content_type="multipart/form-data",
            )

        self.assertEqual(response.status_code, 302)
        send_message.assert_called_once()
        self.assertEqual(send_message.call_args.args[:3], (2, 8, ""))
        self.assertTrue(send_message.call_args.args[3].startswith("messages/"))
        received = receiver.get_received("/messages")
        self.assertEqual(received[0]["name"], "new_message")
        self.assertEqual(received[0]["args"][0]["id"], 19)
        self.assertEqual(received[0]["args"][0]["media_url"], "/messages/media/19")
        receiver.disconnect(namespace="/messages")

    def test_socket_connection_rejects_anonymous_user(self):
        anonymous_client = self.app.test_client()
        client = socketio.test_client(
            self.app, namespace="/messages", flask_test_client=anonymous_client
        )
        self.assertFalse(client.is_connected(namespace="/messages"))

    def test_local_socket_client_is_served(self):
        response = self.client.get("/static/js/socket-client.js")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"window.io", response.data)
        self.assertNotIn(b"cdn.socket.io", response.data)
        response.close()

    def test_authenticated_users_can_signal_a_peer_call(self):
        caller = socketio.test_client(
            self.app, namespace="/messages", flask_test_client=self.client
        )
        recipient_session = self.app.test_client()
        with recipient_session.session_transaction() as session:
            session["user_id"] = 8
            session["username"] = "artist"
        recipient = socketio.test_client(
            self.app, namespace="/messages", flask_test_client=recipient_session
        )
        other_session = self.app.test_client()
        with other_session.session_transaction() as session:
            session["user_id"] = 9
            session["username"] = "other"
        other_user = socketio.test_client(
            self.app, namespace="/messages", flask_test_client=other_session
        )
        users = {
            2: {"id": 2, "username": "viewer", "full_name": "Current Viewer"},
            8: {"id": 8, "username": "artist", "full_name": "A. Artist"},
        }
        call_id = "call-test-0123456789"
        try:
            with patch("services.realtime.get_by_id", side_effect=users.get):
                caller.emit(
                    "call:invite",
                    {"call_id": call_id, "to_user_id": 8, "call_type": "video"},
                    namespace="/messages",
                )
                incoming = recipient.get_received("/messages")
                self.assertEqual(incoming[0]["name"], "call:incoming")
                self.assertEqual(incoming[0]["args"][0]["from_name"], "Current Viewer")

                recipient.emit(
                    "call:accept", {"call_id": call_id}, namespace="/messages"
                )
                accepted = caller.get_received("/messages")
                self.assertEqual(accepted[0]["name"], "call:accepted")

                offer = {"type": "offer", "sdp": "test-offer"}
                other_user.emit(
                    "call:offer",
                    {"call_id": call_id, "signal": offer},
                    namespace="/messages",
                )
                self.assertEqual(other_user.get_received("/messages")[0]["name"], "call:error")
                self.assertEqual(recipient.get_received("/messages"), [])

                caller.emit(
                    "call:offer",
                    {"call_id": call_id, "signal": offer},
                    namespace="/messages",
                )
                received_offer = recipient.get_received("/messages")
                self.assertEqual(received_offer[0]["name"], "call:offer")
                self.assertEqual(received_offer[0]["args"][0]["signal"], offer)

                recipient.emit(
                    "call:end", {"call_id": call_id}, namespace="/messages"
                )
                ended = caller.get_received("/messages")
                self.assertEqual(ended[0]["name"], "call:ended")
        finally:
            caller.disconnect(namespace="/messages")
            recipient.disconnect(namespace="/messages")
            other_user.disconnect(namespace="/messages")

    def test_private_message_media_is_not_found_for_nonparticipants(self):
        with patch("routes.message_routes.get_message_media_path", return_value=None):
            response = self.client.get("/messages/media/19")
        self.assertEqual(response.status_code, 404)

    def test_message_updates_are_limited_to_authenticated_conversation(self):
        created_at = datetime(2026, 10, 30, 12, 0)
        messages = [{
            "id": 21,
            "sender_id": 8,
            "sender_username": "artist",
            "body": "Hello again",
            "media_path": None,
            "created_at": created_at,
        }]
        with (
            patch("routes.message_routes.get_by_id", return_value={"id": 8}),
            patch("routes.message_routes.get_new_messages", return_value=messages) as updates,
            patch("routes.message_routes.mark_conversation_read") as mark_read,
        ):
            response = self.client.get("/messages/8/updates?after_id=-3")

        self.assertEqual(response.status_code, 200)
        mark_read.assert_called_once_with(2, 8)
        self.assertEqual(response.get_json()[0]["id"], 21)
        self.assertEqual(response.get_json()[0]["body"], "Hello again")
        updates.assert_called_once_with(2, 8, 0)


if __name__ == "__main__":
    unittest.main()
