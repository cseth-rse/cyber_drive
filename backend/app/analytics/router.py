# app/analytics/router.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.analytics.service import AnalyticsService
from app.auth.dependencies import require_admin
from app.database import get_db

router = APIRouter(prefix="/admin/stats", tags=["Admin Analytics"])


def _svc(db: Session = Depends(get_db)) -> AnalyticsService:
    return AnalyticsService(db)


@router.get("/overview")
def stats_overview(
    _=Depends(require_admin),
    svc: AnalyticsService = Depends(_svc),
):
    """Platform summary: users, documents, downloads, storage."""
    return svc.overview()


@router.get("/daily")
def stats_daily(
    days: int = Query(default=30, ge=1, le=90, description="Number of days to look back"),
    _=Depends(require_admin),
    svc: AnalyticsService = Depends(_svc),
):
    """Daily upload/download counts for the last N days."""
    return svc.daily(days)


@router.get("/top-documents")
def stats_top_documents(
    limit: int = Query(default=10, ge=1, le=50),
    _=Depends(require_admin),
    svc: AnalyticsService = Depends(_svc),
):
    """Most downloaded documents."""
    return svc.top_documents(limit)


@router.get("/top-users")
def stats_top_users(
    limit: int = Query(default=10, ge=1, le=50),
    metric: str = Query(default="uploads", pattern="^(uploads|downloads)$"),
    _=Depends(require_admin),
    svc: AnalyticsService = Depends(_svc),
):
    """Most active users by uploads or downloads."""
    return svc.top_users(limit, metric)


@router.get("/storage-by-level")
def stats_storage_by_level(
    _=Depends(require_admin),
    svc: AnalyticsService = Depends(_svc),
):
    """Storage usage and download counts broken down by academic level."""
    return svc.storage_by_level()
