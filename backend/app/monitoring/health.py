# app/monitoring/health.py
"""
Enhanced health check: tests DB, Redis, S3 (if enabled), and ClamAV.
Returns 200 OK when all critical services are up, 503 when any critical one fails.
"""
import logging
from dataclasses import dataclass, field

from fastapi import Request
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@dataclass
class CheckResult:
    name: str
    status: str       # "ok" | "degraded" | "down"
    detail: str = ""
    critical: bool = True


def _check_db(db: Session) -> CheckResult:
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        return CheckResult("database", "ok")
    except Exception as exc:
        return CheckResult("database", "down", str(exc), critical=True)


def _check_redis(redis_url: str) -> CheckResult:
    try:
        import redis as _redis
        r = _redis.from_url(redis_url, socket_timeout=2)
        r.ping()
        return CheckResult("redis", "ok")
    except Exception as exc:
        return CheckResult("redis", "degraded", str(exc), critical=False)


def _check_s3(settings) -> CheckResult:
    if not settings.s3_enabled:
        return CheckResult("s3", "ok", "local storage mode", critical=False)
    try:
        from app.storage.s3 import S3Service
        ok = S3Service(settings).ping()
        return CheckResult("s3", "ok" if ok else "down", critical=True)
    except Exception as exc:
        return CheckResult("s3", "down", str(exc), critical=True)


def _check_clamav() -> CheckResult:
    try:
        import pyclamd
        try:
            cd = pyclamd.ClamdUnixSocket()
            cd.ping()
        except Exception:
            cd = pyclamd.ClamdNetworkSocket()
            cd.ping()
        return CheckResult("clamav", "ok", critical=False)
    except Exception as exc:
        return CheckResult("clamav", "degraded", "ClamAV not reachable — scan fallback active", critical=False)


def run_health_checks(db: Session, settings) -> dict:
    checks = [
        _check_db(db),
        _check_redis(settings.redis_url),
        _check_s3(settings),
        _check_clamav(),
    ]

    any_critical_down = any(c.status == "down" and c.critical for c in checks)
    overall = "down" if any_critical_down else (
        "degraded" if any(c.status in ("down", "degraded") for c in checks) else "ok"
    )

    return {
        "status": overall,
        "version": "4.0.0",
        "checks": {c.name: {"status": c.status, "detail": c.detail} for c in checks},
    }
