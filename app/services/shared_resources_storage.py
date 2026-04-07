from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from urllib.parse import quote, urlparse
from uuid import UUID, uuid4

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


def _max_size_bytes() -> int:
    return int(settings.shared_resources_max_file_size_mb) * 1024 * 1024


def _build_s3_client():
    try:
        import boto3
    except ImportError as exc:  # pragma: no cover - defensive guard
        raise RuntimeError("boto3 is required for S3 shared resource storage.") from exc

    from botocore.config import Config

    endpoint_url = (settings.supabase_storage_endpoint_url or "").strip() or None
    addressing_style = "path" if _is_supabase_s3_endpoint(endpoint_url) else "auto"
    client_kwargs = {
        "region_name": settings.supabase_storage_region,
        "config": Config(signature_version="s3v4", s3={"addressing_style": addressing_style}),
    }

    if endpoint_url:
        client_kwargs["endpoint_url"] = endpoint_url

    if settings.supabase_storage_access_key_id:
        client_kwargs["aws_access_key_id"] = settings.supabase_storage_access_key_id

    if settings.supabase_storage_secret_access_key:
        client_kwargs["aws_secret_access_key"] = settings.supabase_storage_secret_access_key

    return boto3.client("s3", **client_kwargs)


def _build_s3_storage_key(uploader_id: UUID, extension: str) -> str:
    prefix = settings.shared_resources_s3_prefix.strip().strip("/")
    suffix = f"{uploader_id}/{uuid4().hex}{extension}"
    return f"{prefix}/{suffix}" if prefix else suffix


def _is_supabase_s3_endpoint(endpoint_url: str | None) -> bool:
    if not endpoint_url:
        return False
    parsed = urlparse(endpoint_url)
    return (
        parsed.scheme in {"http", "https"}
        and parsed.netloc.endswith(".storage.supabase.co")
        and parsed.path.rstrip("/").endswith("/storage/v1/s3")
    )


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


def _read_upload_bytes(uploaded_file: UploadFile) -> tuple[bytes, int]:
    total_size = 0
    chunks: list[bytes] = []
    while True:
        chunk = uploaded_file.file.read(1024 * 1024)
        if not chunk:
            break
        total_size += len(chunk)
        if total_size > _max_size_bytes():
            raise ConflictError(
                f"File size exceeded limit ({settings.shared_resources_max_file_size_mb} MB)."
            )
        chunks.append(chunk)
    return b"".join(chunks), total_size


async def save_uploaded_resource_file(
    uploader_id: UUID,
    uploaded_file: UploadFile,
) -> StoredResourceFile:
    original_filename = validate_uploaded_resource_file(uploaded_file)
    extension = Path(original_filename).suffix.lower()[:20]

    bucket = settings.shared_resources_s3_bucket.strip()
    if not bucket:
        raise RuntimeError("SHARED_RESOURCES_S3_BUCKET must be configured.")

    data, total_size = _read_upload_bytes(uploaded_file)
    storage_key = _build_s3_storage_key(uploader_id, extension)
    client = _build_s3_client()

    put_kwargs = {
        "Bucket": bucket,
        "Key": storage_key,
        "Body": BytesIO(data),
        "ContentDisposition": f'attachment; filename="{original_filename}"',
    }
    if uploaded_file.content_type:
        put_kwargs["ContentType"] = uploaded_file.content_type

    client.put_object(**put_kwargs)

    return StoredResourceFile(
        storage_key=storage_key,
        original_filename=original_filename,
        content_type=uploaded_file.content_type,
        size_bytes=total_size,
    )


def delete_stored_resource_file(storage_key: str) -> None:
    bucket = settings.shared_resources_s3_bucket.strip()
    if not bucket:
        return

    client = _build_s3_client()
    client.delete_object(Bucket=bucket, Key=storage_key)


def get_stored_resource_download_url(
    storage_key: str,
    *,
    original_filename: str,
    content_type: str | None,
) -> str:
    bucket = settings.shared_resources_s3_bucket.strip()
    if not bucket:
        raise FileNotFoundError("Stored file not found.")

    expires_in = max(60, int(settings.shared_resources_signed_url_ttl_seconds))
    client = _build_s3_client()
    params = {
        "Bucket": bucket,
        "Key": storage_key,
        "ResponseContentDisposition": (
            f"attachment; filename*=UTF-8''{quote(original_filename)}"
        ),
    }
    if content_type:
        params["ResponseContentType"] = content_type

    return str(
        client.generate_presigned_url(
            ClientMethod="get_object",
            Params=params,
            ExpiresIn=expires_in,
        )
    )
