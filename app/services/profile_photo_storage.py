from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

from fastapi import UploadFile
from botocore.exceptions import ClientError

from app.core.config import settings
from app.core.exceptions import ConflictError


@dataclass
class StoredProfilePhoto:
    storage_key: str
    url: str
    content_type: str | None
    size_bytes: int


ALLOWED_PROFILE_PHOTO_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".bmp",
}


def _profile_backend() -> str:
    return settings.profile_photos_storage_backend.strip().lower()


def _max_size_bytes() -> int:
    return int(settings.profile_photos_max_file_size_mb) * 1024 * 1024


def _filesystem_storage_root() -> Path:
    return Path(settings.profile_photos_storage_dir).resolve()


def _resolve_filesystem_path(storage_key: str) -> Path:
    base = _filesystem_storage_root()
    path = (base / storage_key).resolve()
    if base != path and base not in path.parents:
        raise ValueError("Invalid storage key.")
    return path


def _normalize_public_base_url(raw_value: str | None, *, fallback: str) -> str:
    base = (raw_value or "").strip()
    if not base:
        base = fallback
    return base.rstrip("/")


def _build_filesystem_photo_url(storage_key: str, request_base_url: str) -> str:
    configured_base = (settings.profile_photos_public_base_url or "").strip()
    base_url = _normalize_public_base_url(
        configured_base,
        fallback=request_base_url,
    )
    return f"{base_url}/profile/photos/{storage_key}"


def _validate_upload(uploaded_file: UploadFile) -> str:
    filename = Path(uploaded_file.filename or "").name
    if not filename:
        raise ConflictError("Uploaded file must have a filename.")

    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_PROFILE_PHOTO_EXTENSIONS:
        raise ConflictError("Unsupported image format.")

    content_type = (uploaded_file.content_type or "").strip().lower()
    if content_type and not content_type.startswith("image/"):
        raise ConflictError("Unsupported content type for profile photo.")

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
                f"File size exceeded limit ({settings.profile_photos_max_file_size_mb} MB)."
            )
        chunks.append(chunk)

    return b"".join(chunks), total_size


def _build_s3_client():
    try:
        import boto3
    except ImportError as exc:  # pragma: no cover - defensive guard
        raise RuntimeError("boto3 is required for S3 profile photo storage.") from exc

    from botocore.config import Config

    endpoint_url = (settings.profile_photos_s3_endpoint_url or "").strip() or None
    addressing_style = "path" if _is_supabase_s3_endpoint(endpoint_url) else "auto"
    client_kwargs = {
        "region_name": settings.profile_photos_s3_region,
        "config": Config(signature_version="s3v4", s3={"addressing_style": addressing_style}),
    }

    if endpoint_url:
        client_kwargs["endpoint_url"] = endpoint_url

    if settings.profile_photos_s3_access_key_id:
        client_kwargs["aws_access_key_id"] = settings.profile_photos_s3_access_key_id

    if settings.profile_photos_s3_secret_access_key:
        client_kwargs["aws_secret_access_key"] = settings.profile_photos_s3_secret_access_key

    return boto3.client("s3", **client_kwargs)


def _build_s3_storage_key(user_id: int, extension: str) -> str:
    prefix = settings.profile_photos_s3_prefix.strip().strip("/")
    suffix = f"{user_id}/{uuid4().hex}{extension}"
    return f"{prefix}/{suffix}" if prefix else suffix


def _build_s3_photo_url(storage_key: str) -> str:
    base = (settings.profile_photos_s3_public_base_url or "").strip()
    if base:
        return f"{base.rstrip('/')}/{storage_key}"

    bucket = settings.profile_photos_s3_bucket.strip()
    endpoint_url = (settings.profile_photos_s3_endpoint_url or "").strip()
    inferred_base = _infer_supabase_public_base_url(endpoint_url, bucket)
    if inferred_base:
        return f"{inferred_base}/{storage_key}"

    region = settings.profile_photos_s3_region.strip()
    return f"https://{bucket}.s3.{region}.amazonaws.com/{storage_key}"


def _is_supabase_s3_endpoint(endpoint_url: str | None) -> bool:
    if not endpoint_url:
        return False
    parsed = urlparse(endpoint_url)
    return (
        parsed.scheme in {"http", "https"}
        and parsed.netloc.endswith(".storage.supabase.co")
        and parsed.path.rstrip("/").endswith("/storage/v1/s3")
    )


def _infer_supabase_public_base_url(endpoint_url: str, bucket: str) -> str | None:
    if not bucket:
        return None
    if not _is_supabase_s3_endpoint(endpoint_url):
        return None

    parsed = urlparse(endpoint_url)
    hostname = parsed.hostname or ""
    suffix = ".storage.supabase.co"
    if not hostname.endswith(suffix):
        return None

    project_ref = hostname.removesuffix(suffix)
    if not project_ref:
        return None

    return f"https://{project_ref}.supabase.co/storage/v1/object/public/{bucket}"


