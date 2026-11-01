from database.queries import execute, fetch_all, fetch_one


def is_following(follower_id, followed_id):
    return bool(
        fetch_one(
            "SELECT follower_id FROM follows WHERE follower_id = %s AND followed_id = %s",
            (follower_id, followed_id),
        )
    )


def toggle_follow(follower_id, followed_id):
    if follower_id == followed_id:
        raise ValueError("You cannot follow your own account.")
    if is_following(follower_id, followed_id):
        execute(
            "DELETE FROM follows WHERE follower_id = %s AND followed_id = %s",
            (follower_id, followed_id),
        )
        return False
    execute(
        "INSERT INTO follows (follower_id, followed_id) VALUES (%s, %s)",
        (follower_id, followed_id),
    )
    return True


def counts(user_id):
    followers = fetch_one(
        "SELECT COUNT(*) AS total FROM follows WHERE followed_id = %s", (user_id,)
    )
    following = fetch_one(
        "SELECT COUNT(*) AS total FROM follows WHERE follower_id = %s", (user_id,)
    )
    return followers["total"], following["total"]


def get_followers(user_id):
    return fetch_all(
        "SELECT u.id, u.username, u.full_name, u.avatar_path FROM follows f "
        "JOIN users u ON u.id = f.follower_id WHERE f.followed_id = %s ORDER BY u.username",
        (user_id,),
    )


def get_following(user_id):
    return fetch_all(
        "SELECT u.id, u.username, u.full_name, u.avatar_path FROM follows f "
        "JOIN users u ON u.id = f.followed_id WHERE f.follower_id = %s ORDER BY u.username",
        (user_id,),
    )
