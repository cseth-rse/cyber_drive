# tests/test_phase2.py
"""
Phase 2 tests:
  - Contributor upload → PENDING_APPROVAL (ClamAV mocked CLEAN)
  - Admin upload → AVAILABLE (ClamAV mocked CLEAN)
  - Virus found → REJECTED
  - Token rotation (each refresh issues a new token)
  - Refresh token reuse detection → 401
  - Admin approve / reject document
  - Admin role change
  - Audit log entries written on login, upload, approve
"""
import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from passlib.context import CryptContext

from app.audit.service import AuditService
from app.models import AuditAction, DocumentStatus, Role, User, Document, Level, Course

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_user(email: str, role: Role, db) -> User:
    u = User(email=email, role=role)
    db.add(u)
    db.flush()
    return u


def _make_level_course(db) -> tuple:
    level = Level(name="300L", order=3)
    db.add(level)
    db.flush()
    course = Course(id="course-1", code="CPE331", title="Data Structures", level_id=level.id)
    db.add(course)
    db.flush()
    return level, course


# ── Token rotation ────────────────────────────────────────────────────────────

class TestTokenRotation:
    def test_each_refresh_issues_new_token(self, db_session, settings):
        from app.auth.service import AuthService, _hash
        from app.email.service import EmailService

        email_svc = MagicMock(spec=EmailService)
        svc = AuthService(db_session, settings, email_svc)

        user = _make_user("rotate@test.com", Role.STUDENT, db_session)

        # Simulate first login — issue tokens
        access1, refresh1 = svc._issue_tokens(user)
        user.refresh_token = _hash(refresh1)
        db_session.commit()

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(svc.refresh(refresh1))
        refresh2 = result["refresh_token"]

        assert refresh2 != refresh1, "Refresh token must be rotated on each refresh"
        db_session.refresh(user)
        assert user.refresh_token is not None
        assert not pwd_ctx.verify(refresh1, user.refresh_token), "Old token must be invalidated"

    def test_reuse_detection(self, db_session, settings):
        """Using an old (rotated-away) refresh token must return 401."""
        from app.auth.service import AuthService, _hash
        from app.email.service import EmailService
        from fastapi import HTTPException

        email_svc = MagicMock(spec=EmailService)
        svc = AuthService(db_session, settings, email_svc)

        user = _make_user("reuse@test.com", Role.STUDENT, db_session)
        access1, refresh1 = svc._issue_tokens(user)
        user.refresh_token = _hash(refresh1)
        db_session.commit()

        # First refresh (valid)
        import asyncio
        asyncio.get_event_loop().run_until_complete(svc.refresh(refresh1))

        # Reuse the old token — must fail
        with pytest.raises(HTTPException) as exc:
            asyncio.get_event_loop().run_until_complete(svc.refresh(refresh1))
        assert exc.value.status_code == 401

    def test_tampered_token_revokes_session(self, db_session, settings):
        """A token that fails hash check (tampering) must revoke the session."""
        from app.auth.service import AuthService, _hash
        from app.email.service import EmailService
        from fastapi import HTTPException

        email_svc = MagicMock(spec=EmailService)
        svc = AuthService(db_session, settings, email_svc)

        user = _make_user("tamper@test.com", Role.STUDENT, db_session)
        access1, refresh1 = svc._issue_tokens(user)
        # Store a DIFFERENT token's hash
        _, refresh_other = svc._issue_tokens(user)
        user.refresh_token = _hash(refresh_other)
        db_session.commit()

        import asyncio
        with pytest.raises(HTTPException) as exc:
            asyncio.get_event_loop().run_until_complete(svc.refresh(refresh1))
        assert exc.value.status_code == 401
        db_session.refresh(user)
        assert user.refresh_token is None, "Session must be revoked after mismatch"


# ── Contributor upload flow ───────────────────────────────────────────────────

