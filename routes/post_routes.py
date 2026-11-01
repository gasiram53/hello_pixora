from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.utils import secure_filename

from models.comment_model import add_comment, get_for_post
from models.like_model import count_for_post, toggle_like
from models.post_model import create_post, delete_post as remove_post, get_by_id, toggle_save
from routes.helpers import login_required
from services.notification_service import create as create_notification
from services.upload_service import save_upload

post_bp = Blueprint("posts", __name__, url_prefix="/posts")


@post_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        caption = request.form.get("caption", "").strip()
        if len(caption) > 2200:
            flash("Caption is too long (maximum 2,200 characters).", "error")
        else:
            try:
                media = request.files.get("media") or request.files.get("image")
                extension = secure_filename(media.filename).rsplit(".", 1)[-1].lower() if media and media.filename else ""
                media_type = (
                    "video"
                    if extension in current_app.config["ALLOWED_VIDEO_EXTENSIONS"]
                    else "image"
                )
                media_path = save_upload(
                    media,
                    "posts",
                    current_app.config["ALLOWED_IMAGE_EXTENSIONS"]
                    | current_app.config["ALLOWED_VIDEO_EXTENSIONS"],
                )
            except ValueError as exc:
                flash(str(exc), "error")
            else:
                create_post(session["user_id"], media_path, caption, media_type)
                flash("Your post was published.", "success")
                return redirect(url_for("home.feed"))
    return render_template("posts/create_post.html")


@post_bp.get("/<int:post_id>")
@login_required
def view(post_id):
    post = get_by_id(post_id)
    if not post:
        return render_template("errors/404.html"), 404
    return render_template(
        "posts/view_post.html",
        post=post,
        comments=get_for_post(post_id),
        like_count=count_for_post(post_id),
    )


@post_bp.post("/<int:post_id>/like")
@login_required
def like(post_id):
    post = get_by_id(post_id)
    if not post:
        return render_template("errors/404.html"), 404
    liked = toggle_like(session["user_id"], post_id)
    if liked:
        create_notification(post["user_id"], session["user_id"], "like", post_id)
    return redirect(request.referrer or url_for("posts.view", post_id=post_id))


@post_bp.post("/<int:post_id>/save")
@login_required
def save(post_id):
    if not get_by_id(post_id):
        return jsonify({"error": "Post not found."}), 404
    return jsonify({"saved": toggle_save(session["user_id"], post_id)})


@post_bp.post("/<int:post_id>/comment")
@login_required
def comment(post_id):
    post = get_by_id(post_id)
    body = request.form.get("body", "").strip()
    if not post:
        return render_template("errors/404.html"), 404
    if not body or len(body) > 1000:
        flash("Comment must be between 1 and 1,000 characters.", "error")
    else:
        add_comment(session["user_id"], post_id, body)
        create_notification(post["user_id"], session["user_id"], "comment", post_id)
    return redirect(url_for("posts.view", post_id=post_id))


@post_bp.post("/<int:post_id>/delete")
@login_required
def delete(post_id):
    removed = remove_post(post_id, session["user_id"])
    if not removed:
        flash("Post not found or you do not own it.", "error")
    else:
        flash("Post deleted.", "success")
    return redirect(url_for("home.feed"))
