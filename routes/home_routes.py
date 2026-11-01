from flask import Blueprint, render_template, session

from models.post_model import get_feed
from models.story_model import active_stories, group_stories
from models.user_model import get_by_id
from routes.helpers import login_required
from services.story_cleanup import cleanup_expired_story_media

home_bp = Blueprint("home", __name__)


@home_bp.get("/feed")
@login_required
def feed():
    user_id = session["user_id"]
    cleanup_expired_story_media()
    return render_template(
        "home/feed.html",
        posts=get_feed(user_id),
        current_user=get_by_id(user_id),
        story_groups=group_stories(active_stories(user_id), user_id),
    )
