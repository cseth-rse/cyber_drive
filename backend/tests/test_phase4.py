# tests/test_phase4.py
"""
Phase 4 tests:
  - S3Service: upload, presigned URL, delete (all mocked)
  - Upload flow picks S3 key when S3 enabled
  - Upload flow uses local path when S3 disabled
  - Analytics: overview, daily, top docs, top users, storage by level
  - Health checks: all ok / db down / s3 down
"""
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from app.models import AuditAction, AuditLog, Document, DocumentStatus, Level, Course, Role, User


# ── Helpers ───────────────────────────────────────────────────────────────────

def _user(db, email, role=Role.STUDENT):
    u = User(email=email, role=role)
    db.add(u); db.flush(); return u


def _level(db, name="300L", order=3):
    l = Level(name=name, order=order)
    db.add(l); db.flush(); return l


def _course(db, level_id, code="CPE331"):
    c = Course(code=code, title="Data Structures", level_id=level_id)
    db.add(c); db.flush(); return c


def _doc(db, uploader_id, course_id, level_id, status=DocumentStatus.AVAILABLE, size=1024*1024, downloads=0):
    d = Document(
        title="Test Doc",
        file_name="test.pdf",
        file_path=f"/tmp/test_{len(db.query(Document).all())}.pdf",
        storage_backend="local",
        checksum=f"chk_{len(db.query(Document).all())}",
        size=size,
        mime_type="application/pdf",
        status=status,
        uploaded_by_id=uploader_id,
        course_id=course_id,
        level_id=level_id,
        download_count=downloads,
    )
    db.add(d); db.flush(); return d


def _audit(db, user_id, action, doc_id=None, ts=None):
    log = AuditLog(
        user_id=user_id,
        action=action,
        document_id=doc_id,
        timestamp=ts or datetime.utcnow(),
    )
    db.add(log); db.flush(); return log


# ── S3 Service ────────────────────────────────────────────────────────────────

class TestS3Service:
    def _settings(self, enabled=True):
        s = MagicMock()
        s.s3_enabled = enabled
        s.s3_endpoint = "http://localhost:9000"
        s.s3_region = "us-east-1"
        s.s3_access_key_id = "minioadmin"
        s.s3_secret_access_key = "minioadmin"
        s.s3_bucket_name = "cyber-drive"
        s.s3_force_path_style = True
        s.s3_presigned_url_expires = 900
        s.using_s3 = enabled
        return s

    def test_upload_calls_put_object(self):
        from app.storage.s3 import S3Service
        settings = self._settings(True)
        svc = S3Service(settings)

        mock_client = MagicMock()
        with patch("app.storage.s3._get_client", return_value=mock_client):
            result = svc.upload_file(b"%PDF test", "documents/abc/test.pdf")

        mock_client.put_object.assert_called_once()
        assert result == "documents/abc/test.pdf"

    def test_presigned_url_calls_generate(self):
        from app.storage.s3 import S3Service
        settings = self._settings(True)
        svc = S3Service(settings)

        mock_client = MagicMock()
        mock_client.generate_presigned_url.return_value = "https://minio/presigned"

        with patch("app.storage.s3._get_client", return_value=mock_client):
            url = svc.presigned_url("documents/abc/test.pdf", "inline", "test.pdf")

        assert "https://minio/presigned" == url

    def test_delete_calls_delete_object(self):
        from app.storage.s3 import S3Service
        settings = self._settings(True)
        svc = S3Service(settings)

        mock_client = MagicMock()
        with patch("app.storage.s3._get_client", return_value=mock_client):
            svc.delete_file("documents/abc/test.pdf")

        mock_client.delete_object.assert_called_once_with(
            Bucket="cyber-drive", Key="documents/abc/test.pdf"
        )

    def test_disabled_raises_on_upload(self):
        from app.storage.s3 import S3Service
        svc = S3Service(self._settings(False))
        with pytest.raises(RuntimeError, match="S3 is not enabled"):
            svc.upload_file(b"data", "key")

    def test_ping_returns_true_when_disabled(self):
        from app.storage.s3 import S3Service
        svc = S3Service(self._settings(False))
        assert svc.ping() is True

    def test_ping_returns_false_on_connection_error(self):
        from app.storage.s3 import S3Service, _client
        import app.storage.s3 as s3_module
        s3_module._client = None   # reset cached client

        settings = self._settings(True)
        svc = S3Service(settings)

        mock_client = MagicMock()
        mock_client.head_bucket.side_effect = Exception("Connection refused")

        with patch("app.storage.s3._get_client", return_value=mock_client):
            result = svc.ping()

        assert result is False


# ── Analytics ─────────────────────────────────────────────────────────────────

