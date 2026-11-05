from flask import Blueprint, render_template, session, current_app

from models.post_model import get_feed
from models.story_model import active_stories, group_stories
from models.user_model import get_by_id
from routes.helpers import login_required
from services.story_cleanup import cleanup_expired_story_media

home_bp = Blueprint("home", __name__)


@home_bp.get("/feed")
@login_required
def feed():
    user_id = session.get("user_id")

    try:
        current_app.logger.info("FEED DEBUG: Starting feed for user %s", user_id)

        current_app.logger.info("FEED DEBUG: Cleaning expired stories")
        cleanup_expired_story_media()

        current_app.logger.info("FEED DEBUG: Loading posts")
        posts = get_feed(user_id)

        current_app.logger.info("FEED DEBUG: Loading current user")
        current_user = get_by_id(user_id)

        current_app.logger.info("FEED DEBUG: Loading active stories")
        stories = active_stories(user_id)

        current_app.logger.info("FEED DEBUG: Grouping stories")
        story_groups = group_stories(stories, user_id)

        current_app.logger.info("FEED DEBUG: Rendering template")

        return render_template(
            "home/feed.html",
            posts=posts,
            current_user=current_user,
            story_groups=story_groups,
        )

    except Exception:
        current_app.logger.exception(
            "PIXORA FEED ERROR for user_id=%s", user_id
        )
        raise