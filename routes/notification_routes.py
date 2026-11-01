from flask import Blueprint, redirect, render_template, session, url_for

from database.queries import execute
from models.notification_model import for_user
from routes.helpers import login_required

notification_bp = Blueprint("notifications", __name__, url_prefix="/notifications")


@notification_bp.get("/")
@login_required
def index():
    return render_template(
        "notifications/notifications.html",
        notifications=for_user(session["user_id"]),
    )


@notification_bp.post("/read")
@login_required
def mark_read():
    execute(
        "UPDATE notifications SET is_read = TRUE WHERE recipient_id = %s",
        (session["user_id"],),
    )
    return redirect(url_for("notifications.index"))
