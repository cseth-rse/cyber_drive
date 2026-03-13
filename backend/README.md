# Cyber Drive Backend

## Project Overview

Cyber Drive is a centralized academic repository backend designed for Computer Engineering students. It provides a secure, scalable, and high-performance API for managing and accessing academic documents such as syllabi, past questions, lecture notes, and handouts. The backend is built with Python and modern open-source technologies, following best practices in security, scalability, and maintainability.

This project was developed as a school project to demonstrate full-stack development capabilities, with emphasis on robust architecture, data integrity, and production-readiness.

---

## What It Is

Cyber Drive Backend is a RESTful API service that powers the Cyber Drive academic repository. It handles user authentication, document management, search, versioning, bulk downloads, and administrative analytics. The backend is designed to be modular, allowing future extensions or migration to microservices if needed.

## What It Does

- **User Management**: Register and authenticate users via email OTP. Supports three roles: Student, Contributor, and Admin.
- **Document Upload & Processing**: Contributors and admins can upload PDF/DOCX files. Files are virus-scanned (ClamAV), checked for duplicates (SHA-256), and thumbnails are generated.
- **Document Browsing & Access**: Students can browse documents by level (100L–500L) and course, view document metadata, and preview/download files via secure, time-limited URLs.
- **Full-Text Search**: Search across document titles, descriptions, course codes, and extracted PDF text using PostgreSQL full-text search.
- **Audit Logging**: Every view, download, upload, approval, and rejection is logged with IP and user agent for accountability.
- **Versioning**: Maintain multiple versions of a document with change logs. Users can access any previous version.
- **Bulk Download**: Select multiple documents and download them as a ZIP archive (processed asynchronously).
- **Admin Analytics**: Real-time statistics on users, documents, downloads, storage usage, and popular content.
- **High Availability & Disaster Recovery**: Designed to run in a clustered environment with load balancing, database replication, and automated failover.
- **Monitoring**: Exposes metrics for Prometheus and health checks for orchestration tools.

## What It Is Not Supposed To Do

- **Not a real-time collaboration platform**: No live editing or concurrent user interaction on documents.
- **Not a content management system (CMS)**: No rich text editing or content creation within the platform.
- **Not a replacement for official university portals**: It is a supplementary tool for students.
- **Not a file-sharing service**: All files are protected and access is strictly controlled by authentication and authorization.
- **Not a distributed system (yet)**: It is a modular monolith; microservices are a possible future evolution but not implemented.

---

## How It Works (Architecture Overview)

The backend follows a modular monolith architecture, where features are organized into modules (Auth, Users, Documents, Courses, etc.) that communicate via in-memory calls and share a database. Asynchronous tasks (virus scanning, thumbnail generation, bulk ZIP creation) are offloaded to a task queue (Celery) backed by Redis.

**Request Flow**:

1. **Client (Frontend)** sends HTTP requests to the API.
2. **Load Balancer** (HAProxy/Nginx) distributes traffic across multiple backend instances.
3. **NestJS/FastAPI** application processes the request:
   - Authentication via JWT (access token in Authorization header).
   - Authorization via role-based guards.
   - Input validation using Pydantic/Zod (FastAPI uses Pydantic natively).
   - Business logic executed in service layers.
   - Data persistence via SQLAlchemy (PostgreSQL).
   - Cached responses retrieved from Redis (if applicable).
4. **File Operations**:
   - Uploads: Files are streamed directly to object storage (MinIO/S3). Metadata stored in DB, and a Celery task is triggered for virus scanning and thumbnail generation.
   - Downloads: A presigned URL is generated from object storage and returned to the client; the client downloads directly from storage, reducing server load.
5. **Background Tasks**:
   - Virus scan: Celery worker communicates with ClamAV daemon.
   - Thumbnail generation: Uses `pdf2image` (requires poppler) to render first page and uploads to storage.
   - Bulk ZIP: Worker fetches files from storage, creates a ZIP, uploads it back, and provides a temporary download link.

**Data Storage**:

- **PostgreSQL**: Stores all relational data: users, levels, courses, documents, versions, audit logs, etc.
- **Redis**: Used for caching (level/course lists, search results) and as a message broker for Celery.
- **MinIO / AWS S3**: Object storage for document files and thumbnails.

**Security Measures**:

- JWT access tokens (short-lived) and HTTP-only refresh tokens (with rotation).
- Role-based access control (RBAC).
- Input validation and sanitization.
- File scanning with ClamAV.
- Rate limiting (per IP and per user).
- HTTPS enforced, security headers via Helmet.
- CSRF protection via SameSite cookies and custom headers.

