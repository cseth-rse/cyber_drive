# app/admin/router.py
from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.orm import Session

from app.admin.service import AdminService
from app.auth.dependencies import require_admin
from app.database import get_db
from app.models import Role, User

router = APIRouter(prefix="/admin", tags=["Admin"])


def _svc(db: Session = Depends(get_db)) -> AdminService:
    return AdminService(db)


# ── Users ─────────────────────────────────────────────────────────────────────

@router.get("/users")
def list_users(
    role: Role | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
    admin: User = Depends(require_admin),
    svc: AdminService = Depends(_svc),
):
    """List all users, optionally filtered by role."""
    result = svc.list_users(role=role, page=page, limit=limit)
    items = [
        {
            "id": u.id,
            "email": u.email,
            "role": u.role,
            "created_at": u.created_at.isoformat(),
            "upload_count": len(u.uploaded_docs),
        }
        for u in result["items"]
    ]
    return {**result, "items": items}


@router.patch("/users/{user_id}/role")
def update_user_role(
    user_id: str,
    role: Role = Body(..., embed=True),
    admin: User = Depends(require_admin),
    svc: AdminService = Depends(_svc),
):
    """Change a user's role (STUDENT / CONTRIBUTOR / ADMIN)."""
    user = svc.update_user_role(user_id, role, admin)
    return {"id": user.id, "email": user.email, "role": user.role}


# ── Documents ─────────────────────────────────────────────────────────────────

@router.get("/documents/pending")
def list_pending_documents(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=50),
    admin: User = Depends(require_admin),
    svc: AdminService = Depends(_svc),
):
    """List documents that passed ClamAV scan and are awaiting admin approval."""
    result = svc.list_pending(page=page, limit=limit)
    items = [
        {
            "id": d.id,
            "title": d.title,
            "description": d.description,
            "file_name": d.file_name,
            "size": d.size,
            "status": d.status,
            "scanned_at": d.scanned_at.isoformat() if d.scanned_at else None,
            "scan_result": d.scan_result,
            "course": {"id": d.course.id, "code": d.course.code, "title": d.course.title} if d.course else None,
            "level": {"id": d.level.id, "name": d.level.name} if d.level else None,
            "uploaded_by": {"id": d.uploaded_by.id, "email": d.uploaded_by.email} if d.uploaded_by else None,
            "created_at": d.created_at.isoformat(),
        }
        for d in result["items"]
    ]
    return {**result, "items": items}


@router.post("/documents/{doc_id}/approve")
def approve_document(
    doc_id: str,
    admin: User = Depends(require_admin),
    svc: AdminService = Depends(_svc),
):
    """Approve a PENDING_APPROVAL document — makes it AVAILABLE."""
    doc = svc.approve_document(doc_id, admin)
    return {
        "id": doc.id,
        "title": doc.title,
        "status": doc.status,
        "approved_at": doc.approved_at.isoformat() if doc.approved_at else None,
    }


@router.post("/documents/{doc_id}/reject")
def reject_document(
    doc_id: str,
    reason: str = Body(..., embed=True),
    admin: User = Depends(require_admin),
    svc: AdminService = Depends(_svc),
):
    """Reject a document with a reason."""
    doc = svc.reject_document(doc_id, reason, admin)
    return {"id": doc.id, "title": doc.title, "status": doc.status, "rejection_reason": doc.rejection_reason}


@router.delete("/documents/{doc_id}")
def delete_document(
    doc_id: str,
    admin: User = Depends(require_admin),
    svc: AdminService = Depends(_svc),
):
    """Permanently delete a document and its file from disk."""
    return svc.delete_document(doc_id, admin)
