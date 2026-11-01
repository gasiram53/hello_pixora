import logging
from datetime import datetime, timedelta, timezone

from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)

from models.message_model import send_message
from models.story_model import (
    active_stories,
    create_story,
    delete_story,
    get_story_for_viewer,
    get_story_viewers,
    group_stories,
    get_owned_story,
    record_story_view,
)
from models.user_model import get_by_id
from routes.helpers import login_required
from services.upload_service import save_upload
from services.story_cleanup import cleanup_expired_story_media, delete_story_media

story_bp = Blueprint("stories", __name__, url_prefix="/stories")
logger = logging.getLogger(__name__)


def _validated_story_upload(file_storage):
    if not file_storage or not file_storage.filename:
        raise ValueError("Choose a photo or video to upload.")

    extension = file_storage.filename.rsplit(".", 1)[-1].lower()
    image_extensions = current_app.config["ALLOWED_IMAGE_EXTENSIONS"]
    video_extensions = current_app.config["ALLOWED_VIDEO_EXTENSIONS"]
    if extension not in image_extensions | video_extensions:
        raise ValueError("This photo or video type is not supported.")

    signature = file_storage.stream.read(12)
    file_storage.stream.seek(0)
    image_signatures = {
        "jpg": signature.startswith(b"\xff\xd8\xff"),
        "jpeg": signature.startswith(b"\xff\xd8\xff"),
        "png": signature.startswith(b"\x89PNG\r\n\x1a\n"),
        "gif": signature.startswith((b"GIF87a", b"GIF89a")),
        "webp": signature.startswith(b"RIFF") and signature[8:12] == b"WEBP",
    }
    video_signature = (
        extension in {"mp4", "mov"} and signature[4:8] == b"ftyp"
    ) or (extension == "webm" and signature.startswith(b"\x1aE\xdf\xa3"))
    valid_image = extension in image_extensions and image_signatures.get(extension, False)
    valid_video = extension in video_extensions and video_signature
    if not valid_image and not valid_video:
        raise ValueError("The uploaded file content does not match a supported photo or video.")

    path = save_upload(
        file_storage,
        "stories",
        image_extensions | video_extensions,
        private=True,
    )
    return path, "video" if valid_video else "image"


@story_bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "POST":
        caption = request.form.get("caption", "").strip()
        overlay_text = request.form.get("overlay_text", "").strip()
        if len(caption) > 500 or len(overlay_text) > 120:
            flash("Story captions are limited to 500 characters and overlays to 120.", "error")
        else:
            try:
                media_path, media_type = _validated_story_upload(request.files.get("media"))
            except ValueError as exc:
                flash(str(exc), "error")
            else:
                create_story(
                    session["user_id"],
                    media_path,
                    media_type,
                    caption,
                    overlay_text,
                    datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=24),
                )
                flash("Story shared for 24 hours.", "success")
                return redirect(url_for("stories.index"))

    cleanup_expired_story_media()
    stories = active_stories(session["user_id"])
    return render_template(
        "stories/stories.html",
        current_user=get_by_id(session["user_id"]),
        story_groups=group_stories(stories, session["user_id"]),
    )


@story_bp.post("/<int:story_id>/view")
@login_required
def view_story(story_id):
    story = get_story_for_viewer(story_id, session["user_id"])
    if not story:
        return jsonify({"error": "Story not found or unavailable."}), 404
    if story["user_id"] != session["user_id"]:
        record_story_view(story_id, session["user_id"])
    return jsonify({"viewed": True})


@story_bp.get("/<int:story_id>/media")
@login_required
def media(story_id):
    story = get_story_for_viewer(story_id, session["user_id"])
    if not story:
        return render_template("errors/404.html"), 404
    media_path = story["media_path"]
    if media_path.startswith("stories/"):
        directory = current_app.config["PRIVATE_UPLOAD_FOLDER"]
        relative_path = media_path
    elif media_path.startswith("uploads/stories/"):
        directory = current_app.config["UPLOAD_FOLDER"]
        relative_path = media_path.removeprefix("uploads/")
    else:
        logger.error("Story %s has an invalid media path.", story_id)
        return render_template("errors/404.html"), 404
    return send_from_directory(directory, relative_path, conditional=True)


@story_bp.get("/<int:story_id>/viewers")
@login_required
def viewers(story_id):
    if not get_owned_story(story_id, session["user_id"]):
        return jsonify({"error": "Story not found."}), 404
    viewers_list = get_story_viewers(story_id, session["user_id"])
    return jsonify(
        [
            {
                "username": viewer["username"],
                "full_name": viewer["full_name"],
                "avatar_url": url_for(
                    "static", filename=viewer["avatar_path"]
                )
                if viewer["avatar_path"]
                else None,
                "viewed_at": viewer["viewed_at"].isoformat(),
            }
            for viewer in viewers_list
        ]
    )


@story_bp.post("/<int:story_id>/delete")
@login_required
def remove_story(story_id):
    media_path = delete_story(story_id, session["user_id"])
    if not media_path:
        flash("Story not found or you do not own it.", "error")
        return redirect(url_for("stories.index"))

    delete_story_media(media_path)
    flash("Story deleted.", "success")
    return redirect(url_for("stories.index"))


@story_bp.post("/<int:story_id>/reply")
@login_required
def reply(story_id):
    story = get_story_for_viewer(story_id, session["user_id"])
    if not story:
        flash("Story not found or unavailable.", "error")
        return redirect(url_for("stories.index"))
    body = request.form.get("body", "").strip()
    if story["user_id"] == session["user_id"]:
        flash("You cannot reply to your own story.", "error")
    elif not body or len(body) > 2000:
        flash("Reply must be between 1 and 2,000 characters.", "error")
    else:
        send_message(session["user_id"], story["user_id"], body)
        flash("Story reply sent.", "success")
        return redirect(url_for("messages.index", user_id=story["user_id"]))
    return redirect(url_for("stories.index"))
