# Cyber Drive Backend — Phase 5 (Production Ready)

FastAPI + SQLAlchemy academic repository backend — all five phases complete.

---

## What's new in Phase 5

| Feature | Details |
|---|---|
| **Security headers** | CSP, HSTS, X-Frame-Options, Referrer-Policy, Permissions-Policy on every response |
| **Distributed rate limiting** | Redis-backed SlowAPI — limits shared across all app instances |
| **Per-endpoint rate limits** | Auth 10/min · Upload 20/min · Download 60/min · Admin 200/min |
| **HAProxy config** | Round-robin, health checks, TLS 1.2+, HTTP→HTTPS redirect |
| **Nginx alternative** | Drop-in Nginx config for those who prefer it |
| **Keepalived VIP** | Floating IP between lb1/lb2 — automatic LB failover |
| **PostgreSQL replication** | Streaming replication + repmgr automatic failover |
| **PgBouncer** | Transaction-mode connection pooling (1000 clients → 25 Postgres conns) |
| **Redis Sentinel** | 3-node Sentinel config for Redis HA |
| **Prometheus + Grafana** | 11-panel dashboard, alerting rules for errors/latency/replication/disk |
| **Alertmanager** | Email + Slack alerts for high error rate, latency, instance down |
| **k6 load tests** | Three test scripts: browse/download, auth flow, admin upload spike |
| **Production docs** | Deployment guide, DR runbook, security checklist, scaling guidelines |
| **Smoke test script** | `scripts/smoke_test.sh` — post-deploy validation |
| **DB failover test** | `scripts/test_db_failover.sh` — DR drill script |

---

## Full feature history

| Phase | Features |
|---|---|
| **1** | OTP auth, document upload (local), PDF MIME check, dedup, Celery worker |
| **2** | CONTRIBUTOR role, ClamAV scanning, approval workflow, audit logging, token rotation |
| **3** | *(skipped — Phase 4 built directly on Phase 2)* |
| **4** | S3/MinIO storage, presigned URLs, admin analytics, Prometheus metrics, health checks, structured logging |
| **5** | HA infrastructure, security headers, distributed rate limiting, DR runbook, load tests |

---

## Quick start (development)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in values

# PostgreSQL (one-time)
sudo -u postgres psql -c "CREATE USER cyber_user WITH PASSWORD 'cyber_pass';"
sudo -u postgres psql -c "CREATE DATABASE cyber_db OWNER cyber_user;"

alembic upgrade head
python seed.py

