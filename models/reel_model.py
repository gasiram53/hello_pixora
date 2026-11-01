from database.queries import execute, fetch_all, fetch_one


def create_reel(user_id, video_path, caption):
    return execute(
        "INSERT INTO reels (user_id, video_path, caption) VALUES (%s, %s, %s)",
        (user_id, video_path, caption),
    )


def get_reels(viewer_id, limit=50):
    return fetch_all(
        "SELECT r.id, r.user_id, r.video_path, r.caption, r.created_at, "
        "u.username, u.avatar_path, "
        "(SELECT COUNT(*) FROM reel_likes l WHERE l.reel_id = r.id) AS like_count, "
        "(SELECT COUNT(*) FROM reel_comments c WHERE c.reel_id = r.id) AS comment_count, "
        "EXISTS(SELECT 1 FROM reel_likes mine WHERE mine.reel_id = r.id AND mine.user_id = %s) AS liked, "
        "EXISTS(SELECT 1 FROM reel_saves s WHERE s.reel_id = r.id AND s.user_id = %s) AS saved, "
        "EXISTS(SELECT 1 FROM follows f WHERE f.follower_id = %s AND f.followed_id = r.user_id) AS is_following "
        "FROM reels r JOIN users u ON u.id = r.user_id "
        "WHERE u.is_verified = TRUE ORDER BY r.created_at DESC LIMIT %s",
        (viewer_id, viewer_id, viewer_id, limit),
    )


def search_reels(term, viewer_id, limit=30):
    pattern = f"%{term}%"
    return fetch_all(
        "SELECT r.id, r.user_id, r.video_path, r.caption, r.created_at, "
        "u.username, u.avatar_path, "
        "(SELECT COUNT(*) FROM reel_likes l WHERE l.reel_id = r.id) AS like_count, "
        "(SELECT COUNT(*) FROM reel_comments c WHERE c.reel_id = r.id) AS comment_count, "
        "EXISTS(SELECT 1 FROM reel_likes mine WHERE mine.reel_id = r.id "
        "AND mine.user_id = %s) AS liked "
        "FROM reels r JOIN users u ON u.id = r.user_id "
        "WHERE u.is_verified = TRUE AND (r.caption LIKE %s OR u.username LIKE %s) "
        "ORDER BY r.created_at DESC LIMIT %s",
        (viewer_id, pattern, pattern, limit),
    )


def get_reel(reel_id):
    return fetch_one("SELECT id, user_id FROM reels WHERE id = %s", (reel_id,))


def toggle_like(user_id, reel_id):
    existing = fetch_one(
        "SELECT user_id FROM reel_likes WHERE user_id = %s AND reel_id = %s",
        (user_id, reel_id),
    )
    if existing:
        execute(
            "DELETE FROM reel_likes WHERE user_id = %s AND reel_id = %s",
            (user_id, reel_id),
        )
        return False
    execute(
        "INSERT INTO reel_likes (user_id, reel_id) VALUES (%s, %s)",
        (user_id, reel_id),
    )
    return True


def toggle_save(user_id, reel_id):
    existing = fetch_one(
        "SELECT user_id FROM reel_saves WHERE user_id = %s AND reel_id = %s",
        (user_id, reel_id),
    )
    if existing:
        execute(
            "DELETE FROM reel_saves WHERE user_id = %s AND reel_id = %s",
            (user_id, reel_id),
        )
        return False
    execute(
        "INSERT INTO reel_saves (user_id, reel_id) VALUES (%s, %s)",
        (user_id, reel_id),
    )
    return True


def add_comment(user_id, reel_id, body):
    return execute(
        "INSERT INTO reel_comments (user_id, reel_id, body) VALUES (%s, %s, %s)",
        (user_id, reel_id, body),
    )


def get_comments_for_reels(reel_ids, per_reel=3):
    if not reel_ids:
        return []
    placeholders = ", ".join(["%s"] * len(reel_ids))
    return fetch_all(
        "SELECT id, reel_id, body, created_at, username, avatar_path FROM ("
        "SELECT c.id, c.reel_id, c.body, c.created_at, u.username, u.avatar_path, "
        "ROW_NUMBER() OVER (PARTITION BY c.reel_id ORDER BY c.created_at DESC) AS row_num "
        "FROM reel_comments c JOIN users u ON u.id = c.user_id "
        f"WHERE c.reel_id IN ({placeholders})"
        ") recent WHERE row_num <= %s ORDER BY reel_id, created_at DESC",
        (*reel_ids, per_reel),
    )
