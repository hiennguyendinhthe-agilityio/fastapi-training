"""
tests/api/test_uploads.py
Unit and integration tests for POST /api/v1/uploads/image endpoint.
"""

import io
from pathlib import Path

import pytest
from httpx import AsyncClient

from app.api.deps import get_current_user
from app.main import app
from app.models.user import User


@pytest.fixture(autouse=True)
def cleanup_uploads():
    """Ensure test upload artifacts are removed after tests."""
    yield
    test_upload_dir = Path("uploads/images")
    if test_upload_dir.exists():
        for file in test_upload_dir.glob("*"):
            if file.is_file():
                try:
                    file.unlink()
                except OSError:
                    pass


@pytest.mark.asyncio
async def test_upload_image_success_admin(
    client: AsyncClient,
    fake_admin: User,
) -> None:
    """
    Admin successfully uploads a valid PNG image and receives 201 Created.
    """
    app.dependency_overrides[get_current_user] = lambda: fake_admin

    image_content = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100  # Fake PNG bytes
    files = {"file": ("coffee.png", io.BytesIO(image_content), "image/png")}

    response = await client.post("/api/v1/uploads/image", files=files)
    assert response.status_code == 201

    data = response.json()
    assert "url" in data
    assert data["url"].endswith(".png")
    assert "/static/images/" in data["url"]
    assert data["content_type"] == "image/png"
    assert data["size_bytes"] == len(image_content)
    assert data["filename"].endswith(".png")


@pytest.mark.asyncio
async def test_upload_image_forbidden_for_regular_user(
    client: AsyncClient,
    fake_user: User,
) -> None:
    """
    Non-admin user (USER role) receives 403 Forbidden when uploading image.
    """
    app.dependency_overrides[get_current_user] = lambda: fake_user

    image_content = b"\xff\xd8\xff\xe0" + b"\x00" * 50
    files = {"file": ("latte.jpg", io.BytesIO(image_content), "image/jpeg")}

    response = await client.post("/api/v1/uploads/image", files=files)
    assert response.status_code == 403
    assert response.json()["detail"] == "Admin privileges required"


@pytest.mark.asyncio
async def test_upload_image_unauthorized_no_token(client: AsyncClient) -> None:
    """Unauthenticated request without token receives 401 Unauthorized."""
    # Ensure no override
    app.dependency_overrides.pop(get_current_user, None)

    image_content = b"\xff\xd8\xff\xe0" + b"\x00" * 50
    files = {"file": ("latte.jpg", io.BytesIO(image_content), "image/jpeg")}

    response = await client.post("/api/v1/uploads/image", files=files)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_upload_image_invalid_content_type(
    client: AsyncClient,
    fake_admin: User,
) -> None:
    """Uploading unsupported media type (e.g. text/plain) receives 400 Bad Request."""
    app.dependency_overrides[get_current_user] = lambda: fake_admin

    text_content = b"hello, this is not an image"
    files = {"file": ("notes.txt", io.BytesIO(text_content), "text/plain")}

    response = await client.post("/api/v1/uploads/image", files=files)
    assert response.status_code == 400
    assert "Unsupported media type" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_image_empty_file(
    client: AsyncClient,
    fake_admin: User,
) -> None:
    """Uploading empty 0-byte file receives 400 Bad Request."""
    app.dependency_overrides[get_current_user] = lambda: fake_admin

    files = {"file": ("empty.png", io.BytesIO(b""), "image/png")}

    response = await client.post("/api/v1/uploads/image", files=files)
    assert response.status_code == 400
    assert response.json()["detail"] == "Uploaded file is empty"


@pytest.mark.asyncio
async def test_upload_image_file_too_large(
    client: AsyncClient,
    fake_admin: User,
) -> None:
    """Uploading image exceeding 5MB receives 413 Request Entity Too Large."""
    app.dependency_overrides[get_current_user] = lambda: fake_admin

    # 5MB + 1 byte
    oversized = b"\x00" * (5 * 1024 * 1024 + 1)
    files = {"file": ("huge.png", io.BytesIO(oversized), "image/png")}

    response = await client.post("/api/v1/uploads/image", files=files)
    assert response.status_code == 413
    assert "exceeds maximum allowed limit" in response.json()["detail"]