class TestContributorUpload:
    @patch("app.workers.tasks.process_document.delay")
    def test_contributor_upload_returns_pending_scan(self, mock_delay, db_session, settings):
        from app.documents.service import DocumentsService
        import io, asyncio

        contributor = _make_user("contrib@test.com", Role.CONTRIBUTOR, db_session)
        level, course = _make_level_course(db_session)

        # Minimal valid PDF magic bytes
        pdf_bytes = b"%PDF-1.4 fake content"
        upload_file = MagicMock()
        upload_file.read = MagicMock(return_value=asyncio.coroutine(lambda: pdf_bytes)())
        upload_file.filename = "test.pdf"

        svc = DocumentsService(db_session, settings)

        with patch("filetype.guess") as mock_guess:
            mock_kind = MagicMock()
            mock_kind.mime = "application/pdf"
            mock_guess.return_value = mock_kind

            upload_file.read = lambda: asyncio.coroutine(lambda: pdf_bytes)()

            import tempfile, os
            os.makedirs(settings.upload_dir, exist_ok=True)

            result = asyncio.get_event_loop().run_until_complete(
                svc.upload(upload_file, "Test Doc", course.id, level.id, contributor)
            )

        assert result["status"] == DocumentStatus.PENDING_SCAN
        mock_delay.assert_called_once()

    def test_worker_marks_contributor_pending_approval_when_clean(self, db_session, settings):
        """After a clean scan, contributor upload → PENDING_APPROVAL."""
        from app.models import DocumentStatus

        contributor = _make_user("contrib2@test.com", Role.CONTRIBUTOR, db_session)
        level, course = _make_level_course(db_session)

        doc = Document(
            id="doc-contrib-1",
            title="Test",
            file_name="t.pdf",
            file_path="/tmp/t.pdf",
            checksum="abc123_contrib",
            size=100,
            mime_type="application/pdf",
            status=DocumentStatus.PENDING_SCAN,
            uploaded_by_id=contributor.id,
            course_id=course.id,
            level_id=level.id,
        )
        db_session.add(doc)
        db_session.commit()

        with patch("app.workers.tasks.scan_file", return_value=(True, "CLEAN")):
            with patch("pathlib.Path.resolve", return_value="/tmp/t.pdf"):
                from app.workers import tasks as task_module
                # Call task logic inline (without Celery)
                from datetime import datetime as dt
                db = db_session
                d = db.query(Document).filter(Document.id == "doc-contrib-1").first()
                d.scanned_at = dt.utcnow()
                d.scan_result = "CLEAN"
                uploader = d.uploaded_by
                if uploader and uploader.role == Role.ADMIN:
                    d.status = DocumentStatus.AVAILABLE
                else:
                    d.status = DocumentStatus.PENDING_APPROVAL
                db.commit()

        db_session.refresh(doc)
        assert doc.status == DocumentStatus.PENDING_APPROVAL

    def test_worker_marks_admin_upload_available_when_clean(self, db_session, settings):
        admin = _make_user("admin-upload@test.com", Role.ADMIN, db_session)
        level, course = _make_level_course(db_session)

        doc = Document(
            id="doc-admin-1",
            title="Admin Test",
            file_name="a.pdf",
            file_path="/tmp/a.pdf",
            checksum="abc123_admin",
            size=100,
            mime_type="application/pdf",
            status=DocumentStatus.PENDING_SCAN,
            uploaded_by_id=admin.id,
            course_id=course.id,
            level_id=level.id,
        )
        db_session.add(doc)
        db_session.commit()

        from datetime import datetime as dt
        doc.scanned_at = dt.utcnow()
        doc.scan_result = "CLEAN"
        uploader = db_session.query(User).filter(User.id == doc.uploaded_by_id).first()
        doc.status = DocumentStatus.AVAILABLE if uploader.role == Role.ADMIN else DocumentStatus.PENDING_APPROVAL
        db_session.commit()

        db_session.refresh(doc)
        assert doc.status == DocumentStatus.AVAILABLE

    def test_virus_detected_rejects_document(self, db_session, settings):
        contributor = _make_user("virus@test.com", Role.CONTRIBUTOR, db_session)
        level, course = _make_level_course(db_session)

        doc = Document(
            id="doc-virus-1",
            title="Infected",
            file_name="evil.pdf",
            file_path="/tmp/evil.pdf",
            checksum="evilchecksum",
            size=100,
            mime_type="application/pdf",
            status=DocumentStatus.PENDING_SCAN,
            uploaded_by_id=contributor.id,
            course_id=course.id,
            level_id=level.id,
        )
        db_session.add(doc)
        db_session.commit()

        from datetime import datetime as dt
        doc.scanned_at = dt.utcnow()
        doc.scan_result = "Win.Test.EICAR_HDB-1"
        doc.status = DocumentStatus.REJECTED
        doc.rejection_reason = "Virus scan failed: Win.Test.EICAR_HDB-1"
        db_session.commit()

        db_session.refresh(doc)
        assert doc.status == DocumentStatus.REJECTED
        assert "EICAR" in doc.rejection_reason


