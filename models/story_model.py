from database.queries import execute, fetch_all, fetch_one


def create_story(user_id, media_path, media_type, caption, overlay_text, expires_at):
    return execute(
        "INSERT INTO stories "
        "(user_id, media_path, media_type, caption, overlay_text, expires_at) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        (user_id, media_path, media_type, caption, overlay_text, expires_at),
    )


def active_stories(user_id):
    return fetch_all(
        "SELECT s.id, s.user_id, s.media_path, s.media_type, s.caption, "
        "s.overlay_text, s.created_at, s.expires_at, u.username, u.full_name, "
        "u.avatar_path, CASE WHEN s.user_id = %s THEN 1 ELSE EXISTS("
        "SELECT 1 FROM story_views sv WHERE sv.story_id = s.id "
        "AND sv.viewer_id = %s"
        ") END AS is_viewed, "
        "(SELECT COUNT(*) FROM story_views total WHERE total.story_id = s.id "
        "AND total.viewer_id <> s.user_id) "
        "AS view_count "
        "FROM stories s JOIN users u ON u.id = s.user_id "
        "WHERE s.expires_at > NOW() AND (s.user_id = %s OR u.is_private = FALSE OR EXISTS("
        "SELECT 1 FROM follows f WHERE f.follower_id = %s "
        "AND f.followed_id = s.user_id"
        ")) ORDER BY CASE WHEN s.user_id = %s THEN 0 ELSE 1 END, "
        "s.created_at ASC, s.id ASC",
        (user_id, user_id, user_id, user_id, user_id),
    )


def group_stories(stories, viewer_id):
    groups = {}
    for story in stories:
        group = groups.setdefault(
            story["user_id"],
            {
                "user_id": story["user_id"],
                "username": story["username"],
                "full_name": story["full_name"],
                "avatar_path": story["avatar_path"],
                "avatar_url": f"/static/{story['avatar_path']}"
                if story["avatar_path"]
                else None,
                "is_own": story["user_id"] == viewer_id,
                "has_unviewed": False,
                "stories": [],
            },
        )
        group["stories"].append(
            {
                "id": story["id"],
                "media_url": f"/stories/{story['id']}/media",
                "media_type": story["media_type"],
                "caption": story["caption"] or "",
                "overlay_text": story["overlay_text"] or "",
                "created_at": story["created_at"].isoformat()
                if story["created_at"]
                else "",
                "is_viewed": bool(story["is_viewed"]),
                "view_count": story["view_count"],
                "view_url": f"/stories/{story['id']}/view",
                "delete_url": f"/stories/{story['id']}/delete",
                "viewers_url": f"/stories/{story['id']}/viewers",
                "reply_url": f"/stories/{story['id']}/reply",
            }
        )
        group["has_unviewed"] = group["has_unviewed"] or not story["is_viewed"]
    return sorted(
        groups.values(),
        key=lambda group: (
            not group["is_own"],
            not group["has_unviewed"],
            max(item["created_at"] for item in group["stories"]),
        ),
    )


def get_story_for_viewer(story_id, viewer_id):
    return fetch_one(
        "SELECT s.id, s.user_id, s.media_path, s.media_type, s.caption, "
        "s.overlay_text, s.created_at, s.expires_at, u.username, u.full_name "
        "FROM stories s JOIN users u ON u.id = s.user_id "
        "WHERE s.id = %s AND s.expires_at > NOW() "
        "AND (s.user_id = %s OR u.is_private = FALSE OR EXISTS("
        "SELECT 1 FROM follows f WHERE f.follower_id = %s "
        "AND f.followed_id = s.user_id"
        "))",
        (story_id, viewer_id, viewer_id),
    )


def get_owned_story(story_id, owner_id):
    return fetch_one(
        "SELECT id FROM stories WHERE id = %s AND user_id = %s AND expires_at > NOW()",
        (story_id, owner_id),
    )


def record_story_view(story_id, viewer_id):
    execute(
        "INSERT INTO story_views (story_id, viewer_id) VALUES (%s, %s) "
        "ON DUPLICATE KEY UPDATE viewed_at = CURRENT_TIMESTAMP",
        (story_id, viewer_id),
    )


def get_story_viewers(story_id, owner_id):
    return fetch_all(
        "SELECT u.username, u.full_name, u.avatar_path, sv.viewed_at "
        "FROM story_views sv JOIN users u ON u.id = sv.viewer_id "
        "JOIN stories s ON s.id = sv.story_id "
        "WHERE sv.story_id = %s AND s.user_id = %s AND sv.viewer_id <> s.user_id "
        "ORDER BY sv.viewed_at DESC",
        (story_id, owner_id),
    )


def delete_story(story_id, owner_id):
    story = fetch_one(
        "SELECT id, media_path FROM stories WHERE id = %s AND user_id = %s",
        (story_id, owner_id),
    )
    if not story:
        return None
    execute("DELETE FROM stories WHERE id = %s AND user_id = %s", (story_id, owner_id))
    return story["media_path"]


def get_expired_stories():
    return fetch_all(
        "SELECT id, media_path FROM stories WHERE expires_at <= NOW()"
    )


def delete_expired_story(story_id):
    execute(
        "DELETE FROM stories WHERE id = %s AND expires_at <= NOW()",
        (story_id,),
    )


def get_legacy_story_media():
    return fetch_all(
        "SELECT id, media_path FROM stories "
        "WHERE media_path LIKE 'uploads/stories/%' AND expires_at > NOW()"
    )


def update_story_media_path(story_id, old_path, new_path):
    execute(
        "UPDATE stories SET media_path = %s WHERE id = %s AND media_path = %s",
        (new_path, story_id, old_path),
    )
