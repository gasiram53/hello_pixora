from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, send_from_directory, session, url_for

from models.message_model import (
    get_conversation,
    get_conversations,
    get_message_media_path,
    get_new_messages,
    send_message,
    mark_conversation_read,
)
from models.user_model import get_by_id, search_users
from routes.helpers import login_required
from services.realtime import socketio
from services.notification_service import create as create_notification
from services.upload_service import save_upload

message_bp = Blueprint("messages", __name__, url_prefix="/messages")


@message_bp.get("/people")
@login_required
def people():
    term = request.args.get("q", "").strip()[:80]
    people = search_users(term, session["user_id"]) if term else []
    return jsonify(
        [
            {
                "id": person["id"],
                "username": person["username"],
                "full_name": person["full_name"],
                "avatar_path": person["avatar_path"],
            }
            for person in people
        ]
    )


@message_bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    other_id = request.values.get("user_id", type=int)
    if request.method == "POST":
        body = request.form.get("body", "").strip()
        media = request.files.get("media")
        recipient = get_by_id(other_id) if other_id else None
        sender = get_by_id(session["user_id"])
        if not recipient or not sender or other_id == session["user_id"]:
            flash("Choose a valid recipient.", "error")
        elif len(body) > 2000 or (not body and not (media and media.filename)):
            flash("Add a message or attach a photo. Text is limited to 2,000 characters.", "error")
        else:
            try:
                media_path = (
                    save_upload(
                        media,
                        "messages",
                        current_app.config["ALLOWED_IMAGE_EXTENSIONS"],
                        private=True,
                    )
                    if media and media.filename
                    else None
                )
            except ValueError as exc:
                flash(str(exc), "error")
            else:
                message_id = send_message(
                    session["user_id"], other_id, body, media_path
                )
                create_notification(other_id, session["user_id"], "message")
                socketio.emit(
                    "new_message",
                    {
                        "id": message_id,
                        "sender_id": session["user_id"],
                        "sender_username": sender["username"],
                        "body": body,
                        "media_url": url_for("messages.media", message_id=message_id)
                        if media_path
                        else None,
                        "created_at": "Just now",
                    },
                    to=f"user:{other_id}",
                    namespace="/messages",
                )
                return redirect(url_for("messages.index", user_id=other_id))

    recipient = get_by_id(other_id) if other_id else None
    if recipient and other_id != session["user_id"]:
        mark_conversation_read(session["user_id"], other_id)
    thread = get_conversation(session["user_id"], other_id) if recipient else []
    return render_template(
        "messages/messages.html",
        current_user=get_by_id(session["user_id"]),
        recipient=recipient,
        thread=thread,
        conversations=get_conversations(session["user_id"]),
        active_user_id=session["user_id"],
    )


@message_bp.get("/media/<int:message_id>")
@login_required
def media(message_id):
    media_path = get_message_media_path(message_id, session["user_id"])
    if not media_path:
        return render_template("errors/404.html"), 404
    return send_from_directory(
        current_app.config["PRIVATE_UPLOAD_FOLDER"],
        media_path,
        conditional=True,
    )


@message_bp.get("/<int:other_id>/updates")
@login_required
def updates(other_id):
    user_id = session["user_id"]
    if other_id == user_id or not get_by_id(other_id):
        return jsonify({"error": "Conversation not found."}), 404
    after_id = max(request.args.get("after_id", 0, type=int), 0)
    messages = get_new_messages(user_id, other_id, after_id)
    mark_conversation_read(user_id, other_id)
    return jsonify(
        [
            {
                "id": message["id"],
                "sender_id": message["sender_id"],
                "sender_username": message["sender_username"],
                "body": message["body"],
                "media_url": url_for("messages.media", message_id=message["id"])
                if message["media_path"]
                else None,
                "created_at": message["created_at"].isoformat()
                if message["created_at"]
                else "",
            }
            for message in messages
        ]
    )