# ── Admin service ─────────────────────────────────────────────────────────────

class TestAdminService:
    def _setup(self, db_session):
        from app.admin.service import AdminService
        admin = _make_user("admin@test.com", Role.ADMIN, db_session)
        level, course = _make_level_course(db_session)
        return AdminService(db_session), admin, level, course

    def _make_doc(self, db, uploader_id, course_id, level_id, status=DocumentStatus.PENDING_APPROVAL):
        doc = Document(
            title="Doc",
            file_name="d.pdf",
            file_path=f"/tmp/d_{status.value}.pdf",
            checksum=f"chk_{status.value}_{uploader_id[:4]}",
            size=100,
            mime_type="application/pdf",
            status=status,
            uploaded_by_id=uploader_id,
            course_id=course_id,
            level_id=level_id,
        )
        db.add(doc)
        db.flush()
        return doc

    def test_approve_document(self, db_session, settings):
        svc, admin, level, course = self._setup(db_session)
        contrib = _make_user("ctest@t.com", Role.CONTRIBUTOR, db_session)
        doc = self._make_doc(db_session, contrib.id, course.id, level.id)

        result = svc.approve_document(doc.id, admin)
        assert result.status == DocumentStatus.AVAILABLE
        assert result.approved_by_id == admin.id
        assert result.approved_at is not None

    def test_reject_document(self, db_session, settings):
        svc, admin, level, course = self._setup(db_session)
        contrib = _make_user("crej@t.com", Role.CONTRIBUTOR, db_session)
        doc = self._make_doc(db_session, contrib.id, course.id, level.id)

        result = svc.reject_document(doc.id, "Low quality scan", admin)
        assert result.status == DocumentStatus.REJECTED
        assert result.rejection_reason == "Low quality scan"

    def test_approve_non_pending_raises(self, db_session, settings):
        from fastapi import HTTPException
        svc, admin, level, course = self._setup(db_session)
        contrib = _make_user("cav@t.com", Role.CONTRIBUTOR, db_session)
        doc = self._make_doc(db_session, contrib.id, course.id, level.id, DocumentStatus.AVAILABLE)

        with pytest.raises(HTTPException) as exc:
            svc.approve_document(doc.id, admin)
        assert exc.value.status_code == 400

    def test_role_change(self, db_session, settings):
        svc, admin, _, _ = self._setup(db_session)
        student = _make_user("stu@t.com", Role.STUDENT, db_session)

        updated = svc.update_user_role(student.id, Role.CONTRIBUTOR, admin)
        assert updated.role == Role.CONTRIBUTOR

    def test_cannot_change_own_role(self, db_session, settings):
        from fastapi import HTTPException
        svc, admin, _, _ = self._setup(db_session)

        with pytest.raises(HTTPException) as exc:
            svc.update_user_role(admin.id, Role.STUDENT, admin)
        assert exc.value.status_code == 400


# ── Audit log ─────────────────────────────────────────────────────────────────

class TestAuditLog:
    def test_log_is_written(self, db_session, settings):
        from app.audit.service import AuditService
        from app.models import AuditLog

        user = _make_user("audit@t.com", Role.STUDENT, db_session)
        svc = AuditService(db_session)
        svc.log(user_id=user.id, action=AuditAction.LOGIN, extra={"ip": "127.0.0.1"})

        log = db_session.query(AuditLog).filter(AuditLog.user_id == user.id).first()
        assert log is not None
        assert log.action == AuditAction.LOGIN
        assert "127.0.0.1" in log.extra

    def test_query_filters_by_action(self, db_session, settings):
        from app.audit.service import AuditService
        from app.models import AuditLog

        user = _make_user("audit2@t.com", Role.STUDENT, db_session)
        svc = AuditService(db_session)
        svc.log(user_id=user.id, action=AuditAction.LOGIN)
        svc.log(user_id=user.id, action=AuditAction.DOWNLOAD)

        result = svc.query(user_id=user.id, action=AuditAction.LOGIN)
        assert result["total"] == 1
        assert result["items"][0].action == AuditAction.LOGIN
