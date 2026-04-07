from io import BytesIO
from uuid import UUID
from typing import cast

import anyio
import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers

from app.core.config import settings
from app.core.exceptions import ConflictError
from app.services.profile_photo_storage import (
    delete_profile_photo_by_url,
    get_profile_photo_read_url,
    save_profile_photo,
)
from botocore.exceptions import ClientError


def test_save_profile_photo_rejects_invalid_extension(monkeypatch):
    monkeypatch.setattr(settings, "profile_photos_s3_bucket", "avatars")

    file = UploadFile(
        filename="avatar.txt",
        file=BytesIO(b"not-image"),
        headers=Headers({"content-type": "text/plain"}),
    )
    
    async def _save():
        await save_profile_photo(
            UUID(int=1),
            file,
        )

    with pytest.raises(ConflictError, match="Unsupported image format"):
        anyio.run(_save)


def test_save_profile_photo_uploads_to_s3(monkeypatch):
    monkeypatch.setattr(settings, "profile_photos_s3_bucket", "avatars")
    monkeypatch.setattr(settings, "profile_photos_max_file_size_mb", 5)
    monkeypatch.setattr(settings, "profile_photos_s3_prefix", "profile-photos")
    monkeypatch.setattr(
        settings,
        "profile_photos_s3_public_base_url",
        "https://project.supabase.co/storage/v1/object/public/avatars",
    )

    captured: dict[str, object] = {}

    class FakeS3Client:
        def put_object(self, **kwargs: object) -> None:
            captured.update(kwargs)

    monkeypatch.setattr(
        "app.services.profile_photo_storage._build_s3_client",
        lambda: FakeS3Client(),
    )

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
        )

    stored = anyio.run(_save)

    assert stored.storage_key.startswith(f"profile-photos/{UUID(int=42)}/")
    assert stored.url.startswith("https://project.supabase.co/storage/v1/object/public/avatars/")
    assert stored.size_bytes == len(payload)
    assert captured["Bucket"] == "avatars"
    assert captured["Key"] == stored.storage_key
    assert captured["ContentType"] == "image/png"
    assert cast(BytesIO, captured["Body"]).read() == payload


def test_get_profile_photo_read_url_generates_s3_signed_url(monkeypatch):
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


def test_delete_profile_photo_by_url_ignores_missing_object(monkeypatch):
    monkeypatch.setattr(settings, "profile_photos_s3_bucket", "avatars")
    monkeypatch.setattr(
        settings,
        "profile_photos_s3_public_base_url",
        "https://project.supabase.co/storage/v1/object/public/avatars",
    )

    class FakeS3Client:
        def delete_object(self, **kwargs: object) -> None:
            raise ClientError(
                {
                    "Error": {
                        "Code": "NoSuchKey",
                        "Message": "Object not found",
                    }
                },
                "DeleteObject",
            )

    monkeypatch.setattr(
        "app.services.profile_photo_storage._build_s3_client",
        lambda: FakeS3Client(),
    )

    delete_profile_photo_by_url(
        "https://project.supabase.co/storage/v1/object/public/avatars/"
        "profile-photos/00000000-0000-0000-0000-000000000001/avatar.png"
    )
