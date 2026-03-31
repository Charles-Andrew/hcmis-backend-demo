from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import ConflictError


@dataclass
class StoredResourceFile:
    storage_key: str
    original_filename: str
    content_type: str | None
    size_bytes: int


ALLOWED_DOCUMENT_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".txt",
    ".csv",
}
ALLOWED_MEDIA_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".webp",
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".webm",
    ".mp3",
    ".wav",
    ".m4a",
    ".aac",
    ".ogg",
}
ALLOWED_EXTENSIONS = ALLOWED_DOCUMENT_EXTENSIONS | ALLOWED_MEDIA_EXTENSIONS
ALLOWED_EXACT_MIME_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "text/plain",
    "text/csv",
    "application/octet-stream",
}


def _storage_root() -> Path:
    return Path(settings.shared_resources_storage_dir).resolve()


def _resolve_storage_path(storage_key: str) -> Path:
    base = _storage_root()
    path = (base / storage_key).resolve()
    if base != path and base not in path.parents:
        raise ValueError("Invalid storage key.")
    return path


def _max_size_bytes() -> int:
    return int(settings.shared_resources_max_file_size_mb) * 1024 * 1024


def validate_uploaded_resource_file(uploaded_file: UploadFile) -> str:
    filename = Path(uploaded_file.filename or "").name
    if not filename:
        raise ConflictError("Uploaded file must have a filename.")

    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ConflictError(
            "Unsupported file type. Allowed: document files and media files only."
        )

    content_type = (uploaded_file.content_type or "").lower().strip()
    if content_type and not (
        content_type in ALLOWED_EXACT_MIME_TYPES
        or content_type.startswith("image/")
        or content_type.startswith("video/")
        or content_type.startswith("audio/")
    ):
        raise ConflictError("Unsupported content type for uploaded file.")
    return filename


async def save_uploaded_resource_file(
    uploader_id: int,
    uploaded_file: UploadFile,
) -> StoredResourceFile:
    original_filename = validate_uploaded_resource_file(uploaded_file)
    extension = Path(original_filename).suffix.lower()[:20]
    storage_key = f"{uploader_id}/{uuid4().hex}{extension}"

    file_path = _resolve_storage_path(storage_key)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    total_size = 0
    try:
        with file_path.open("wb") as handle:
            while True:
                chunk = uploaded_file.file.read(1024 * 1024)
                if not chunk:
                    break
                total_size += len(chunk)
                if total_size > _max_size_bytes():
                    raise ConflictError(
                        f"File size exceeded limit ({settings.shared_resources_max_file_size_mb} MB)."
                    )
                handle.write(chunk)
    except Exception:
        if file_path.exists():
            file_path.unlink()
        raise

    return StoredResourceFile(
        storage_key=storage_key,
        original_filename=original_filename,
        content_type=uploaded_file.content_type,
        size_bytes=total_size,
    )


def delete_stored_resource_file(storage_key: str) -> None:
    file_path = _resolve_storage_path(storage_key)
    if file_path.exists() and file_path.is_file():
        file_path.unlink()


def get_stored_resource_file_path(storage_key: str) -> Path:
    return _resolve_storage_path(storage_key)