---

## Technology Stack (Why These Choices?)

| Component            | Technology                    | Reason                                                                                                                       |
|----------------------|-------------------------------|------------------------------------------------------------------------------------------------------------------------------|
| **Programming Language** | Python 3.10+                  | Python offers rapid development, excellent libraries for data processing, and is widely used in academic settings.            |
| **Web Framework**    | FastAPI                       | FastAPI provides automatic OpenAPI documentation, high performance (async), built-in validation with Pydantic, and is easy to learn. |
| **Database**         | PostgreSQL 15+                | PostgreSQL is ACID-compliant, supports full-text search, JSON fields, and has robust replication features. Free and open-source. |
| **ORM**              | SQLAlchemy 2.0 + Alembic      | SQLAlchemy is the most powerful and flexible ORM for Python. Alembic handles migrations elegantly.                           |
| **Validation**       | Pydantic                      | Integrated with FastAPI, ensures type-safe request/response handling.                                                         |
| **Authentication**   | python-jose, passlib, bcrypt  | JWT for stateless authentication; bcrypt for secure password/OTP hashing.                                                     |
| **Task Queue**       | Celery                         | Mature distributed task queue with Redis broker; handles background jobs reliably.                                           |
| **Caching**          | Redis                          | In-memory data store for caching and Celery broker. High performance and easy to set up.                                     |
| **Object Storage**   | MinIO (self-hosted) or AWS S3  | S3-compatible object storage ensures scalability and durability. MinIO is free for self-hosting.                             |
| **Virus Scanning**   | ClamAV                         | Open-source antivirus engine; can be integrated via clamd for real-time scanning.                                            |
| **Thumbnail Generation** | pdf2image, Pillow           | pdf2image (wraps poppler) converts PDF pages to images; Pillow processes them.                                               |
| **Monitoring**       | Prometheus, Grafana            | Prometheus collects metrics from the app (via `prometheus-client`); Grafana visualizes them.                                 |
| **Load Balancing**   | HAProxy / Nginx                | Proven, high-performance, free software for traffic distribution.                                                            |
| **Database Pooling** | PgBouncer                      | Lightweight connection pooler for PostgreSQL; essential for high concurrency.                                                |
| **Replication/Failover** | repmgr / Patroni            | repmgr simplifies PostgreSQL replication management and automated failover.                                                  |
| **Containerization** | Docker (optional)              | For consistent development and deployment environments.                                                                      |
| **CI/CD**            | GitHub Actions                 | Free for public/private repos; automates testing and deployment.                                                             |

**Why Not Node.js?**  
While Node.js is a viable option, Python was chosen for this school project due to the team's familiarity, extensive libraries for academic tasks (e.g., text extraction), and the desire to demonstrate backend development in a language commonly taught in computer engineering curricula.

---

## Features in Detail

### 1. Authentication & Authorization

- **Email OTP Registration/Login**: Users register with email; a 6-digit OTP is sent via SMTP (Ethereal for development, SendGrid for production). OTP expires in 10 minutes.
- **JWT Tokens**: Access token (15 min) in memory, refresh token (7 days) as HTTP-only cookie with rotation.
- **Roles**: `STUDENT` (view only), `CONTRIBUTOR` (can upload, needs approval), `ADMIN` (full control).
- **Rate Limiting**: Per IP and per user; stricter on auth endpoints.

### 2. Document Management

- **Upload**: Admin/contributor uploads PDF/DOCX (max 50MB). File is streamed to object storage; metadata saved to DB.
- **Duplicate Detection**: SHA-256 checksum prevents duplicate uploads.
- **Virus Scanning**: Celery task sends file to ClamAV; infected files are rejected and deleted.
- **Thumbnail Generation**: First page rendered as JPEG, stored in object storage.
- **Approval Workflow**: Contributor uploads → PENDING_APPROVAL → Admin approves/rejects.
- **Versioning**: New versions can be uploaded for existing documents; each version stored separately with change log.
- **Metadata**: Title, description, course, level, uploader, download count, timestamps.

### 3. Document Access

- **Browsing**: GET endpoints for levels, courses, and documents (paginated).
- **Viewing**: `GET /documents/{id}/view` returns presigned URL for inline viewing (logs VIEW).
- **Downloading**: `GET /documents/{id}/download` returns presigned URL with attachment disposition (logs DOWNLOAD).
- **Search**: Full-text search across title, description, course code, and extracted PDF text (via PostgreSQL tsvector).
- **Bulk Download**: `POST /bulk-downloads` with list of document IDs. Returns job ID; worker creates ZIP and provides download link when ready.

