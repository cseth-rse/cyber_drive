# app/admin/service.py
import logging
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.audit.service import AuditService
from app.models import AuditAction, Document, DocumentStatus, Role, User

logger = logging.getLogger(__name__)


class AdminService:
    def __init__(self, db: Session):
        self.db = db
        self.audit = AuditService(db)

    # ── Users ─────────────────────────────────────────────────────────────────

    def list_users(self, role: Role | None, page: int, limit: int) -> dict:
        limit = min(limit, 100)
        q = self.db.query(User).order_by(User.created_at.desc())
        if role:
            q = q.filter(User.role == role)
        total = q.count()
        items = q.offset((page - 1) * limit).limit(limit).all()
        return {"total": total, "page": page, "limit": limit, "total_pages": -(-total // limit), "items": items}

    def update_user_role(self, user_id: str, new_role: Role, admin: User) -> User:
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
        if user.id == admin.id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot change your own role")
        old_role = user.role
        user.role = new_role
        self.db.commit()
        self.audit.log(
            user_id=admin.id,
            action=AuditAction.ROLE_CHANGE,
            extra={"target_user": user_id, "old_role": old_role.value, "new_role": new_role.value},
        )
        logger.info("Admin %s changed %s role: %s → %s", admin.email, user.email, old_role, new_role)
        return user

    # ── Pending documents ─────────────────────────────────────────────────────

    def list_pending(self, page: int, limit: int) -> dict:
        limit = min(limit, 50)
        q = (
            self.db.query(Document)
            .options(joinedload(Document.course), joinedload(Document.level), joinedload(Document.uploaded_by))
            .filter(Document.status == DocumentStatus.PENDING_APPROVAL)
            .order_by(Document.created_at.asc())
        )
        total = q.count()
        items = q.offset((page - 1) * limit).limit(limit).all()
        return {"total": total, "page": page, "limit": limit, "total_pages": -(-total // limit), "items": items}

    # ── Approve ────────────────────────────────────────────────────────────────

    def approve_document(self, doc_id: str, admin: User) -> Document:
        doc = self.db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
        if doc.status != DocumentStatus.PENDING_APPROVAL:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Document status is {doc.status.value}, not PENDING_APPROVAL")

        doc.status = DocumentStatus.AVAILABLE
        doc.approved_by_id = admin.id
        doc.approved_at = datetime.utcnow()
        doc.rejection_reason = None
        self.db.commit()

        self.audit.log(
            user_id=admin.id,
            action=AuditAction.APPROVE,
            document_id=doc_id,
            extra={"approved_by": admin.email},
        )
        logger.info("Admin %s approved document %s", admin.email, doc_id)
        return doc

    # ── Reject ─────────────────────────────────────────────────────────────────

    def reject_document(self, doc_id: str, reason: str, admin: User) -> Document:
        doc = self.db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
        if doc.status not in (DocumentStatus.PENDING_APPROVAL, DocumentStatus.PENDING_SCAN):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Document cannot be rejected from status {doc.status.value}")

        doc.status = DocumentStatus.REJECTED
        doc.rejection_reason = reason
        self.db.commit()

        self.audit.log(
            user_id=admin.id,
            action=AuditAction.REJECT,
            document_id=doc_id,
            extra={"reason": reason, "rejected_by": admin.email},
        )
        logger.info("Admin %s rejected document %s: %s", admin.email, doc_id, reason)
        return doc

    # ── Delete ─────────────────────────────────────────────────────────────────

    def delete_document(self, doc_id: str, admin: User) -> dict:
        from pathlib import Path

        doc = self.db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")

        file_path = Path(doc.file_path).resolve()
        self.audit.log(
            user_id=admin.id,
            action=AuditAction.DELETE,
            document_id=doc_id,
            extra={"title": doc.title},
        )
        self.db.delete(doc)
        self.db.commit()

        try:
            file_path.unlink(missing_ok=True)
        except Exception as exc:
            logger.warning("Could not delete file %s: %s", file_path, exc)

        logger.info("Admin %s deleted document %s", admin.email, doc_id)
        return {"message": "Document deleted"}