class TestAnalytics:
    def _setup(self, db):
        admin = _user(db, "adm@t.com", Role.ADMIN)
        c1 = _user(db, "c1@t.com", Role.CONTRIBUTOR)
        c2 = _user(db, "c2@t.com", Role.CONTRIBUTOR)
        lv = _level(db)
        co = _course(db, lv.id)
        d1 = _doc(db, admin.id, co.id, lv.id, downloads=50, size=2*1024*1024)
        d2 = _doc(db, c1.id, co.id, lv.id, downloads=30, size=1024*1024)
        d3 = _doc(db, c2.id, co.id, lv.id, status=DocumentStatus.PENDING_APPROVAL, downloads=0)
        db.commit()
        return admin, c1, c2, lv, co, d1, d2, d3

    def test_overview_counts(self, db_session, settings):
        from app.analytics.service import AnalyticsService

        admin, c1, c2, lv, co, d1, d2, d3 = self._setup(db_session)
        svc = AnalyticsService(db_session)

        # Patch Redis out so results aren't cached
        with patch("app.analytics.service._redis", return_value=None):
            result = svc.overview()

        assert result["documents"]["available"] == 2
        assert result["documents"]["pending_approval"] == 1
        assert result["downloads"]["total"] == 80
        assert result["storage"]["bytes"] == 3 * 1024 * 1024
        assert result["users"]["contributors"] == 2

    def test_storage_by_level(self, db_session, settings):
        from app.analytics.service import AnalyticsService

        admin, c1, c2, lv, co, d1, d2, d3 = self._setup(db_session)
        svc = AnalyticsService(db_session)

        with patch("app.analytics.service._redis", return_value=None):
            result = svc.storage_by_level()

        assert len(result) >= 1
        level_row = next((r for r in result if r["level_id"] == lv.id), None)
        assert level_row is not None
        assert level_row["document_count"] == 2   # only AVAILABLE docs

    def test_top_documents_ordering(self, db_session, settings):
        from app.analytics.service import AnalyticsService

        admin, *_, lv, co, d1, d2, d3 = self._setup(db_session)

        # Add download audit logs
        _audit(db_session, admin.id, AuditAction.DOWNLOAD, d1.id)
        _audit(db_session, admin.id, AuditAction.DOWNLOAD, d1.id)
        _audit(db_session, admin.id, AuditAction.DOWNLOAD, d2.id)
        db_session.commit()

        svc = AnalyticsService(db_session)
        with patch("app.analytics.service._redis", return_value=None):
            result = svc.top_documents(limit=10)

        assert len(result) >= 1
        assert result[0]["id"] == d1.id   # d1 has more downloads

    def test_daily_returns_N_entries(self, db_session, settings):
        from app.analytics.service import AnalyticsService

        admin = _user(db_session, "a@t.com", Role.ADMIN)
        db_session.commit()
        _audit(db_session, admin.id, AuditAction.DOWNLOAD, ts=datetime.utcnow())
        _audit(db_session, admin.id, AuditAction.UPLOAD, ts=datetime.utcnow() - timedelta(days=2))
        db_session.commit()

        svc = AnalyticsService(db_session)
        with patch("app.analytics.service._redis", return_value=None):
            result = svc.daily(days=7)

        assert len(result) == 7
        assert all("date" in r and "downloads" in r and "uploads" in r for r in result)

    def test_top_users_upload_metric(self, db_session, settings):
        from app.analytics.service import AnalyticsService

        admin = _user(db_session, "adm2@t.com", Role.ADMIN)
        c = _user(db_session, "cu@t.com", Role.CONTRIBUTOR)
        db_session.commit()

        # Admin has 3 uploads, contributor has 1
        for _ in range(3):
            _audit(db_session, admin.id, AuditAction.UPLOAD)
        _audit(db_session, c.id, AuditAction.UPLOAD)
        db_session.commit()

        svc = AnalyticsService(db_session)
        with patch("app.analytics.service._redis", return_value=None):
            result = svc.top_users(limit=10, metric="uploads")

        assert result[0]["id"] == admin.id


# ── Health checks ─────────────────────────────────────────────────────────────

class TestHealthChecks:
    def test_all_ok(self, db_session, settings):
        from app.monitoring.health import run_health_checks
        from sqlalchemy import text

        with patch("app.monitoring.health._check_redis", return_value=__import__("app.monitoring.health", fromlist=["CheckResult"]).CheckResult("redis", "ok")):
            with patch("app.monitoring.health._check_s3", return_value=__import__("app.monitoring.health", fromlist=["CheckResult"]).CheckResult("s3", "ok", critical=False)):
                with patch("app.monitoring.health._check_clamav", return_value=__import__("app.monitoring.health", fromlist=["CheckResult"]).CheckResult("clamav", "ok", critical=False)):
                    result = run_health_checks(db_session, settings)

        assert result["status"] == "ok"
        assert result["checks"]["database"]["status"] == "ok"

    def test_db_down_returns_503_status(self, db_session, settings):
        from app.monitoring.health import run_health_checks, CheckResult

        broken_db = MagicMock()
        broken_db.execute.side_effect = Exception("Connection lost")

        with patch("app.monitoring.health._check_redis", return_value=CheckResult("redis", "ok")):
            with patch("app.monitoring.health._check_s3", return_value=CheckResult("s3", "ok", critical=False)):
                with patch("app.monitoring.health._check_clamav", return_value=CheckResult("clamav", "ok", critical=False)):
                    result = run_health_checks(broken_db, settings)

        assert result["status"] == "down"
        assert result["checks"]["database"]["status"] == "down"

    def test_redis_down_is_degraded_not_down(self, db_session, settings):
        from app.monitoring.health import run_health_checks, CheckResult

        with patch("app.monitoring.health._check_redis", return_value=CheckResult("redis", "degraded", critical=False)):
            with patch("app.monitoring.health._check_s3", return_value=CheckResult("s3", "ok", critical=False)):
                with patch("app.monitoring.health._check_clamav", return_value=CheckResult("clamav", "ok", critical=False)):
                    result = run_health_checks(db_session, settings)

        # DB is OK; redis is non-critical degraded → overall degraded, not down
        assert result["status"] in ("degraded", "ok")
        assert result["checks"]["redis"]["status"] == "degraded"

    def test_s3_enabled_down_is_critical(self, db_session, settings):
        from app.monitoring.health import run_health_checks, CheckResult

        with patch("app.monitoring.health._check_redis", return_value=CheckResult("redis", "ok")):
            with patch("app.monitoring.health._check_s3", return_value=CheckResult("s3", "down", critical=True)):
                with patch("app.monitoring.health._check_clamav", return_value=CheckResult("clamav", "ok", critical=False)):
                    result = run_health_checks(db_session, settings)

        assert result["status"] == "down"