### 4. Audit Logging

- All significant actions (LOGIN, LOGOUT, UPLOAD, VIEW, DOWNLOAD, APPROVE, REJECT, DELETE) are recorded in `audit_logs` table.
- Includes user ID, IP address, user agent, timestamp, and optional metadata (e.g., rejection reason).
- Admins can query logs via `/audit-logs` endpoint with filters.

### 5. Admin Analytics

- `/admin/stats/overview`: Total users, documents, downloads, storage.
- `/admin/stats/daily`: Daily activity trends.
- `/admin/stats/top-documents`: Most downloaded.
- `/admin/stats/top-users`: Most active users.
- `/admin/stats/storage-by-level`: Storage per academic level.

### 6. Scalability & High Availability

- Multiple application instances behind load balancer (HAProxy).
- PostgreSQL primary-replica with automated failover (repmgr).
- Connection pooling via PgBouncer.
- Redis for caching and Celery broker (optional Sentinel for HA).
- Stateless application; session data in Redis.
- Object storage (MinIO) distributed mode for durability.

### 7. Monitoring

- `/metrics` endpoint exposing Prometheus metrics (request count, duration, queue sizes, etc.).
- Health check endpoint `/health` verifying DB, Redis, object storage, ClamAV.
- Sentry integration for error tracking.

---

## Getting Started

### Prerequisites

- Python 3.10+
- PostgreSQL 15+
- Redis 7+
- MinIO (or AWS S3 account)
- ClamAV (with clamd running)
- Poppler (for thumbnail generation)

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-org/cyber-drive-backend.git
   cd cyber-drive-backend
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```


5. **Run database migrations**:
   ```bash
   alembic upgrade head
   ```

6. **Seed initial data (levels and courses)**:
   ```bash
   python scripts/seed.py
   ```

7. **Start the development server**:
   ```bash
   uvicorn main:app --reload
   ```

8. **Start Celery worker** (in a separate terminal):
   ```bash
   celery -A tasks worker --loglevel=info
   ```

9. **Ensure required services are running**:
   - PostgreSQL
   - Redis
   - MinIO (or configure S3)
   - ClamAV daemon (`clamd`)

### Running with Docker (Alternative)

A `docker-compose.yml` is provided for quick setup of all services (PostgreSQL, Redis, MinIO, ClamAV). However, note that ClamAV in Docker requires additional configuration; refer to the `docker-compose` file for details.

---

## API Documentation

Once the server is running, interactive API documentation is available at:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

The API follows RESTful conventions and uses JSON for request/response bodies. Authentication is via Bearer token.

---

## Testing

- **Unit tests**: `pytest tests/unit`
- **Integration tests**: `pytest tests/integration` (requires test database)
- **End-to-end tests**: (optional) Use Postman or custom scripts.

Run all tests with coverage:
```bash
pytest --cov=app tests/
```

---

## Deployment

For production deployment, we are not yet ready for production because we are still working on some very useful features that makes the platform unique 
and esy to use.

---

## Project Structure

```
cyber-drive-backend/
├── app/
│   ├── api/                 # Route handlers (controllers)
│   ├── core/                 # Configuration, security, dependencies
│   ├── models/               # SQLAlchemy models
│   ├── schemas/              # Pydantic schemas
│   ├── services/             # Business logic
│   ├── tasks/                # Celery tasks
│   └── utils/                # Helper functions
├── migrations/               # Alembic migrations
├── scripts/                  # Seed scripts, maintenance
├── tests/                    # Test suite
├── .env.example
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── README.md
└── ...
```

---

## Limitations & Future Work

- **Search**: Currently uses PostgreSQL full-text search; could be enhanced with Elasticsearch for more advanced features.
- **Real-time notifications**: Not implemented; could be added with WebSockets for admin alerts.
- **Machine learning**: No recommendation engine; could be added to suggest documents based on user behavior.
- **Microservices**: The monolith can be split into independent services (auth, documents, analytics) if scale requires.

---

## Contributors

- Joseph Anointed
- Team Members: Lawretta, Jeffery, Daniel, Emmanuel, David, Sunday and Chidera

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgements

- FastAPI, SQLAlchemy, Celery communities for excellent documentation.
- PostgreSQL, Redis, MinIO for robust open-source solutions.
- ClamAV for virus scanning capabilities.
- Our instructors and peers for feedback and support.

---

**Note**: This backend is designed as a school project and is not intended for production use without thorough security review and load testing.
