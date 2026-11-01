from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for

from models.reel_model import (
    add_comment,
    create_reel,
    get_comments_for_reels,
    get_reel,
    get_reels,
    toggle_like,
    toggle_save,
)
from routes.helpers import login_required
from services.upload_service import save_upload

reel_bp = Blueprint("reels", __name__, url_prefix="/reels")


@reel_bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "POST":
        caption = request.form.get("caption", "").strip()
        if len(caption) > 2200:
            flash("Caption is too long (maximum 2,200 characters).", "error")
        else:
            try:
                path = save_upload(
                    request.files.get("video"),
                    "reels",
                    current_app.config["ALLOWED_VIDEO_EXTENSIONS"],
                )
            except ValueError as exc:
                flash(str(exc), "error")
            else:
                create_reel(session["user_id"], path, caption)
                flash("Your reel was published.", "success")
                return redirect(url_for("reels.index"))
    reels = get_reels(session["user_id"])
    comments_by_reel = {}
    for comment in get_comments_for_reels([reel["id"] for reel in reels]):
        comments_by_reel.setdefault(comment["reel_id"], []).append(comment)
    return render_template(
        "reels/reels.html",
        reels=reels,
        comments_by_reel=comments_by_reel,
    )


@reel_bp.post("/<int:reel_id>/like")
@login_required
def like(reel_id):
    if not get_reel(reel_id):
        return render_template("errors/404.html"), 404
    toggle_like(session["user_id"], reel_id)
    return redirect(url_for("reels.index", _anchor=f"reel-{reel_id}"))


@reel_bp.post("/<int:reel_id>/save")
@login_required
def save(reel_id):
    if not get_reel(reel_id):
        return render_template("errors/404.html"), 404
    toggle_save(session["user_id"], reel_id)
    return redirect(url_for("reels.index", _anchor=f"reel-{reel_id}"))


@reel_bp.post("/<int:reel_id>/comment")
@login_required
def comment(reel_id):
    if not get_reel(reel_id):
        return render_template("errors/404.html"), 404
    body = request.form.get("body", "").strip()
    if not body or len(body) > 1000:
        flash("Comment must be between 1 and 1,000 characters.", "error")
    else:
        add_comment(session["user_id"], reel_id, body)
    return redirect(
        url_for("reels.index", _anchor=f"comments-{reel_id}")
    )
