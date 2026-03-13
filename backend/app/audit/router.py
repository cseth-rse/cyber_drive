# app/audit/router.py
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.audit.service import AuditService
from app.database import get_db
from app.models import AuditAction

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


@router.get("")
def query_audit_logs(
    user_id: str | None = Query(default=None),
    document_id: str | None = Query(default=None),
    action: AuditAction | None = Query(default=None),
    from_date: datetime | None = Query(default=None),
    to_date: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    svc = AuditService(db)
    result = svc.query(
        user_id=user_id,
        document_id=document_id,
        action=action,
        from_date=from_date,
        to_date=to_date,
        page=page,
        limit=limit,
    )
    # Serialize items
    items = []
    for log in result["items"]:
        items.append({
            "id": log.id,
            "user": {"id": log.user.id, "email": log.user.email} if log.user else None,
            "action": log.action,
            "document": {"id": log.document.id, "title": log.document.title} if log.document else None,
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "extra": log.extra,
            "timestamp": log.timestamp.isoformat(),
        })
    return {**result, "items": items}
