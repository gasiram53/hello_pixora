from database.queries import execute, fetch_all, fetch_one


def create_user(username, email, password_hash, full_name):
    return execute(
        "INSERT INTO users (username, email, password_hash, full_name) VALUES (%s, %s, %s, %s)",
        (username, email, password_hash, full_name),
    )


def get_by_email(email):
    return fetch_one("SELECT * FROM users WHERE email = %s", (email,))


def get_by_username(username):
    return fetch_one("SELECT * FROM users WHERE username = %s", (username,))


def get_by_id(user_id):
    return fetch_one(
        "SELECT id, username, email, full_name, bio, website, avatar_path, "
        "is_verified, is_private, created_at "
        "FROM users WHERE id = %s",
        (user_id,),
    )


def update_profile(user_id, full_name, bio, avatar_path=None, website=None):
    if avatar_path:
        execute(
            "UPDATE users SET full_name = %s, bio = %s, avatar_path = %s, website = %s "
            "WHERE id = %s",
            (full_name, bio, avatar_path, website or None, user_id),
        )
    else:
        execute(
            "UPDATE users SET full_name = %s, bio = %s, website = %s WHERE id = %s",
            (full_name, bio, website or None, user_id),
        )


def search_users(term, exclude_id, limit=20):
    pattern = f"%{term}%"
    return fetch_all(
        "SELECT id, username, full_name, bio, avatar_path, "
        "EXISTS(SELECT 1 FROM follows f WHERE f.follower_id = %s "
        "AND f.followed_id = users.id) AS is_following "
        "FROM users "
        "WHERE is_verified = TRUE AND id <> %s AND (username LIKE %s OR full_name LIKE %s) "
        "ORDER BY username LIMIT %s",
        (exclude_id, exclude_id, pattern, pattern, limit),
    )


def save_otp(user_id, code_hash, expires_at):
    execute("DELETE FROM email_otps WHERE user_id = %s", (user_id,))
    execute(
        "INSERT INTO email_otps (user_id, code_hash, expires_at) VALUES (%s, %s, %s)",
        (user_id, code_hash, expires_at),
    )


def get_otp(user_id):
    return fetch_one(
        "SELECT id, code_hash, expires_at FROM email_otps WHERE user_id = %s "
        "ORDER BY created_at DESC LIMIT 1",
        (user_id,),
    )


def get_otp_request_stats(user_id):
    return fetch_one(
        "SELECT COUNT(*) AS request_count, MAX(created_at) AS latest_request_at "
        "FROM otp_request_log WHERE user_id = %s "
        "AND created_at >= NOW() - INTERVAL 1 HOUR",
        (user_id,),
    )


def log_otp_request(user_id):
    execute(
        "DELETE FROM otp_request_log WHERE created_at < NOW() - INTERVAL 1 DAY"
    )
    execute("INSERT INTO otp_request_log (user_id) VALUES (%s)", (user_id,))


def verify_user(user_id):
    execute("UPDATE users SET is_verified = TRUE WHERE id = %s", (user_id,))
    execute("DELETE FROM email_otps WHERE user_id = %s", (user_id,))


def update_password(user_id, password_hash):
    execute("UPDATE users SET password_hash = %s WHERE id = %s", (password_hash, user_id))


def update_username(user_id, username):
    execute("UPDATE users SET username = %s WHERE id = %s", (username, user_id))
