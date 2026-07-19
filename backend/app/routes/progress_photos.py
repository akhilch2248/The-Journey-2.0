from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import ProgressPhoto, User
from ..schemas.training import ProgressPhotoRead
from ..utils.images import delete_image, image_abspath, save_image

router = APIRouter(prefix="/progress-photos", tags=["training"])


def _own_photo(photo_id: int, user: User, db: Session) -> ProgressPhoto:
    photo = (
        db.query(ProgressPhoto)
        .filter(ProgressPhoto.id == photo_id, ProgressPhoto.user_id == user.id)
        .first()
    )
    if photo is None:
        raise HTTPException(status_code=404, detail="Photo not found")
    return photo


@router.get("", response_model=list[ProgressPhotoRead])
def list_photos(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return (
        db.query(ProgressPhoto)
        .filter(ProgressPhoto.user_id == user.id)
        .order_by(ProgressPhoto.taken_at.desc(), ProgressPhoto.id.desc())
        .all()
    )


@router.post("", response_model=ProgressPhotoRead, status_code=201)
def upload_photo(
    image: UploadFile = File(...),
    taken_at: date | None = Form(default=None),
    note: str | None = Form(default=None, max_length=200),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    path = save_image(image, f"progress/u{user.id}")
    photo = ProgressPhoto(
        user_id=user.id,
        image_path=path,
        taken_at=taken_at or date.today(),
        note=note,
    )
    db.add(photo)
    db.commit()
    db.refresh(photo)
    return photo


@router.get("/{photo_id}/image")
def photo_image(photo_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    photo = _own_photo(photo_id, user, db)
    return FileResponse(image_abspath(photo.image_path), media_type="image/jpeg")


@router.delete("/{photo_id}", status_code=204)
def delete_photo(photo_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    photo = _own_photo(photo_id, user, db)
    delete_image(photo.image_path)  # the file goes too, not just the row
    db.delete(photo)
    db.commit()