uvicorn app.main:app --reload --port 3000
celery -A app.workers.tasks worker --loglevel=info
```

Swagger: http://localhost:3000/api  
Health: http://localhost:3000/health  
Metrics: http://localhost:3000/metrics  

---

## Production deployment (summary)

Full step-by-step instructions: **[docs/production-deployment.md](docs/production-deployment.md)**

```
lb1 + lb2  → HAProxy + Keepalived  (VIP failover)
app1 + app2 → FastAPI + Celery + PM2
db1 + db2   → PostgreSQL primary + standby + repmgr
pgbouncer   → connection pooler on db1 (port 6432)
redis       → single with AOF, or Redis Sentinel cluster
minio       → self-hosted S3-compatible storage
monitor     → Prometheus + Grafana + Alertmanager
cloudflare  → CDN, DDoS, free WAF
```

---

## Directory structure

```
cyber-drive-backend/
├── app/
│   ├── admin/          # user management, approve/reject/delete
│   ├── analytics/      # 5 stats endpoints (cached in Redis)
│   ├── audit/          # audit log service + query API
│   ├── auth/           # OTP, JWT, token rotation
│   ├── documents/      # upload, list, view, download
│   ├── email/          # SMTP OTP delivery
│   ├── levels/         # levels + courses
│   ├── monitoring/     # health checks, Prometheus, JSON logging
│   ├── storage/        # S3/MinIO abstraction
│   ├── workers/        # Celery tasks + ClamAV scanner
│   ├── config.py       # all settings via .env
│   ├── models.py       # SQLAlchemy models
│   ├── schemas.py      # Pydantic request/response
│   ├── security.py     # security headers + distributed rate limiter
│   └── main.py         # FastAPI app wiring
├── alembic/            # database migrations
├── docs/
│   ├── production-deployment.md
│   ├── disaster-recovery-runbook.md
│   ├── security-checklist.md
│   └── scaling-guidelines.md
├── infra/
│   ├── haproxy/        # haproxy.cfg
│   ├── nginx/          # cyber-drive.conf (alternative to HAProxy)
│   ├── keepalived/     # lb1 + lb2 configs
│   ├── pgbouncer/      # pgbouncer.ini + userlist.txt
│   ├── prometheus/     # prometheus.yml + alert rules
│   ├── grafana/        # dashboard-overview.json
│   ├── alertmanager/   # alertmanager.yml
│   ├── redis-sentinel/ # redis.conf + sentinel.conf
│   └── repmgr/         # postgresql-primary.conf + repmgr configs
├── load-tests/
│   ├── browse_and_download.js  # main load test (500 VU ramp)
│   ├── auth_flow.js            # auth rate limit stress test
│   └── admin_upload.js         # upload pipeline spike test
├── scripts/
│   ├── smoke_test.sh           # post-deploy validation
│   └── test_db_failover.sh     # DR drill
├── tests/
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_documents.py
│   ├── test_phase2.py          # contributor flow, admin, audit
│   └── test_phase4.py          # S3, analytics, health checks
├── migrate_phase1_to_phase2.py
├── migrate_files_to_s3.py
├── seed.py
├── requirements.txt
└── .env.example
```

---

## API reference

### Auth
| Method | Path | Description |
|---|---|---|
| POST | `/auth/register` | Send OTP to email |
| POST | `/auth/verify-otp` | Verify OTP → access token + HttpOnly refresh cookie |
| POST | `/auth/refresh` | Rotate tokens (`X-Requested-With: XMLHttpRequest` required) |
| POST | `/auth/logout` | Revoke session |

### Documents
| Method | Path | Access |
|---|---|---|
| POST | `/documents/upload` | CONTRIBUTOR, ADMIN |
| GET | `/documents` | Any auth |
| GET | `/documents/:id` | Any auth |
| GET | `/documents/:id/view` | Any auth — logs VIEW |
| GET | `/documents/:id/download` | Any auth — logs DOWNLOAD |

### Admin
| Method | Path | Description |
|---|---|---|
| GET | `/admin/users` | List users (filter by role) |
| PATCH | `/admin/users/:id/role` | Change role |
| GET | `/admin/documents/pending` | Pending approval queue |
| POST | `/admin/documents/:id/approve` | Approve |
| POST | `/admin/documents/:id/reject` | Reject with reason |
| DELETE | `/admin/documents/:id` | Delete permanently |

### Analytics
| Method | Path | Description |
|---|---|---|
| GET | `/admin/stats/overview` | Users, docs, downloads, storage |
| GET | `/admin/stats/daily?days=30` | Daily activity chart data |
| GET | `/admin/stats/top-documents` | Most downloaded |
| GET | `/admin/stats/top-users?metric=uploads` | Most active users |
| GET | `/admin/stats/storage-by-level` | Disk usage per level |

### Audit
| Method | Path | Description |
|---|---|---|
| GET | `/audit-logs` | Query with filters (user, doc, action, date range) |

### Health & Monitoring
| Method | Path | Description |
|---|---|---|
| GET | `/health` | DB + Redis + S3 + ClamAV status; 503 if critical service down |
| GET | `/health/detailed` | Alias for /health |
| GET | `/metrics` | Prometheus scrape endpoint |

---

## Promote user to ADMIN
```sql
UPDATE users SET role = 'ADMIN' WHERE email = 'admin@example.com';
```

## Run tests
```bash
pytest --tb=short -q
```

## Run load tests
```bash
# Install k6: https://k6.io/docs/get-started/installation/

# Main load test (ramp to 500 VUs)
k6 run -e BASE_URL=http://localhost:3000 \
        -e ACCESS_TOKEN=your_token \
        load-tests/browse_and_download.js

# Upload spike test
k6 run -e BASE_URL=http://localhost:3000 \
        -e ACCESS_TOKEN=your_admin_token \
        -e COURSE_ID=your-course-uuid \
        -e LEVEL_ID=1 \
        load-tests/admin_upload.js
```

## Post-deploy smoke test
```bash
chmod +x scripts/smoke_test.sh
./scripts/smoke_test.sh https://yourdomain.com your_access_token
```
