from database.queries import execute, fetch_all


def create(recipient_id, actor_id, kind, post_id=None):
    if recipient_id == actor_id:
        return
    execute(
        "INSERT INTO notifications (recipient_id, actor_id, kind, post_id) "
        "VALUES (%s, %s, %s, %s)",
        (recipient_id, actor_id, kind, post_id),
    )


def for_user(user_id):
    return fetch_all(
        "SELECT n.id, n.kind, n.is_read, n.created_at, n.post_id, n.actor_id, "
        "u.username AS actor_username, u.avatar_path "
        "FROM notifications n JOIN users u ON u.id = n.actor_id "
        "WHERE n.recipient_id = %s ORDER BY n.created_at DESC LIMIT 50",
        (user_id,),
    )
