"""
app/schemas/upload.py
Pydantic schemas for file and image upload endpoints.
"""

from pydantic import BaseModel, Field


class ImageUploadResponse(BaseModel):
    """Metadata response returned upon successful image upload."""

    url: str = Field(..., description="Publicly accessible URL of the uploaded image")
    filename: str = Field(..., description="Unique filename stored on the server")
    content_type: str = Field(..., description="MIME type of the uploaded file")
    size_bytes: int = Field(..., description="File size in bytes")
