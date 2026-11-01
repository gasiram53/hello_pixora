from database.queries import execute, fetch_all


def add_comment(user_id, post_id, body):
    return execute(
        "INSERT INTO comments (user_id, post_id, body) VALUES (%s, %s, %s)",
        (user_id, post_id, body),
    )


def get_for_post(post_id):
    return fetch_all(
        "SELECT c.id, c.body, c.created_at, u.username, u.avatar_path "
        "FROM comments c JOIN users u ON u.id = c.user_id "
        "WHERE c.post_id = %s ORDER BY c.created_at ASC",
        (post_id,),
    )
