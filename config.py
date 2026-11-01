import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    if not SECRET_KEY:
        raise RuntimeError("SECRET_KEY must be configured in the environment.")

    MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "pixora")
    MAX_CONTENT_LENGTH = 21 * 1024 * 1024
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
    UPLOAD_FOLDER = os.getenv(
        "UPLOAD_FOLDER", str(Path(__file__).parent / "static" / "uploads")
    )
    PRIVATE_UPLOAD_FOLDER = os.getenv(
        "PRIVATE_UPLOAD_FOLDER", str(Path(__file__).parent / "private_uploads")
    )
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
    ALLOWED_VIDEO_EXTENSIONS = {"mp4", "webm", "mov"}
    UPLOAD_MAX_BYTES = {
        "posts": 20 * 1024 * 1024,
        "reels": 20 * 1024 * 1024,
        "stories": 16 * 1024 * 1024,
        "profile_pictures": 5 * 1024 * 1024,
        "messages": 10 * 1024 * 1024,
    }
    SMTP_HOST = os.getenv("SMTP_HOST")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
    MAIL_FROM = os.getenv("MAIL_FROM", SMTP_USER or "")
    DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
