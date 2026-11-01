from io import BytesIO

import qrcode
from flask import Blueprint, current_app, flash, redirect, render_template, request, send_file, session, url_for
from mysql.connector import IntegrityError
from urllib.parse import urlparse, urlsplit

from database.queries import execute, fetch_one
from models.follow_model import counts, get_followers, get_following, is_following, toggle_follow
from models.post_model import get_by_user, get_saved_by_user, post_count
from models.user_model import get_by_id, get_by_username, update_profile
from routes.helpers import login_required
from services.notification_service import create as create_notification
from services.upload_service import save_upload

profile_bp = Blueprint("profile", __name__, url_prefix="/profile")


@profile_bp.get("/")
@login_required
def index():
    user = get_by_id(session["user_id"])
    if not user:
        return render_template("errors/404.html"), 404
    return redirect(url_for("profile.view_profile", username=user["username"]))


@profile_bp.get("/<username>")
@login_required
def view_profile(username):
    user = get_by_username(username)
    if not user:
        return render_template("errors/404.html"), 404
    viewer_id = session["user_id"]
    followers, following = counts(user["id"])
    return render_template(
        "profile/profile.html",
        profile_user=user,
        posts=get_by_user(user["id"], viewer_id),
        follower_count=followers,
        following_count=following,
        is_following=is_following(viewer_id, user["id"]),
        is_self=viewer_id == user["id"],
    )


@profile_bp.get("/<username>/qr")
@login_required
def profile_qr(username):
    user = get_by_username(username)
    if not user:
        return render_template("errors/404.html"), 404
    profile_url = url_for("profile.view_profile", username=user["username"], _external=True)
    image = qrcode.make(profile_url)
    output = BytesIO()
    image.save(output, format="PNG")
    output.seek(0)
    return send_file(
        output,
        mimetype="image/png",
        download_name=f"pixora-{user['username']}-qr.png",
        max_age=3600,
    )


@profile_bp.post("/<username>/report")
@login_required
def report_user(username):
    target = get_by_username(username)
    if not target:
        return render_template("errors/404.html"), 404
    if target["id"] == session["user_id"]:
        return render_template("errors/404.html"), 404

    reason = request.form.get("reason", "").strip()
    details = request.form.get("details", "").strip()
    if reason not in {"spam", "harassment", "impersonation", "inappropriate", "other"} or len(details) > 500:
        flash("Choose a valid report reason and keep details under 500 characters.", "error")
        return redirect(url_for("profile.view_profile", username=username))

    existing_report = fetch_one(
        "SELECT id FROM user_reports WHERE reporter_id = %s AND reported_user_id = %s",
        (session["user_id"], target["id"]),
    )
    if existing_report:
        flash("You have already reported this account.", "info")
        return redirect(url_for("profile.view_profile", username=username))
    try:
        execute(
            "INSERT INTO user_reports (reporter_id, reported_user_id, reason, details) "
            "VALUES (%s, %s, %s, %s)",
            (session["user_id"], target["id"], reason, details),
        )
    except IntegrityError:
        flash("You have already reported this account.", "info")
    else:
        current_app.logger.info(
            "User report submitted: reporter_id=%s reported_user_id=%s",
            session["user_id"],
            target["id"],
        )
        flash("Thanks for helping keep PIXORA safe. Your report was submitted.", "success")
    return redirect(url_for("profile.view_profile", username=username))


@profile_bp.route("/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    user = get_by_id(session["user_id"])
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        bio = request.form.get("bio", "").strip()
        website = request.form.get("website", "").strip()
        avatar = request.files.get("avatar")
        if not full_name or len(full_name) > 80 or len(bio) > 300 or len(website) > 255:
            flash("Name is required (up to 80 characters), bio is limited to 300, and website to 255.", "error")
        else:
            try:
                if website:
                    initial_website = urlparse(website)
                    if initial_website.scheme and initial_website.scheme not in {"https", "http"}:
                        raise ValueError("Enter a valid website URL.")
                    if not initial_website.scheme:
                        website = f"https://{website}"
                    parsed_website = urlparse(website)
                    if (
                        parsed_website.scheme not in {"https", "http"}
                        or not parsed_website.hostname
                        or parsed_website.username
                        or parsed_website.password
                        or any(character.isspace() for character in website)
                    ):
                        raise ValueError("Enter a valid website URL.")
                    try:
                        parsed_website.port
                    except ValueError as exc:
                        raise ValueError("Enter a valid website URL.") from exc
                avatar_path = None
                if avatar and avatar.filename:
                    avatar_path = save_upload(
                        avatar,
                        "profile_pictures",
                        current_app.config["ALLOWED_IMAGE_EXTENSIONS"],
                    )
                update_profile(session["user_id"], full_name, bio, avatar_path, website)
            except ValueError as exc:
                flash(str(exc), "error")
            else:
                flash("Profile updated.", "success")
                return redirect(url_for("profile.view_profile", username=user["username"]))
    return render_template("profile/edit_profile.html", profile_user=user)


@profile_bp.post("/<username>/follow")
@login_required
def follow(username):
    target = get_by_username(username)
    if not target:
        return render_template("errors/404.html"), 404
    try:
        followed = toggle_follow(session["user_id"], target["id"])
    except ValueError as exc:
        flash(str(exc), "error")
    else:
        if followed:
            create_notification(target["id"], session["user_id"], "follow")
    next_url = request.form.get("next", "")
    next_parts = urlsplit(next_url)
    if (
        next_parts.scheme == ""
        and next_parts.netloc == ""
        and next_parts.path.startswith("/")
        and not next_parts.path.startswith("//")
        and "\\" not in next_parts.path
    ):
        return redirect(next_url)
    return redirect(url_for("profile.view_profile", username=username))


@profile_bp.get("/<username>/followers")
@login_required
def followers(username):
    user = get_by_username(username)
    if not user:
        return render_template("errors/404.html"), 404
    return render_template(
        "profile/followers.html", profile_user=user, followers=get_followers(user["id"])
    )


@profile_bp.get("/<username>/following")
@login_required
def following(username):
    user = get_by_username(username)
    if not user:
        return render_template("errors/404.html"), 404
    return render_template(
        "profile/following.html",
        profile_user=user,
        following=get_following(user["id"]),
    )


@profile_bp.get("/saved")
@login_required
def saved_posts():
    user = get_by_id(session["user_id"])
    if not user:
        return render_template("errors/404.html"), 404
    followers, following_count = counts(user["id"])
    return render_template(
        "profile/profile.html",
        profile_user=user,
        posts=get_saved_by_user(user["id"]),
        follower_count=followers,
        following_count=following_count,
        is_following=True,
        is_self=True,
        active_tab="saved",
        profile_post_count=post_count(user["id"]),
    )
