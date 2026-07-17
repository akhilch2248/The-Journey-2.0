from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models.user import User
from ..models.weight import WeightLog
from ..schemas.weight import WeightCreate, WeightRead, WeightStats, WeightUpdate

router = APIRouter(prefix="/weights", tags=["weights"])


@router.post("", response_model=WeightRead, status_code=201)
def create_weight(
    payload: WeightCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    exists = (
        db.query(WeightLog)
        .filter(WeightLog.user_id == user.id, WeightLog.date == payload.date)
        .first()
    )
    if exists:
        raise HTTPException(
            status_code=409,
            detail=f"A weight for {payload.date} already exists (id={exists.id}); use PUT /weights/{exists.id} to change it",
        )
    record = WeightLog(user_id=user.id, **payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("", response_model=list[WeightRead])
def list_weights(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(WeightLog).filter(WeightLog.user_id == user.id)
    if start_date:
        query = query.filter(WeightLog.date >= start_date)
    if end_date:
        query = query.filter(WeightLog.date <= end_date)
    return query.order_by(WeightLog.date.desc()).offset(offset).limit(limit).all()


@router.get("/latest", response_model=WeightRead)
def latest_weight(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    record = (
        db.query(WeightLog)
        .filter(WeightLog.user_id == user.id)
        .order_by(WeightLog.date.desc())
        .first()
    )
    if record is None:
        raise HTTPException(status_code=404, detail="No weights logged yet")
    return record


@router.get("/stats", response_model=WeightStats)
def weight_stats(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = (
        db.query(WeightLog)
        .filter(WeightLog.user_id == user.id)
        .order_by(WeightLog.date.asc())
        .all()
    )
    if not rows:
        return WeightStats(count=0)

    first, latest = rows[0], rows[-1]
    weights = [r.weight_kg for r in rows]

    window_start = latest.date - timedelta(days=6)
    window = [r.weight_kg for r in rows if r.date >= window_start]

    span_days = (latest.date - first.date).days
    avg_weekly = (
        round((latest.weight_kg - first.weight_kg) / span_days * 7, 2)
        if span_days > 0
        else None
    )

    return WeightStats(
        count=len(rows),
        first_date=first.date,
        latest_date=latest.date,
        start_weight_kg=first.weight_kg,
        latest_weight_kg=latest.weight_kg,
        min_weight_kg=min(weights),
        max_weight_kg=max(weights),
        total_change_kg=round(latest.weight_kg - first.weight_kg, 2),
        moving_avg_7d_kg=round(sum(window) / len(window), 2),
        avg_weekly_change_kg=avg_weekly,
    )


def _get_owned_weight(weight_id: int, user: User, db: Session) -> WeightLog:
    record = (
        db.query(WeightLog)
        .filter(WeightLog.id == weight_id, WeightLog.user_id == user.id)
        .first()
    )
    if record is None:
        # 404 (not 403) so other users' entry ids can't be probed
        raise HTTPException(status_code=404, detail="Weight not found")
    return record


@router.put("/{weight_id}", response_model=WeightRead)
def update_weight(
    weight_id: int,
    payload: WeightUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    record = _get_owned_weight(weight_id, user, db)
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=400, detail="No fields to update")
    for field, value in changes.items():
        setattr(record, field, value)
    db.commit()
    db.refresh(record)
    return record


@router.delete("/{weight_id}", status_code=204)
def delete_weight(
    weight_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    record = _get_owned_weight(weight_id, user, db)
    db.delete(record)
    db.commit()
    return Response(status_code=204)
