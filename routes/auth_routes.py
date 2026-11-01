import re

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from flask_wtf.csrf import CSRFError
from werkzeug.security import check_password_hash, generate_password_hash

from models import user_model
from routes.helpers import login_required
from services.email_service import send_otp_email
from services.otp_service import OtpRateLimitError, issue_otp, verify_otp

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def _send_code(user):
    code = issue_otp(user["id"])
    send_otp_email(user["email"], code)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        email = request.form.get("email", "").strip().lower()
        full_name = request.form.get("full_name", "").strip()
        password = request.form.get("password", "")
        if not re.fullmatch(r"[a-z0-9_]{3,30}", username):
            flash("Username must be 3–30 characters: letters, numbers, or underscores.", "error")
        elif not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            flash("Enter a valid email address.", "error")
        elif not full_name or len(full_name) > 80:
            flash("Enter your name (up to 80 characters).", "error")
        elif len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
        elif user_model.get_by_email(email) or user_model.get_by_username(username):
            flash("That username or email is already registered.", "error")
        else:
            user_id = user_model.create_user(
                username, email, generate_password_hash(password), full_name
            )
            session["pending_user_id"] = user_id
            try:
                _send_code({"id": user_id, "email": email})
            except OtpRateLimitError as exc:
                flash(str(exc), "error")
            except (RuntimeError, OSError) as exc:
                current_app.logger.exception("Could not send registration OTP.")
                flash(f"Account created, but the verification email could not be sent: {exc}", "error")
            else:
                flash("We sent a verification code to your email.", "success")
            return redirect(url_for("auth.verify_otp_route"))
    return render_template("auth/register.html")


@auth_bp.route("/verify", methods=["GET", "POST"])
def verify_otp_route():
    user_id = session.get("pending_user_id")
    if not user_id:
        return redirect(url_for("auth.register"))
    if request.method == "POST":
        code = request.form.get("code", "").strip()
        if verify_otp(user_id, code):
            user_model.verify_user(user_id)
            session.clear()
            session["user_id"] = user_id
            session["username"] = user_model.get_by_id(user_id)["username"]
            flash("Your email is verified. Welcome to PIXORA!", "success")
            return redirect(url_for("home.feed"))
        flash("That code is invalid or expired.", "error")
    return render_template("auth/verify_otp.html")


@auth_bp.post("/verify/resend")
def resend_otp():
    user_id = session.get("pending_user_id")
    user = user_model.get_by_id(user_id) if user_id else None
    if not user:
        flash("Start registration again to request a verification code.", "error")
        return redirect(url_for("auth.register"))
    try:
        _send_code(user)
    except OtpRateLimitError as exc:
        flash(str(exc), "error")
    except (RuntimeError, OSError) as exc:
        current_app.logger.exception("Could not resend verification OTP.")
        flash(f"Could not send the email: {exc}", "error")
    else:
        flash("A new verification code was sent.", "success")
    return redirect(url_for("auth.verify_otp_route"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = user_model.get_by_email(email)
        if not user or not check_password_hash(user["password_hash"], password):
            flash("Email or password is incorrect.", "error")
        elif not user["is_verified"]:
            session["pending_user_id"] = user["id"]
            flash("Verify your email before logging in.", "info")
            return redirect(url_for("auth.verify_otp_route"))
        else:
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            flash("Welcome back!", "success")
            return redirect(url_for("home.feed"))
    return render_template("auth/login.html")


@auth_bp.post("/logout")
@login_required
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = user_model.get_by_email(email)
        if user and user["is_verified"]:
            session["reset_user_id"] = user["id"]
            try:
                _send_code(user)
            except OtpRateLimitError as exc:
                flash(str(exc), "error")
                return render_template("auth/forgot_password.html")
            except (RuntimeError, OSError) as exc:
                current_app.logger.exception("Could not send password reset OTP.")
                flash(f"Could not send the reset email: {exc}", "error")
                return render_template("auth/forgot_password.html")
        flash("If that verified account exists, a reset code has been sent.", "info")
        return redirect(url_for("auth.reset_password"))
    return render_template("auth/forgot_password.html")


@auth_bp.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    user_id = session.get("reset_user_id")
    if not user_id:
        flash("Request a password reset code first, then use the link sent to your email.", "info")
        return redirect(url_for("auth.forgot_password"))
    if request.method == "POST":
        code = request.form.get("code", "").strip()
        password = request.form.get("password", "")
        if not verify_otp(user_id, code):
            flash("That code is invalid or expired.", "error")
        elif len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
        else:
            user_model.update_password(user_id, generate_password_hash(password))
            user_model.verify_user(user_id)
            session.pop("reset_user_id", None)
            flash("Password updated. You can now log in.", "success")
            return redirect(url_for("auth.login"))
    return render_template("auth/reset_password.html")


@auth_bp.errorhandler(CSRFError)
def handle_csrf_error(_error):
    flash("Your form expired. Please try again.", "error")
    return redirect(request.referrer or url_for("auth.login"))
