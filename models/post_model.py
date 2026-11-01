import re

from database.db_connection import cursor
from database.queries import execute, fetch_all, fetch_one


def create_post(user_id, image_path, caption, media_type="image"):
    tags = {tag.lower() for tag in re.findall(r"(?<!\w)#([a-zA-Z0-9_]{1,80})", caption)}
    with cursor() as db_cursor:
        db_cursor.execute(
            "INSERT INTO posts (user_id, image_path, media_type, caption) "
            "VALUES (%s, %s, %s, %s)",
            (user_id, image_path, media_type, caption),
        )
        post_id = db_cursor.lastrowid
        for tag in tags:
            db_cursor.execute(
                "INSERT INTO hashtags (tag) VALUES (%s) "
                "ON DUPLICATE KEY UPDATE id = LAST_INSERT_ID(id)",
                (tag,),
            )
            hashtag_id = db_cursor.lastrowid
            db_cursor.execute(
                "INSERT IGNORE INTO post_hashtags (post_id, hashtag_id) "
                "VALUES (%s, %s)",
                (post_id, hashtag_id),
            )
    return post_id


def get_feed(user_id, limit=50):
    return fetch_all(
        "SELECT p.id, p.user_id, p.image_path, p.media_type, p.caption, p.created_at, "
        "u.username, u.full_name, u.avatar_path, "
        "(SELECT COUNT(*) FROM likes l WHERE l.post_id = p.id) AS like_count, "
        "(SELECT COUNT(*) FROM comments c WHERE c.post_id = p.id) AS comment_count, "
        "EXISTS(SELECT 1 FROM likes mine WHERE mine.post_id = p.id AND mine.user_id = %s) AS liked, "
        "EXISTS(SELECT 1 FROM saved_posts saved WHERE saved.post_id = p.id "
        "AND saved.user_id = %s) AS saved "
        "FROM posts p JOIN users u ON u.id = p.user_id "
        "WHERE p.user_id = %s OR p.user_id IN "
        "(SELECT followed_id FROM follows WHERE follower_id = %s) "
        "ORDER BY p.created_at DESC LIMIT %s",
        (user_id, user_id, user_id, user_id, limit),
    )


def get_discovery_posts(viewer_id, limit=30):
    return fetch_all(
        "SELECT p.id, p.user_id, p.image_path, p.media_type, p.caption, p.created_at, "
        "u.username, u.full_name, u.avatar_path, "
        "(SELECT COUNT(*) FROM likes l WHERE l.post_id = p.id) AS like_count, "
        "(SELECT COUNT(*) FROM comments c WHERE c.post_id = p.id) AS comment_count, "
        "EXISTS(SELECT 1 FROM likes mine WHERE mine.post_id = p.id AND mine.user_id = %s) AS liked "
        "FROM posts p JOIN users u ON u.id = p.user_id "
        "WHERE u.is_verified = TRUE "
        "ORDER BY p.created_at DESC LIMIT %s",
        (viewer_id, limit),
    )


def search_posts(term, viewer_id, hashtags_only=False, limit=30):
    pattern = f"%#{term.lstrip('#')}%" if hashtags_only else f"%{term}%"
    caption_match = "p.caption LIKE %s" if hashtags_only else "(p.caption LIKE %s OR u.username LIKE %s)"
    params = [viewer_id, pattern]
    if not hashtags_only:
        params.append(pattern)
    params.append(limit)
    return fetch_all(
        "SELECT p.id, p.user_id, p.image_path, p.media_type, p.caption, p.created_at, "
        "u.username, u.full_name, u.avatar_path, "
        "(SELECT COUNT(*) FROM likes l WHERE l.post_id = p.id) AS like_count, "
        "(SELECT COUNT(*) FROM comments c WHERE c.post_id = p.id) AS comment_count, "
        "EXISTS(SELECT 1 FROM likes mine WHERE mine.post_id = p.id AND mine.user_id = %s) AS liked "
        "FROM posts p JOIN users u ON u.id = p.user_id "
        f"WHERE u.is_verified = TRUE AND {caption_match} "
        "ORDER BY p.created_at DESC LIMIT %s",
        tuple(params),
    )


def get_by_id(post_id):
    return fetch_one(
        "SELECT p.*, u.username, u.full_name, u.avatar_path FROM posts p "
        "JOIN users u ON u.id = p.user_id WHERE p.id = %s",
        (post_id,),
    )


def get_by_user(user_id, viewer_id=None):
    return fetch_all(
        "SELECT p.*, (SELECT COUNT(*) FROM likes l WHERE l.post_id = p.id) AS like_count, "
        "(SELECT COUNT(*) FROM comments c WHERE c.post_id = p.id) AS comment_count, "
        "EXISTS(SELECT 1 FROM likes mine WHERE mine.post_id = p.id AND mine.user_id = %s) AS liked "
        "FROM posts p WHERE p.user_id = %s ORDER BY p.created_at DESC",
        (viewer_id or 0, user_id),
    )


def get_saved_by_user(user_id):
    return fetch_all(
        "SELECT p.*, (SELECT COUNT(*) FROM likes l WHERE l.post_id = p.id) AS like_count, "
        "(SELECT COUNT(*) FROM comments c WHERE c.post_id = p.id) AS comment_count, "
        "TRUE AS liked FROM saved_posts s "
        "JOIN posts p ON p.id = s.post_id "
        "WHERE s.user_id = %s ORDER BY s.created_at DESC",
        (user_id,),
    )


def post_count(user_id):
    result = fetch_one(
        "SELECT COUNT(*) AS total FROM posts WHERE user_id = %s",
        (user_id,),
    )
    return result["total"]


def delete_post(post_id, user_id):
    with_post = fetch_one(
        "SELECT id FROM posts WHERE id = %s AND user_id = %s", (post_id, user_id)
    )
    if not with_post:
        return False
    execute("DELETE FROM posts WHERE id = %s AND user_id = %s", (post_id, user_id))
    return True


def toggle_save(user_id, post_id):
    existing = fetch_one(
        "SELECT post_id FROM saved_posts WHERE user_id = %s AND post_id = %s",
        (user_id, post_id),
    )
    if existing:
        execute(
            "DELETE FROM saved_posts WHERE user_id = %s AND post_id = %s",
            (user_id, post_id),
        )
        return False
    execute(
        "INSERT INTO saved_posts (user_id, post_id) VALUES (%s, %s)",
        (user_id, post_id),
    )
    return True
