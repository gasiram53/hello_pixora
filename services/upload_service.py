from pathlib import Path
from uuid import uuid4

from flask import current_app
from werkzeug.utils import secure_filename


def _matches_file_signature(extension, signature):
    image_signatures = {
        "jpg": signature.startswith(b"\xff\xd8\xff"),
        "jpeg": signature.startswith(b"\xff\xd8\xff"),
        "png": signature.startswith(b"\x89PNG\r\n\x1a\n"),
        "gif": signature.startswith((b"GIF87a", b"GIF89a")),
        "webp": signature.startswith(b"RIFF") and signature[8:12] == b"WEBP",
    }
    if extension in image_signatures:
        return image_signatures[extension]
    if extension in {"mp4", "mov"}:
        return signature[4:8] == b"ftyp"
    if extension == "webm":
        return signature.startswith(b"\x1aE\xdf\xa3")
    return False


def save_upload(file_storage, category, allowed_extensions, private=False):
    if not file_storage or not file_storage.filename:
        raise ValueError("Choose a file to upload.")
    original_name = secure_filename(file_storage.filename)
    if "." not in original_name:
        raise ValueError("The uploaded file must have a supported extension.")
    extension = original_name.rsplit(".", 1)[1].lower()
    if extension not in allowed_extensions:
        raise ValueError("This file type is not supported.")

    file_storage.stream.seek(0, 2)
    size = file_storage.stream.tell()
    file_storage.stream.seek(0)
    max_bytes = current_app.config.get("UPLOAD_MAX_BYTES", {}).get(
        category, 16 * 1024 * 1024
    )
    if size == 0:
        raise ValueError("The uploaded file is empty.")
    if size > max_bytes:
        raise ValueError(f"File exceeds the {max_bytes // (1024 * 1024)} MB upload limit.")
    signature = file_storage.stream.read(12)
    file_storage.stream.seek(0)
    if not _matches_file_signature(extension, signature):
        raise ValueError("The uploaded file content does not match its file type.")

    upload_root = (
        current_app.config["PRIVATE_UPLOAD_FOLDER"]
        if private
        else current_app.config["UPLOAD_FOLDER"]
    )
    destination = Path(upload_root) / category
    destination.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}.{extension}"
    file_storage.save(destination / filename)
    return f"{category}/{filename}" if private else f"uploads/{category}/{filename}"
