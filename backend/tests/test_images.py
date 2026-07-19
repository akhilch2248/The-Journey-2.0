"""Image uploads: validation, EXIF stripping, ownership, file lifecycle."""

import io
from pathlib import Path

from PIL import Image

from app.config import get_settings

from .conftest import login


def png_bytes(size=(64, 64), color=(120, 40, 40)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def jpeg_with_exif() -> bytes:
    img = Image.new("RGB", (64, 64), (10, 90, 60))
    exif = Image.Exif()
    exif[271] = "TestMake"        # Make
    exif[272] = "TestCamera"      # Model
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif)
    # Sanity: the fixture really does carry EXIF before upload.
    assert Image.open(io.BytesIO(buf.getvalue())).getexif()
    return buf.getvalue()


def test_goal_reference_image_roundtrip(client, auth_headers):
    res = client.post(
        "/physique-goals",
        data={"reference_label": "Vidyut"},
        files={"reference_image": ("ref.png", png_bytes(), "image/png")},
        headers=auth_headers,
    )
    assert res.status_code == 201, res.text
    goal = res.json()
    assert goal["has_image"] is True
    img = client.get(f"/physique-goals/{goal['id']}/image", headers=auth_headers)
    assert img.status_code == 200
    assert img.headers["content-type"] == "image/jpeg"
    Image.open(io.BytesIO(img.content)).verify()


def test_upload_strips_exif_metadata(client, auth_headers):
    res = client.post(
        "/progress-photos",
        files={"image": ("me.jpg", jpeg_with_exif(), "image/jpeg")},
        headers=auth_headers,
    )
    assert res.status_code == 201, res.text
    photo_id = res.json()["id"]
    served = client.get(f"/progress-photos/{photo_id}/image", headers=auth_headers)
    assert served.status_code == 200
    assert not Image.open(io.BytesIO(served.content)).getexif(), "EXIF survived re-encode"


def test_non_image_upload_rejected(client, auth_headers):
    res = client.post(
        "/progress-photos",
        files={"image": ("evil.jpg", b"#!/bin/sh\necho not an image", "image/jpeg")},
        headers=auth_headers,
    )
    assert res.status_code == 400


def test_oversize_upload_rejected(client, auth_headers):
    settings = get_settings()
    original = settings.max_upload_mb
    settings.max_upload_mb = 0
    try:
        res = client.post(
            "/progress-photos",
            files={"image": ("big.png", png_bytes(), "image/png")},
            headers=auth_headers,
        )
        assert res.status_code == 413
    finally:
        settings.max_upload_mb = original


def test_photo_delete_removes_row_and_file(client, auth_headers):
    res = client.post(
        "/progress-photos",
        data={"note": "week 4"},
        files={"image": ("me.png", png_bytes(), "image/png")},
        headers=auth_headers,
    )
    photo_id = res.json()["id"]
    upload_root = Path(get_settings().upload_dir)
    files_before = list(upload_root.rglob("*.jpg"))
    assert len(files_before) == 1

    assert client.delete(f"/progress-photos/{photo_id}", headers=auth_headers).status_code == 204
    assert list(upload_root.rglob("*.jpg")) == []
    assert client.get("/progress-photos", headers=auth_headers).json() == []


def test_photos_are_isolated(client):
    h_a = login(client, "photo-a")
    h_b = login(client, "photo-b")
    res = client.post(
        "/progress-photos",
        files={"image": ("me.png", png_bytes(), "image/png")},
        headers=h_a,
    )
    photo_id = res.json()["id"]
    assert client.get("/progress-photos", headers=h_b).json() == []
    assert client.get(f"/progress-photos/{photo_id}/image", headers=h_b).status_code == 404
    assert client.delete(f"/progress-photos/{photo_id}", headers=h_b).status_code == 404