async def save_profile_photo(
    user_id: int,
    uploaded_file: UploadFile,
    *,
    request_base_url: str,
) -> StoredProfilePhoto:
    original_filename = _validate_upload(uploaded_file)
    extension = Path(original_filename).suffix.lower()[:20]

    if _profile_backend() == "filesystem":
        storage_key = f"{user_id}/{uuid4().hex}{extension}"
        file_path = _resolve_filesystem_path(storage_key)
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
                            f"File size exceeded limit ({settings.profile_photos_max_file_size_mb} MB)."
                        )
                    handle.write(chunk)
        except Exception:
            if file_path.exists():
                file_path.unlink()
            raise

        return StoredProfilePhoto(
            storage_key=storage_key,
            url=_build_filesystem_photo_url(storage_key, request_base_url),
            content_type=uploaded_file.content_type,
            size_bytes=total_size,
        )

    if _profile_backend() == "s3":
        bucket = settings.profile_photos_s3_bucket.strip()
        if not bucket:
            raise RuntimeError(
                "PROFILE_PHOTOS_S3_BUCKET must be configured when using S3 storage."
            )

        data, total_size = _read_upload_bytes(uploaded_file)
        storage_key = _build_s3_storage_key(user_id, extension)
        client = _build_s3_client()

        put_kwargs = {
            "Bucket": bucket,
            "Key": storage_key,
            "Body": BytesIO(data),
        }
        if uploaded_file.content_type:
            put_kwargs["ContentType"] = uploaded_file.content_type

        client.put_object(**put_kwargs)

        return StoredProfilePhoto(
            storage_key=storage_key,
            url=_build_s3_photo_url(storage_key),
            content_type=uploaded_file.content_type,
            size_bytes=total_size,
        )

    raise RuntimeError(
        "Invalid PROFILE_PHOTOS_STORAGE_BACKEND. Use 'filesystem' or 's3'."
    )


def get_profile_photo_file_path(storage_key: str) -> Path:
    return _resolve_filesystem_path(storage_key)


def _extract_filesystem_storage_key(photo_url: str) -> str | None:
    parsed = urlparse(photo_url)
    path = parsed.path
    marker = "/profile/photos/"
    if marker not in path:
        return None

    _, storage_key = path.split(marker, maxsplit=1)
    return storage_key.strip("/") or None


def _extract_s3_storage_key(photo_url: str) -> str | None:
    base = (settings.profile_photos_s3_public_base_url or "").strip().rstrip("/")
    if base and photo_url.startswith(f"{base}/"):
        return photo_url.removeprefix(f"{base}/").strip("/") or None

    bucket = settings.profile_photos_s3_bucket.strip()
    endpoint_url = (settings.profile_photos_s3_endpoint_url or "").strip()
    inferred_base = _infer_supabase_public_base_url(endpoint_url, bucket)
    if inferred_base and photo_url.startswith(f"{inferred_base}/"):
        return photo_url.removeprefix(f"{inferred_base}/").strip("/") or None

    parsed = urlparse(photo_url)
    path = parsed.path.lstrip("/")
    if bucket and path.startswith(f"{bucket}/"):
        return path.removeprefix(f"{bucket}/").strip("/") or None
    return path or None


def delete_profile_photo_by_url(photo_url: str | None) -> None:
    if not photo_url:
        return

    backend = _profile_backend()
    if backend == "filesystem":
        storage_key = _extract_filesystem_storage_key(photo_url)
        if not storage_key:
            return

        file_path = _resolve_filesystem_path(storage_key)
        if file_path.exists() and file_path.is_file():
            file_path.unlink()
        return

    if backend == "s3":
        storage_key = _extract_s3_storage_key(photo_url)
        if not storage_key:
            return

        bucket = settings.profile_photos_s3_bucket.strip()
        if not bucket:
            return

        client = _build_s3_client()
        client.delete_object(Bucket=bucket, Key=storage_key)


def get_profile_photo_content_by_url(photo_url: str) -> tuple[bytes, str | None]:
    backend = _profile_backend()
    if backend == "filesystem":
        storage_key = _extract_filesystem_storage_key(photo_url)
        if not storage_key:
            raise FileNotFoundError("Profile photo not found.")
        file_path = _resolve_filesystem_path(storage_key)
        if not file_path.exists() or not file_path.is_file():
            raise FileNotFoundError("Profile photo not found.")
        return file_path.read_bytes(), None

    if backend == "s3":
        storage_key = _extract_s3_storage_key(photo_url)
        if not storage_key:
            raise FileNotFoundError("Profile photo not found.")
        bucket = settings.profile_photos_s3_bucket.strip()
        if not bucket:
            raise FileNotFoundError("Profile photo not found.")
        client = _build_s3_client()
        try:
            response = client.get_object(Bucket=bucket, Key=storage_key)
        except ClientError as exc:
            code = str(exc.response.get("Error", {}).get("Code", ""))
            if code in {"NoSuchKey", "NotFound", "404"}:
                raise FileNotFoundError("Profile photo not found.") from exc
            raise
        body = response.get("Body")
        if body is None:
            raise FileNotFoundError("Profile photo not found.")
        return body.read(), response.get("ContentType")

    raise RuntimeError(
        "Invalid PROFILE_PHOTOS_STORAGE_BACKEND. Use 'filesystem' or 's3'."
    )
