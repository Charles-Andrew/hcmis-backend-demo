from io import BytesIO
from uuid import UUID

import anyio
import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers

from app.core.config import settings
from app.core.exceptions import ConflictError
from app.services.profile_photo_storage import get_profile_photo_read_url, save_profile_photo


def test_save_profile_photo_rejects_invalid_extension(monkeypatch):
    monkeypatch.setattr(settings, "profile_photos_storage_backend", "filesystem")

    file = UploadFile(
        filename="avatar.txt",
        file=BytesIO(b"not-image"),
        headers=Headers({"content-type": "text/plain"}),
    )
    
    async def _save():
        await save_profile_photo(
            UUID(int=1),
            file,
            request_base_url="http://localhost:8000/",
        )

    with pytest.raises(ConflictError, match="Unsupported image format"):
        anyio.run(_save)


def test_save_profile_photo_in_filesystem_mode(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "profile_photos_storage_backend", "filesystem")
    monkeypatch.setattr(
        settings,
        "profile_photos_storage_dir",
        str(tmp_path / "profile-photos"),
    )
    monkeypatch.setattr(settings, "profile_photos_max_file_size_mb", 5)
    monkeypatch.setattr(settings, "profile_photos_public_base_url", "")

    payload = b"fake-image-bytes"
    file = UploadFile(
        filename="avatar.png",
        file=BytesIO(payload),
        headers=Headers({"content-type": "image/png"}),
    )
    
    async def _save():
        return await save_profile_photo(
            UUID(int=42),
            file,
            request_base_url="http://localhost:8000/",
        )

    stored = anyio.run(_save)

    assert stored.storage_key.startswith(f"{UUID(int=42)}/")
    assert stored.url.startswith(f"http://localhost:8000/profile/photos/{UUID(int=42)}/")
    assert stored.size_bytes == len(payload)


def test_get_profile_photo_read_url_returns_same_url_for_filesystem(monkeypatch):
    monkeypatch.setattr(settings, "profile_photos_storage_backend", "filesystem")
    url = "http://localhost:8000/profile/photos/42/avatar.png"

    assert get_profile_photo_read_url(url) == url


def test_get_profile_photo_read_url_generates_s3_signed_url(monkeypatch):
    monkeypatch.setattr(settings, "profile_photos_storage_backend", "s3")
    monkeypatch.setattr(settings, "profile_photos_s3_bucket", "avatars")
    monkeypatch.setattr(
        settings,
        "profile_photos_s3_public_base_url",
        "https://project.supabase.co/storage/v1/object/public/avatars",
    )
    monkeypatch.setattr(settings, "profile_photos_signed_url_ttl_seconds", 600)

    captured: dict[str, object] = {}

    class FakeS3Client:
        def generate_presigned_url(
            self,
            ClientMethod: str,
            Params: dict[str, str],
            ExpiresIn: int,
        ) -> str:
            captured["ClientMethod"] = ClientMethod
            captured["Params"] = Params
            captured["ExpiresIn"] = ExpiresIn
            return "https://signed.example.com/photo.png"

    monkeypatch.setattr(
        "app.services.profile_photo_storage._build_s3_client",
        lambda: FakeS3Client(),
    )

    user_id = UUID(int=42)
    url = (
        "https://project.supabase.co/storage/v1/object/public/avatars/"
        f"profile-photos/{user_id}/avatar.png"
    )
    result = get_profile_photo_read_url(url)

    assert result == "https://signed.example.com/photo.png"
    assert captured["ClientMethod"] == "get_object"
    assert captured["Params"] == {
        "Bucket": "avatars",
        "Key": f"profile-photos/{user_id}/avatar.png",
    }
    assert captured["ExpiresIn"] == 600
