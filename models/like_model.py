from database.queries import execute, fetch_one


def toggle_like(user_id, post_id):
    existing = fetch_one(
        "SELECT user_id FROM likes WHERE user_id = %s AND post_id = %s",
        (user_id, post_id),
    )
    if existing:
        execute("DELETE FROM likes WHERE user_id = %s AND post_id = %s", (user_id, post_id))
        return False
    execute("INSERT INTO likes (user_id, post_id) VALUES (%s, %s)", (user_id, post_id))
    return True


def count_for_post(post_id):
    result = fetch_one("SELECT COUNT(*) AS total FROM likes WHERE post_id = %s", (post_id,))
    return result["total"]
