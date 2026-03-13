# app/levels/router.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models import Level, Course, User
from app.schemas import CourseOut, LevelOut

router = APIRouter(prefix="/levels", tags=["Levels"])


@router.get("", response_model=list[LevelOut])
def list_levels(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return (
        db.query(Level)
        .options(joinedload(Level.courses))
        .order_by(Level.order)
        .all()
    )


@router.get("/{level_id}/courses", response_model=list[CourseOut])
def list_courses(
    level_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    level = db.query(Level).filter(Level.id == level_id).first()
    if not level:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Level {level_id} not found")
    return db.query(Course).filter(Course.level_id == level_id).order_by(Course.code).all()
