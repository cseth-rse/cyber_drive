# app/main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.auth.router import router as auth_router
from app.admin.router import router as admin_router
from app.audit.router import router as audit_router
from app.analytics.router import router as analytics_router
from app.config import get_settings
from app.database import get_db
from app.documents.router import router as docs_router
from app.levels.router import router as levels_router
from app.monitoring.logging_config import configure_logging
from app.monitoring.metrics import setup_metrics
from app.security import add_security_headers, make_rate_limiter

settings = get_settings()
configure_logging(settings)

# Optional Sentry
if settings.sentry_dsn:
    try:
        import sentry_sdk
        sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.1)
    except ImportError:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.using_s3:
        from app.storage.s3 import S3Service
        S3Service(settings).ensure_bucket()
    yield


# ── Rate limiter (Redis-backed for multi-instance deployments) ────────────────
limiter = make_rate_limiter(settings)

app = FastAPI(
    title="Cyber Drive API",
    version="5.0.0",
    description="Academic repository backend — Phase 5",
    docs_url="/api",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── Security headers middleware ────────────────────────────────────────────────
# CORRECT ORDER — CORS outermost, handles preflight and adds headers to all responses
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "X-Requested-With"],
)
app.add_middleware(BaseHTTPMiddleware, dispatch=add_security_headers)

if settings.metrics_enabled:
    setup_metrics(app)

app.include_router(auth_router)
app.include_router(docs_router)
app.include_router(levels_router)
app.include_router(admin_router)
app.include_router(audit_router)
app.include_router(analytics_router)


@app.get("/health", tags=["Health"])
def health():
    """Enhanced health check — DB, Redis, S3, ClamAV."""
    from app.monitoring.health import run_health_checks
    db = next(get_db())
    result = run_health_checks(db, settings)
    code = 200 if result["status"] != "down" else 503
    return Response(
        content=__import__("json").dumps(result),
        status_code=code,
        media_type="application/json",
    )


@app.get("/health/detailed", tags=["Health"])
def health_detailed():
    """Alias for /health — kept for backwards compat with Phase 5 spec."""
    return health()
