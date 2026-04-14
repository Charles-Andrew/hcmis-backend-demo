from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID, uuid4

from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import ConflictError


@dataclass
class StoredTrainingAttachment:
    storage_key: str
    original_filename: str
    content_type: str | None
    size_bytes: int


def _max_size_bytes() -> int:
    return int(settings.training_attachments_max_file_size_mb) * 1024 * 1024


def _build_s3_client():
    try:
        import boto3
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("boto3 is required for training attachment storage.") from exc

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


def _build_s3_storage_key(user_id: UUID, extension: str) -> str:
    prefix = settings.training_attachments_s3_prefix.strip().strip("/")
    suffix = f"{user_id}/{uuid4().hex}{extension}"
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
                f"File size exceeded limit ({settings.training_attachments_max_file_size_mb} MB)."
            )
        chunks.append(chunk)
    return b"".join(chunks), total_size


def validate_training_attachment_file(uploaded_file: UploadFile) -> str:
    filename = Path(uploaded_file.filename or "").name
    if not filename:
        raise ConflictError("Uploaded file must have a filename.")
    return filename


async def save_uploaded_training_attachment(
    user_id: UUID,
    uploaded_file: UploadFile,
) -> StoredTrainingAttachment:
    original_filename = validate_training_attachment_file(uploaded_file)
    extension = Path(original_filename).suffix.lower()[:20]
    bucket = settings.training_attachments_s3_bucket.strip()
    if not bucket:
        raise RuntimeError("TRAINING_ATTACHMENTS_S3_BUCKET must be configured.")

    data, total_size = _read_upload_bytes(uploaded_file)
    storage_key = _build_s3_storage_key(user_id, extension)
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
    return StoredTrainingAttachment(
        storage_key=storage_key,
        original_filename=original_filename,
        content_type=uploaded_file.content_type,
        size_bytes=total_size,
    )


def delete_training_attachment_file(storage_key: str) -> None:
    bucket = settings.training_attachments_s3_bucket.strip()
    if not bucket or not storage_key:
        return
    client = _build_s3_client()
    client.delete_object(Bucket=bucket, Key=storage_key)
