# app/documents/service.py
import hashlib
import logging
import re
import uuid
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import filetype
from fastapi import HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session, joinedload

from app.audit.service import AuditService
from app.config import Settings
from app.models import AuditAction, Course, Document, DocumentStatus, Role, User
from app.storage.s3 import S3Service
from app.workers.tasks import process_document

logger = logging.getLogger(__name__)
_TAG_RE = re.compile(r"<[^>]+>")


def _sanitize(text: str | None) -> str | None:
    if text is None:
        return None
    return _TAG_RE.sub("", text).strip()


def _s3_key(doc_id: str, filename: str) -> str:
    return f"documents/{doc_id}/{filename}"


class DocumentsService:
    def __init__(self, db: Session, settings: Settings):
        self.db = db
        self.settings = settings
        self.upload_root = Path(settings.upload_dir).resolve()
        self.s3 = S3Service(settings)

    # ── Upload ───────────────────────────────────────────────────────────────
    async def upload(
        self,
        file: UploadFile,
        title: str,
        course_id: str,
        level_id: int,
        uploader: User,
        description: str | None = None,
        request: Request | None = None,
    ) -> dict:
        contents = await file.read()

        if len(contents) > self.settings.max_file_size_bytes:
            raise HTTPException(status.HTTP_400_BAD_REQUEST,
                f"File exceeds maximum size of {self.settings.max_file_size_mb} MB")

        kind = filetype.guess(contents)
        if kind is None or kind.mime != "application/pdf":
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only PDF files are accepted")

        course = self.db.query(Course).filter(
            Course.id == course_id, Course.level_id == level_id
        ).first()
        if not course:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Course not found for the given level")

        checksum = hashlib.sha256(contents).hexdigest()
        existing = self.db.query(Document).filter(Document.checksum == checksum).first()
        if existing:
            raise HTTPException(status.HTTP_409_CONFLICT,
                {"message": "Duplicate file", "existing_id": existing.id})

        doc_id = str(uuid.uuid4())
        unique_name = f"{uuid.uuid4()}.pdf"

        if self.settings.using_s3:
            # Store in S3
            s3_key = _s3_key(doc_id, unique_name)
            self.s3.upload_file(contents, s3_key)
            file_path = s3_key           # store the S3 key in DB
            storage_backend = "s3"
        else:
            # Store locally (Phase 1/2 behaviour)
            year_month = datetime.utcnow().strftime("%Y-%m")
            sub_dir = self.upload_root / year_month
            sub_dir.mkdir(parents=True, exist_ok=True)
            abs_path = sub_dir / unique_name
            abs_path.write_bytes(contents)
            file_path = f"{self.settings.upload_dir}/{year_month}/{unique_name}"
            storage_backend = "local"

        doc = Document(
            id=doc_id,
            title=_sanitize(title) or title,
            description=_sanitize(description),
            file_name=file.filename or unique_name,
            file_path=file_path,
            checksum=checksum,
            size=len(contents),
            mime_type=kind.mime,
            status=DocumentStatus.PENDING_SCAN,
            storage_backend=storage_backend,
            uploaded_by_id=uploader.id,
            course_id=course_id,
            level_id=level_id,
        )
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)

        process_document.delay(doc.id)
        logger.info("Document %s uploaded to %s, queued for scan", doc.id, storage_backend)
        return {"id": doc.id, "status": doc.status, "title": doc.title}

    # ── List ─────────────────────────────────────────────────────────────────
    def list_documents(self, page: int = 1, limit: int = 20,
                       level_id: int | None = None, course_id: str | None = None) -> dict:
        limit = min(limit, 50)
        query = (
            self.db.query(Document)
            .options(joinedload(Document.course), joinedload(Document.level), joinedload(Document.uploaded_by))
            .filter(Document.status == DocumentStatus.AVAILABLE)
        )
        if level_id:
            query = query.filter(Document.level_id == level_id)
        if course_id:
            query = query.filter(Document.course_id == course_id)
        total = query.count()
        items = query.order_by(Document.created_at.desc()).offset((page-1)*limit).limit(limit).all()
        return {"total": total, "page": page, "limit": limit, "total_pages": -(-total//limit), "items": items}

    # ── Get one ──────────────────────────────────────────────────────────────
    def get_document(self, doc_id: str) -> Document:
        doc = (
            self.db.query(Document)
            .options(joinedload(Document.course), joinedload(Document.level),
                     joinedload(Document.uploaded_by), joinedload(Document.approved_by))
            .filter(Document.id == doc_id).first()
        )
        if not doc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
        return doc

    # ── Serve file ────────────────────────────────────────────────────────────
    def _resolve_file(self, doc_id: str, action: AuditAction, user: User,
                      request: Request | None, disposition: str):
        """
        Returns either:
          - FileResponse (local storage)
          - RedirectResponse to presigned URL (S3)
        """
        doc = self.db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
        if doc.status != DocumentStatus.AVAILABLE:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Document is not yet available")

        # Increment download count (best-effort)
        try:
            doc.download_count += 1
            self.db.commit()
        except Exception:
            self.db.rollback()

        AuditService(self.db).log(user_id=user.id, action=action, document_id=doc_id, request=request)

        backend = getattr(doc, "storage_backend", "local") or "local"

        if backend == "s3":
            url = self.s3.presigned_url(doc.file_path, disposition=disposition, filename=doc.file_name)
            return RedirectResponse(url=url, status_code=307)
        else:
            abs_path = Path(doc.file_path).resolve()
            if not abs_path.exists():
                raise HTTPException(status.HTTP_404_NOT_FOUND, "File not found on disk")
            cd = f"{disposition}; filename*=UTF-8''{quote(doc.file_name)}"
            return FileResponse(path=abs_path, media_type="application/pdf",
                                headers={"Content-Disposition": cd})

    def serve_view(self, doc_id: str, user: User, request: Request | None):
        return self._resolve_file(doc_id, AuditAction.VIEW, user, request, "inline")

    def serve_download(self, doc_id: str, user: User, request: Request | None):
        return self._resolve_file(doc_id, AuditAction.DOWNLOAD, user, request, "attachment")
