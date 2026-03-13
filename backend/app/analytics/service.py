# app/analytics/service.py
"""
Admin analytics: all queries are cached in Redis for 1 hour to avoid hammering the DB.
If Redis is unavailable, queries run live every time.
"""
import json
import logging
from datetime import datetime, timedelta

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.models import AuditAction, AuditLog, Document, DocumentStatus, Level, User

logger = logging.getLogger(__name__)
_CACHE_TTL = 3600  # 1 hour


def _redis():
    """Return a Redis client or None if unavailable."""
    try:
        import redis as _redis
        from app.config import get_settings
        r = _redis.from_url(get_settings().redis_url, decode_responses=True, socket_timeout=1)
        r.ping()
        return r
    except Exception:
        return None


def _cached(key: str, fn):
    r = _redis()
    if r:
        try:
            cached = r.get(key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass
    result = fn()
    if r:
        try:
            r.setex(key, _CACHE_TTL, json.dumps(result, default=str))
        except Exception:
            pass
    return result


class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    # ── Overview ──────────────────────────────────────────────────────────────

    def overview(self) -> dict:
        def _compute():
            total_users = self.db.query(func.count(User.id)).scalar() or 0
            total_docs = self.db.query(func.count(Document.id)).filter(
                Document.status == DocumentStatus.AVAILABLE
            ).scalar() or 0
            pending_approval = self.db.query(func.count(Document.id)).filter(
                Document.status == DocumentStatus.PENDING_APPROVAL
            ).scalar() or 0
            pending_scan = self.db.query(func.count(Document.id)).filter(
                Document.status == DocumentStatus.PENDING_SCAN
            ).scalar() or 0
            total_downloads = self.db.query(func.sum(Document.download_count)).scalar() or 0
            total_storage_bytes = self.db.query(func.sum(Document.size)).filter(
                Document.status == DocumentStatus.AVAILABLE
            ).scalar() or 0
            contributors = self.db.query(func.count(User.id)).filter(
                User.role == "CONTRIBUTOR"
            ).scalar() or 0
            admins = self.db.query(func.count(User.id)).filter(
                User.role == "ADMIN"
            ).scalar() or 0
            return {
                "users": {
                    "total": total_users,
                    "contributors": contributors,
                    "admins": admins,
                    "students": total_users - contributors - admins,
                },
                "documents": {
                    "available": total_docs,
                    "pending_approval": pending_approval,
                    "pending_scan": pending_scan,
                },
                "downloads": {"total": total_downloads},
                "storage": {
                    "bytes": total_storage_bytes,
                    "mb": round(total_storage_bytes / (1024 * 1024), 2) if total_storage_bytes else 0,
                    "gb": round(total_storage_bytes / (1024 * 1024 * 1024), 3) if total_storage_bytes else 0,
                },
            }
        return _cached("analytics:overview", _compute)

    # ── Daily activity ────────────────────────────────────────────────────────

    def daily(self, days: int = 30) -> list[dict]:
        days = min(days, 90)

        def _compute():
            since = datetime.utcnow() - timedelta(days=days)
            conn = self.db.bind.connect() if hasattr(self.db, "bind") else None

            # Use raw SQL for DATE_TRUNC (PostgreSQL) / DATE (SQLite)
            dialect = self.db.bind.dialect.name if self.db.bind else "sqlite"

            if dialect == "postgresql":
                sql = text("""
                    SELECT
                        DATE_TRUNC('day', timestamp) AS day,
                        action,
                        COUNT(*) AS count
                    FROM audit_logs
                    WHERE timestamp >= :since
                      AND action IN ('DOWNLOAD', 'UPLOAD')
                    GROUP BY day, action
                    ORDER BY day ASC
                """)
            else:
                sql = text("""
                    SELECT
                        DATE(timestamp) AS day,
                        action,
                        COUNT(*) AS count
                    FROM audit_logs
                    WHERE timestamp >= :since
                      AND action IN ('DOWNLOAD', 'UPLOAD')
                    GROUP BY day, action
                    ORDER BY day ASC
                """)

            rows = self.db.execute(sql, {"since": since}).fetchall()

            # Build a day-keyed dict
            result: dict[str, dict] = {}
            for row in rows:
                day_str = str(row[0])[:10]
                if day_str not in result:
                    result[day_str] = {"date": day_str, "downloads": 0, "uploads": 0}
                if row[1] == "DOWNLOAD":
                    result[day_str]["downloads"] = row[2]
                elif row[1] == "UPLOAD":
                    result[day_str]["uploads"] = row[2]

            # Fill missing days with zeroes
            all_days = []
            for i in range(days):
                d = (datetime.utcnow() - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
                all_days.append(result.get(d, {"date": d, "downloads": 0, "uploads": 0}))
            return all_days

        return _cached(f"analytics:daily:{days}", _compute)

    # ── Top documents ─────────────────────────────────────────────────────────

    def top_documents(self, limit: int = 10) -> list[dict]:
        limit = min(limit, 50)

        def _compute():
            rows = (
                self.db.query(Document, func.count(AuditLog.id).label("view_count"))
                .join(AuditLog, AuditLog.document_id == Document.id, isouter=True)
                .filter(AuditLog.action == AuditAction.DOWNLOAD)
                .filter(Document.status == DocumentStatus.AVAILABLE)
                .group_by(Document.id)
                .order_by(func.count(AuditLog.id).desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "id": doc.id,
                    "title": doc.title,
                    "course_code": doc.course.code if doc.course else None,
                    "level": doc.level.name if doc.level else None,
                    "download_count": doc.download_count,
                    "audit_download_count": count,
                    "size_mb": round(doc.size / (1024 * 1024), 2),
                }
                for doc, count in rows
            ]

        return _cached(f"analytics:top_docs:{limit}", _compute)

    # ── Top users ─────────────────────────────────────────────────────────────

    def top_users(self, limit: int = 10, metric: str = "uploads") -> list[dict]:
        limit = min(limit, 50)
        action = AuditAction.UPLOAD if metric == "uploads" else AuditAction.DOWNLOAD

        def _compute():
            rows = (
                self.db.query(User, func.count(AuditLog.id).label("count"))
                .join(AuditLog, AuditLog.user_id == User.id, isouter=True)
                .filter(AuditLog.action == action)
                .group_by(User.id)
                .order_by(func.count(AuditLog.id).desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "id": user.id,
                    "email": user.email,
                    "role": user.role,
                    "count": count,
                    "metric": metric,
                }
                for user, count in rows
            ]

        return _cached(f"analytics:top_users:{metric}:{limit}", _compute)

    # ── Storage by level ──────────────────────────────────────────────────────

    def storage_by_level(self) -> list[dict]:
        def _compute():
            rows = (
                self.db.query(
                    Level.id,
                    Level.name,
                    func.count(Document.id).label("doc_count"),
                    func.sum(Document.size).label("total_bytes"),
                    func.sum(Document.download_count).label("total_downloads"),
                )
                .outerjoin(Document, Document.level_id == Level.id)
                .filter((Document.status == DocumentStatus.AVAILABLE) | (Document.id == None))
                .group_by(Level.id, Level.name)
                .order_by(Level.id)
                .all()
            )
            return [
                {
                    "level_id": r[0],
                    "level_name": r[1],
                    "document_count": r[2] or 0,
                    "storage_bytes": r[3] or 0,
                    "storage_mb": round((r[3] or 0) / (1024 * 1024), 2),
                    "total_downloads": r[4] or 0,
                }
                for r in rows
            ]

        return _cached("analytics:storage_by_level", _compute)
