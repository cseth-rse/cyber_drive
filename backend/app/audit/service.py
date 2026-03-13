# app/audit/service.py
import json
import logging
from datetime import datetime

from fastapi import Request
from sqlalchemy.orm import Session

from app.models import AuditAction, AuditLog, Document, User

logger = logging.getLogger(__name__)


def _get_ip(request: Request | None) -> str | None:
    if request is None:
        return None
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


def _get_ua(request: Request | None) -> str | None:
    if request is None:
        return None
    return request.headers.get("User-Agent")


class AuditService:
    def __init__(self, db: Session):
        self.db = db

    def log(
        self,
        user_id: str,
        action: AuditAction,
        document_id: str | None = None,
        request: Request | None = None,
        extra: dict | None = None,
    ) -> None:
        try:
            entry = AuditLog(
                user_id=user_id,
                action=action,
                document_id=document_id,
                ip_address=_get_ip(request),
                user_agent=_get_ua(request),
                extra=json.dumps(extra) if extra else None,
                timestamp=datetime.utcnow(),
            )
            self.db.add(entry)
            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            logger.error("Failed to write audit log: %s", exc)

    def query(
        self,
        user_id: str | None = None,
        document_id: str | None = None,
        action: AuditAction | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        page: int = 1,
        limit: int = 50,
    ) -> dict:
        from sqlalchemy.orm import joinedload

        limit = min(limit, 100)
        q = (
            self.db.query(AuditLog)
            .options(
                joinedload(AuditLog.user),
                joinedload(AuditLog.document),
            )
            .order_by(AuditLog.timestamp.desc())
        )
        if user_id:
            q = q.filter(AuditLog.user_id == user_id)
        if document_id:
            q = q.filter(AuditLog.document_id == document_id)
        if action:
            q = q.filter(AuditLog.action == action)
        if from_date:
            q = q.filter(AuditLog.timestamp >= from_date)
        if to_date:
            q = q.filter(AuditLog.timestamp <= to_date)

        total = q.count()
        items = q.offset((page - 1) * limit).limit(limit).all()
        return {
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": -(-total // limit),
            "items": items,
        }
