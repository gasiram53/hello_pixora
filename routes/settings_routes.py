import re

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from mysql.connector import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from database.queries import execute
from database.queries import fetch_one
from models import user_model
from routes.helpers import login_required

settings_bp = Blueprint("settings", __name__, url_prefix="/settings")


@settings_bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    user = get_user_for_id(session["user_id"])
    if not user:
        return render_template("errors/404.html"), 404
    if request.method == "POST":
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        if not check_password_hash(user["password_hash"], current_password):
            flash("Current password is incorrect.", "error")
        elif len(new_password) < 8:
            flash("New password must be at least 8 characters.", "error")
        else:
            execute(
                "UPDATE users SET password_hash = %s WHERE id = %s",
                (generate_password_hash(new_password), session["user_id"]),
            )
            flash("Password changed.", "success")
            return redirect(url_for("settings.index"))
    return render_template("settings/settings.html", account=user)


@settings_bp.post("/username")
@login_required
def update_username():
    user_id = session["user_id"]
    user = get_user_for_id(user_id)
    if not user:
        return render_template("errors/404.html"), 404

    username = request.form.get("username", "").strip().lower()
    current_password = request.form.get("current_password", "")
    if not re.fullmatch(r"[a-z0-9_]{3,30}", username):
        flash("Username must be 3–30 characters: letters, numbers, or underscores.", "error")
    elif not check_password_hash(user["password_hash"], current_password):
        flash("Current password is incorrect.", "error")
    else:
        existing_user = user_model.get_by_username(username)
        if existing_user and existing_user["id"] != user_id:
            flash("That username is already taken.", "error")
        elif username == user["username"]:
            flash("That is already your username.", "info")
        else:
            try:
                user_model.update_username(user_id, username)
            except IntegrityError:
                flash("That username is already taken.", "error")
            else:
                session["username"] = username
                flash("Username updated.", "success")
                return redirect(url_for("settings.index"))
    return redirect(url_for("settings.index"))


@settings_bp.post("/privacy")
@login_required
def update_privacy():
    is_private = request.form.get("is_private") == "1"
    execute(
        "UPDATE users SET is_private = %s WHERE id = %s",
        (is_private, session["user_id"]),
    )
    flash(
        "Your stories are now visible to followers only."
        if is_private
        else "Your stories are now visible to all signed-in users.",
        "success",
    )
    return redirect(url_for("settings.index"))


def get_user_for_id(user_id):
    return fetch_one(
        "SELECT username, email, password_hash, is_private FROM users WHERE id = %s",
        (user_id,),
    )
