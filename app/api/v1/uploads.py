"""
app/api/v1/uploads.py
File and image upload endpoints for products and media assets.
"""

import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status

from app.api.deps import require_admin
from app.models.user import User
from app.schemas.upload import ImageUploadResponse

router = APIRouter(prefix="/uploads", tags=["uploads"])

UPLOAD_DIR = Path("uploads/images")
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_CONTENT_TYPES: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


@router.post(
    "/image",
    response_model=ImageUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload product image",
    response_description="Uploaded image metadata and public URL",
)
async def upload_product_image(
    current_admin: Annotated[User, Depends(require_admin)],
    request: Request,
    file: UploadFile = File(..., description="Image file to upload (JPEG, PNG, WebP)"),
) -> ImageUploadResponse:
    """
    Upload a product image file (up to 5MB).
    Requires ADMIN role.
    Validates MIME type, generates a cryptographically secure unique UUID filename,
    and returns a publicly resolvable URL.
    """
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported media type '{file.content_type}'. "
                "Only image/jpeg, image/png, and image/webp are allowed."
            ),
        )

    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )

    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="File size exceeds maximum allowed limit of 5MB",
        )

    ext = ALLOWED_CONTENT_TYPES[file.content_type]
    unique_filename = f"{uuid.uuid4().hex}{ext}"
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    file_path = UPLOAD_DIR / unique_filename

    with open(file_path, "wb") as buffer:
        buffer.write(contents)

    base_url = str(request.base_url).rstrip("/")
    image_url = f"{base_url}/static/images/{unique_filename}"

    return ImageUploadResponse(
        url=image_url,
        filename=unique_filename,
        content_type=file.content_type,
        size_bytes=len(contents),
    )
