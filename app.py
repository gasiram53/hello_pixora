from pathlib import Path

from flask import Flask, render_template, session
from flask_wtf.csrf import CSRFProtect

from config import Config
from database.db_connection import close_db
from routes.auth_routes import auth_bp
from routes.home_routes import home_bp
from routes.message_routes import message_bp
from routes.notification_routes import notification_bp
from routes.post_routes import post_bp
from routes.profile_routes import profile_bp
from routes.reel_routes import reel_bp
from routes.search_routes import search_bp
from routes.settings_routes import settings_bp
from routes.story_routes import story_bp
from models.message_model import unread_message_count
from models.notification_model import unread_count
from models.user_model import get_by_id
from services.realtime import socketio


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    socketio.init_app(app)
    CSRFProtect(app)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["PRIVATE_UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    app.teardown_appcontext(close_db)

    @app.context_processor
    def navigation_context():
        user_id = session.get("user_id")
        if not user_id:
            return {"navigation_user": None, "unread_notifications": 0, "unread_messages": 0}
        if app.testing:
            return {
                "navigation_user": {
                    "username": session.get("username", ""),
                    "full_name": session.get("username", ""),
                    "avatar_path": None,
                },
                "unread_notifications": 0,
                "unread_messages": 0,
            }
        return {
            "navigation_user": get_by_id(user_id),
            "unread_notifications": unread_count(user_id),
            "unread_messages": unread_message_count(user_id),
        }

    for blueprint in (
        auth_bp,
        home_bp,
        profile_bp,
        post_bp,
        story_bp,
        reel_bp,
        search_bp,
        message_bp,
        notification_bp,
        settings_bp,
    ):
        app.register_blueprint(blueprint)

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.errorhandler(404)
    def not_found(_):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(_):
        return render_template("errors/500.html"), 500

    return app


app = create_app()

if __name__ == "__main__":
    socketio.run(app, debug=app.config["DEBUG"])
