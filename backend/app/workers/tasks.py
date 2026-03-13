# app/workers/tasks.py
import json
import logging
from datetime import datetime
from pathlib import Path

from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "cyber_drive",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)

logger = logging.getLogger(__name__)


@celery_app.task(name="process_document", bind=True, max_retries=3, default_retry_delay=10)
def process_document(self, document_id: str) -> None:
    """
    Phase 2: Real ClamAV scan.
    - CLEAN + uploader is ADMIN   → AVAILABLE
    - CLEAN + uploader is CONTRIBUTOR → PENDING_APPROVAL
    - VIRUS found or scan error   → REJECTED, file deleted
    """
    from app.database import SessionLocal
    from app.models import AuditAction, AuditLog, Document, DocumentStatus, Role
    from app.workers.scanner import scan_file

    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            logger.warning("Document %s not found in DB", document_id)
            return

        abs_path = Path(doc.file_path).resolve()
        logger.info("Scanning document %s at %s", document_id, abs_path)

        is_clean, detail = scan_file(abs_path)

        doc.scanned_at = datetime.utcnow()
        doc.scan_result = detail

        if not is_clean:
            doc.status = DocumentStatus.REJECTED
            doc.rejection_reason = f"Virus scan failed: {detail}"
            # Delete the infected file
            try:
                abs_path.unlink(missing_ok=True)
            except Exception as del_err:
                logger.error("Could not delete infected file %s: %s", abs_path, del_err)
            logger.warning("Document %s REJECTED (virus: %s)", document_id, detail)
        else:
            # Determine next status based on uploader role
            uploader = doc.uploaded_by
            if uploader and uploader.role == Role.ADMIN:
                doc.status = DocumentStatus.AVAILABLE
                logger.info("Document %s AVAILABLE (admin upload)", document_id)
            else:
                doc.status = DocumentStatus.PENDING_APPROVAL
                logger.info("Document %s PENDING_APPROVAL (contributor upload)", document_id)

        db.commit()

        # Write audit log
        _write_audit(db, doc.uploaded_by_id, AuditAction.UPLOAD, document_id, {
            "scan_result": detail,
            "final_status": doc.status.value,
        })

    except Exception as exc:
        db.rollback()
        logger.error("Error processing document %s: %s", document_id, exc)
        raise self.retry(exc=exc, countdown=10)
    finally:
        db.close()


def _write_audit(db, user_id: str, action, document_id: str, extra: dict) -> None:
    from app.models import AuditLog
    try:
        log = AuditLog(
            user_id=user_id,
            action=action,
            document_id=document_id,
            extra=json.dumps(extra),
        )
        db.add(log)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error("Audit log write failed: %s", e)
