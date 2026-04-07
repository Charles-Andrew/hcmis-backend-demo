from io import BytesIO
from typing import cast

import anyio
import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers

from app.core.config import settings
from app.core.exceptions import ConflictError
from app.services.shared_resources_storage import (
    save_uploaded_resource_file,
    validate_uploaded_resource_file,
)


def test_validate_uploaded_resource_file_rejects_unsupported_extension():
    file = UploadFile(filename="installer.exe", file=BytesIO(b"binary"), headers=Headers())

    with pytest.raises(ConflictError, match="Unsupported file type"):
        validate_uploaded_resource_file(file)


def test_save_uploaded_resource_file_rejects_oversized_file(monkeypatch):
    monkeypatch.setattr(settings, "shared_resources_s3_bucket", "shared-resources")
    monkeypatch.setattr(settings, "shared_resources_max_file_size_mb", 1)

    content = b"a" * (1024 * 1024 + 1)
    file = UploadFile(
        filename="large-video.mp4",
        file=BytesIO(content),
        headers=Headers({"content-type": "video/mp4"}),
    )

    with pytest.raises(ConflictError, match="File size exceeded limit"):
        anyio.run(save_uploaded_resource_file, 1, file)


def test_save_uploaded_resource_file_accepts_document_file(monkeypatch):
    monkeypatch.setattr(settings, "shared_resources_s3_bucket", "shared-resources")
    monkeypatch.setattr(settings, "shared_resources_max_file_size_mb", 5)
    monkeypatch.setattr(settings, "shared_resources_s3_prefix", "shared-resources")

    captured: dict[str, object] = {}

    class FakeS3Client:
        def put_object(self, **kwargs: object) -> None:
            captured.update(kwargs)

    monkeypatch.setattr(
        "app.services.shared_resources_storage._build_s3_client",
        lambda: FakeS3Client(),
    )

    payload = b"hello world"
    file = UploadFile(
        filename="policy.pdf",
        file=BytesIO(payload),
        headers=Headers({"content-type": "application/pdf"}),
    )

    stored = anyio.run(save_uploaded_resource_file, 9, file)

    assert stored.original_filename == "policy.pdf"
    assert stored.storage_key.startswith("shared-resources/9/")
    assert stored.size_bytes == len(payload)
    assert captured["Bucket"] == "shared-resources"
    assert captured["Key"] == stored.storage_key
    assert captured["ContentType"] == "application/pdf"
    assert cast(BytesIO, captured["Body"]).read() == payload
