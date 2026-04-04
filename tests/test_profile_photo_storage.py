from io import BytesIO

import anyio
import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers

from app.core.config import settings
from app.core.exceptions import ConflictError
from app.services.profile_photo_storage import save_profile_photo


def test_save_profile_photo_rejects_invalid_extension(monkeypatch):
    monkeypatch.setattr(settings, "profile_photos_storage_backend", "filesystem")

    file = UploadFile(
        filename="avatar.txt",
        file=BytesIO(b"not-image"),
        headers=Headers({"content-type": "text/plain"}),
    )
    
    async def _save():
        await save_profile_photo(
            1,
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
            42,
            file,
            request_base_url="http://localhost:8000/",
        )

    stored = anyio.run(_save)

    assert stored.storage_key.startswith("42/")
    assert stored.url.startswith("http://localhost:8000/profile/photos/42/")
    assert stored.size_bytes == len(payload)
