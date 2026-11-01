from database.queries import execute, fetch_all, fetch_one


def get_conversations(user_id):
    return fetch_all(
        "SELECT u.id, u.username, u.full_name, u.avatar_path, "
        "m.sender_id, m.body, m.media_path, m.created_at "
        "FROM messages m "
        "JOIN users u ON u.id = CASE WHEN m.sender_id = %s "
        "THEN m.recipient_id ELSE m.sender_id END "
        "WHERE (m.sender_id = %s OR m.recipient_id = %s) "
        "AND NOT EXISTS ("
        "SELECT 1 FROM messages newer "
        "WHERE ((newer.sender_id = m.sender_id AND newer.recipient_id = m.recipient_id) "
        "OR (newer.sender_id = m.recipient_id AND newer.recipient_id = m.sender_id)) "
        "AND (newer.created_at > m.created_at "
        "OR (newer.created_at = m.created_at AND newer.id > m.id))"
        ") ORDER BY m.created_at DESC, m.id DESC",
        (user_id, user_id, user_id),
    )


def get_conversation(user_id, other_id):
    return fetch_all(
        "SELECT m.id, m.sender_id, m.recipient_id, m.body, m.media_path, "
        "m.created_at, u.username "
        "FROM messages m JOIN users u ON u.id = m.sender_id "
        "WHERE (m.sender_id = %s AND m.recipient_id = %s) "
        "OR (m.sender_id = %s AND m.recipient_id = %s) ORDER BY m.created_at",
        (user_id, other_id, other_id, user_id),
    )


def mark_conversation_read(user_id, other_id):
    execute(
        "UPDATE messages SET is_read = TRUE "
        "WHERE recipient_id = %s AND sender_id = %s AND is_read = FALSE",
        (user_id, other_id),
    )


def unread_message_count(user_id):
    result = fetch_one(
        "SELECT COUNT(*) AS total FROM messages "
        "WHERE recipient_id = %s AND is_read = FALSE",
        (user_id,),
    )
    return result["total"]


def send_message(sender_id, recipient_id, body, media_path=None):
    return execute(
        "INSERT INTO messages (sender_id, recipient_id, body, media_path) "
        "VALUES (%s, %s, %s, %s)",
        (sender_id, recipient_id, body, media_path),
    )


def get_message_media_path(message_id, user_id):
    message = fetch_one(
        "SELECT media_path FROM messages WHERE id = %s "
        "AND (sender_id = %s OR recipient_id = %s)",
        (message_id, user_id, user_id),
    )
    return message["media_path"] if message else None


def get_new_messages(user_id, other_id, after_id):
    return fetch_all(
        "SELECT m.id, m.sender_id, m.recipient_id, m.body, m.media_path, "
        "m.created_at, u.username AS sender_username "
        "FROM messages m JOIN users u ON u.id = m.sender_id "
        "WHERE m.id > %s AND ((m.sender_id = %s AND m.recipient_id = %s) "
        "OR (m.sender_id = %s AND m.recipient_id = %s)) "
        "ORDER BY m.id ASC LIMIT 50",
        (after_id, user_id, other_id, other_id, user_id),
    )
