import logging
import shutil
from pathlib import Path

from flask import current_app
from mysql.connector import Error

from models.story_model import (
    delete_expired_story,
    get_expired_stories,
    get_legacy_story_media,
    update_story_media_path,
)

logger = logging.getLogger(__name__)


def cleanup_expired_story_media():
    upload_root = Path(current_app.config["UPLOAD_FOLDER"]).resolve()
    story_root = (upload_root / "stories").resolve()
    private_root = Path(current_app.config["PRIVATE_UPLOAD_FOLDER"]).resolve()
    for story in get_expired_stories():
        if _remove_story_media(
            story["media_path"], upload_root, story_root, private_root
        ):
            delete_expired_story(story["id"])

    private_story_root = private_root / "stories"
    private_story_root.mkdir(parents=True, exist_ok=True)
    for story in get_legacy_story_media():
        old_path = story["media_path"]
        source = (upload_root / old_path.removeprefix("uploads/")).resolve()
        if not source.is_relative_to(story_root):
            logger.warning("Skipped legacy story media outside its directory: %s", old_path)
            continue
        if not source.is_file():
            logger.warning("Legacy story media is missing: %s", old_path)
            continue
        destination = private_story_root / source.name
        try:
            if source != destination:
                shutil.move(str(source), str(destination))
            new_path = f"stories/{destination.name}"
        except OSError:
            logger.exception("Could not privatize legacy story media: %s", old_path)
            continue
        try:
            update_story_media_path(story["id"], old_path, new_path)
        except (Error, RuntimeError):
            if source != destination and destination.exists():
                try:
                    shutil.move(str(destination), str(source))
                except OSError:
                    logger.exception(
                        "Could not restore legacy story media after a database error: %s",
                        old_path,
                    )
            raise


def _remove_story_media(media_path, upload_root, story_root, private_root):
    if media_path.startswith("uploads/stories/"):
        root = story_root
        media_file = (upload_root / media_path.removeprefix("uploads/")).resolve()
    elif media_path.startswith("stories/"):
        root = (private_root / "stories").resolve()
        media_file = (private_root / media_path).resolve()
    else:
        logger.warning("Skipped story media with unexpected path: %s", media_path)
        return False
    if not media_file.is_relative_to(root):
        logger.warning("Skipped story media outside its directory: %s", media_path)
        return False
    try:
        media_file.unlink(missing_ok=True)
        return True
    except OSError:
        logger.exception("Could not remove story media file: %s", media_path)
        return False


def delete_story_media(media_path):
    upload_root = Path(current_app.config["UPLOAD_FOLDER"]).resolve()
    _remove_story_media(
        media_path,
        upload_root,
        (upload_root / "stories").resolve(),
        Path(current_app.config["PRIVATE_UPLOAD_FOLDER"]).resolve(),
    )
