"""Image upload handling for physique references and progress photos.

Every upload is re-encoded through Pillow before it touches disk: that
validates it's really an image, strips ALL metadata (EXIF carries GPS
coordinates — a privacy leak for photos of a person), and caps dimensions.
Files live under settings.upload_dir (gitignored), named by uuid, and are only
ever served through authenticated endpoints that check ownership.
"""

import io
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

from ..config import get_settings

MAX_DIMENSION = 2048


def _upload_root() -> Path:
    root = Path(get_settings().upload_dir)
    root.mkdir(parents=True, exist_ok=True)
    return root


def save_image(file: UploadFile, subdir: str) -> str:
    """Validate, strip metadata, resize, save. Returns the relative path to store."""
    settings = get_settings()
    raw = file.file.read(settings.max_upload_mb * 1024 * 1024 + 1)
    if len(raw) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"Image larger than {settings.max_upload_mb} MB")
    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status_code=400, detail="File is not a readable image")

    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    img.thumbnail((MAX_DIMENSION, MAX_DIMENSION))  # no-op when already smaller

    rel = f"{subdir}/{uuid.uuid4().hex}.jpg"
    dest = _upload_root() / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    # Re-encoding drops every metadata block (EXIF/GPS/XMP) by construction.
    img.save(dest, format="JPEG", quality=88)
    return rel


def image_abspath(rel_path: str) -> Path:
    """Resolve a stored relative path, refusing anything outside the upload root."""
    root = _upload_root().resolve()
    dest = (root / rel_path).resolve()
    if not dest.is_relative_to(root):
        raise HTTPException(status_code=404, detail="Image not found")
    if not dest.is_file():
        raise HTTPException(status_code=404, detail="Image not found")
    return dest


def delete_image(rel_path: str | None) -> None:
    if not rel_path:
        return
    try:
        image_abspath(rel_path).unlink(missing_ok=True)
    except HTTPException:
        pass  # already gone
