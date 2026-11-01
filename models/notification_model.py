from services.notification_service import for_user
from database.queries import fetch_one


def unread_count(user_id):
    result = fetch_one(
        "SELECT COUNT(*) AS total FROM notifications "
        "WHERE recipient_id = %s AND is_read = FALSE",
        (user_id,),
    )
    return result["total"]

__all__ = ["for_user", "unread_count"]
