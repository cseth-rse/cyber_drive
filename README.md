# Cyber Drive Platform

## Overview

Cyber Drive is a centralized academic repository platform designed for Computer Engineering students. It provides a secure, fast, and user‑friendly way to access and manage academic resources such as syllabi, past examination questions, lecture notes, and handouts. Students can browse materials by level (100L–500L) and course, search for documents, preview PDFs directly in the browser, and download them. Contributors (trusted users) can upload new documents, which are scanned for viruses and approved by administrators before publication.

The platform was developed as a school project to demonstrate a full‑stack, production‑ready web application, with emphasis on security, scalability, and a great user experience. It is built using modern, open‑source technologies and follows industry best practices.

---

> The majority of the features mentioned in the software have not yet been implemented, though we plan to add them in the future. Features such as downloading, sharing, liking, commenting, and reading PDFs online are still under development. As a result, we have decided not to upload this version of the software at this time. 
The reason these features haven't been completed yet is that the programming work has been carried out by a very small team. Although we have used AI tools as assistants to help with development, each person still had to implement the code manually to ensure quality and avoid errors. This traditional coding process, combined with the limited Despite these challenges, we remain committed to building a stable and fully functional platform, and we will release the software once the core features are ready for a reliable user experience.
number of contributors, has slowed the pace of development.

## What It Is

Cyber Drive is a **full‑stack web application** consisting of:

- A **React‑based frontend** that delivers a responsive, intuitive interface.
- A **Python‑based backend (FastAPI)** that provides a RESTful API, handles business logic, and manages data persistence.
- A **PostgreSQL database** for relational data.
- **Redis** for caching and background job queuing.
- **MinIO** (or AWS S3) for object storage of documents and thumbnails.
- **Celery** for asynchronous tasks such as virus scanning and thumbnail generation.
- **ClamAV** for virus scanning uploaded files.

## What It Does

- **User Authentication & Roles**  
  - Register and log in using email OTP (one‑time password).  
  - Three roles: `STUDENT` (view‑only), `CONTRIBUTOR` (can upload, needs approval), `ADMIN` (full control, including user management and document approval).  
  - Secure JWT tokens with refresh token rotation.

- **Document Browsing & Search**  
  - Browse by academic level (100L to 500L) and course.  
  - Full‑text search across document titles, descriptions, course codes, and extracted PDF text.  
  - Paginated results with cursor‑based navigation for performance.

- **Document Upload & Processing**  
  - Upload PDF or DOCX files (up to 50 MB).  
  - Duplicate detection using SHA‑256 checksum.  
  - Virus scanning via ClamAV (infected files are rejected).  
  - Thumbnail generation (first page preview).  
  - Approval workflow for contributor uploads (admins approve/reject).

- **Document Access**  
  - View documents inline via a built‑in PDF.js viewer.  
  - Download documents with a single click.  
  - All file access is logged (audit trail) and served via secure, time‑limited URLs.

- **Versioning**  
  - Maintain multiple versions of a document with change logs.  
  - Users can access any previous version.

- **Bulk Download**  
  - Select multiple documents and download them as a ZIP archive (processed asynchronously).

- **Admin Analytics**  
  - Real‑time statistics: total users, documents, downloads, storage usage.  
  - Daily activity trends, most popular documents, most active users, storage breakdown by level.  
  - Queryable audit logs for security and compliance.

- **Audit Logging**  
  - Every view, download, upload, approval, rejection, and administrative action is logged with IP address and user agent.

- **High Availability & Scalability** (designed for production)  
  - Multiple application instances behind a load balancer.  
  - PostgreSQL primary‑replica replication with automated failover.  
  - Connection pooling with PgBouncer.  
  - Redis for caching and Celery broker (can be made highly available with Sentinel).  
  - Stateless application design for horizontal scaling.

## What It Is Not Supposed To Do

- **Real‑time collaboration** – The platform does not support simultaneous editing or live chat.
- **Content management system (CMS)** – It is not designed for creating or editing rich content; it focuses on document storage and retrieval.
- **File‑sharing service** – All access is controlled; files are not publicly accessible.
- **Replacement for official university portals** – It is a supplementary tool for students.
- **Distributed microservices** – Currently a modular monolith; microservices could be extracted later if needed.

---

## How It Works (Architecture)

The platform follows a **modular monolith** architecture: the backend is a single codebase organized into feature modules (Auth, Users, Documents, Courses, etc.) that communicate via in‑memory calls and share a database. Asynchronous tasks are offloaded to a task queue (Celery) with Redis as the broker.

**Request Flow (Simplified)**  

1. **Frontend** (React) sends HTTP requests to the backend API.  
2. **Load Balancer** (HAProxy/Nginx) distributes traffic across multiple backend instances.  
3. **Backend (FastAPI)** processes the request:
   - Authentication via JWT (access token in `Authorization` header).
   - Authorization via role‑based guards.
   - Input validation using Pydantic models.
   - Business logic executed in service layers.
   - Data persistence via SQLAlchemy (PostgreSQL).
   - Cached responses retrieved from Redis (if applicable).
4. **File Operations**:
   - **Upload**: File is streamed directly to object storage (MinIO/S3). A Celery task is triggered for virus scanning and thumbnail generation.
   - **Download**: A presigned URL is generated and returned; the frontend downloads directly from object storage, reducing server load.
5. **Background Jobs** (Celery workers):
   - Virus scan: communicates with ClamAV daemon.
   - Thumbnail generation: uses pdf2image (poppler) to render first page.
   - Bulk ZIP: fetches files, creates archive, stores it temporarily, and provides a download link.

**Data Storage**  

- **PostgreSQL**: relational data – users, levels, courses, documents, versions, audit logs.  
- **Redis**: caching (level/course lists, search results) and Celery broker.  
- **MinIO / S3**: object storage for document files and thumbnails.

---

### Demo images of cyber_drive, How far we've come 
- Home Page (Dark Mode) : ![Home Page](https://github.com/cseth-rse/cyber_drive/raw/main/assets/cyber_home_1.png)
- Home Page (Light Mode) : ![Home Page](https://github.com/cseth-rse/cyber_drive/raw/main/assets/cyber_home.png)
## Technology Stack

| Layer               | Technology                                                                 | Reason                                                                                                                       |
|---------------------|----------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------|
| **Frontend**        | React 18, TypeScript, Vite, Tailwind CSS, React Query, React Router, PDF.js | Industry‑standard libraries for a fast, type‑safe, and responsive UI. Vite ensures rapid development.                       |
| **Backend**         | Python 3.10+, FastAPI                                                      | FastAPI offers high performance, automatic OpenAPI docs, built‑in validation (Pydantic), and async support. Python is widely used in academia. |
| **Database**        | PostgreSQL 15+                                                             | ACID compliant, full‑text search, JSON support, replication, and open source.                                                |
| **ORM & Migrations**| SQLAlchemy 2.0, Alembic                                                    | SQLAlchemy is the most powerful ORM for Python; Alembic handles migrations elegantly.                                        |
| **Validation**      | Pydantic                                                                   | Seamlessly integrated with FastAPI, ensures type safety.                                                                     |
| **Authentication**  | python‑jose, passlib, bcrypt                                               | JWT for stateless auth; bcrypt for secure hashing of OTPs and refresh tokens.                                                |
| **Task Queue**      | Celery                                                                     | Mature, distributed task queue with Redis broker; handles background jobs reliably.                                          |
| **Caching**         | Redis                                                                      | In‑memory data store for caching and Celery broker; high performance.                                                        |
| **Object Storage**  | MinIO (self‑hosted) or AWS S3                                              | S3‑compatible object storage ensures scalability and durability. MinIO is free for self‑hosting.                             |
| **Virus Scanning**  | ClamAV                                                                     | Open‑source antivirus engine; integrated via clamd for real‑time scanning.                                                   |
| **Thumbnail Generation** | pdf2image, Pillow                                                      | pdf2image (wraps poppler) converts PDF pages to images; Pillow processes them.                                               |
| **Monitoring**      | Prometheus, Grafana                                                        | Prometheus collects metrics (via `prometheus‑client`); Grafana visualizes them.                                              |
| **Load Balancing**  | HAProxy / Nginx                                                            | Proven, high‑performance, free software.                                                                                     |
| **Database Pooling**| PgBouncer                                                                  | Lightweight connection pooler for PostgreSQL; essential for high concurrency.                                                |
| **Replication/Failover** | repmgr / Patroni                                                       | repmgr simplifies PostgreSQL replication management and automated failover.                                                  |
| **Containerization**| Docker (optional)                                                          | Consistent development and deployment environments.                                                                          |
| **CI/CD**           | GitHub Actions                                                             | Automates testing, building, and deployment.                                                                                 |

---

## Why These Technologies Were Chosen

As a school project, we aimed to use technologies that are:

- **Modern and widely adopted** – React, FastAPI, PostgreSQL, and Redis are popular in the industry, making the skills learned transferable.
- **Free and open‑source** – No licensing costs; accessible to everyone.
- **Well‑documented** – Extensive community support and learning resources.
- **Performant** – FastAPI is one of the fastest Python frameworks; React ensures a smooth UI.
- **Scalable** – The stack can grow with the project, from a single server to a clustered environment.
- **Secure** – Built‑in features (JWT, bcrypt, ClamAV) and best practices are followed.

Python was chosen for the backend because it is the primary language taught in our computer engineering curriculum, and its rich ecosystem (especially for data processing and PDF manipulation) makes it ideal for an academic repository.

---

## Features in Detail

### 1. Authentication & User Roles
- **Email OTP**: Users register with their email; a 6‑digit OTP is sent (via Ethereal for development, SendGrid for production). OTP expires in 10 minutes.
- **JWT Tokens**: Access token (15 min) stored in memory; refresh token (7 days) as HTTP‑only cookie with rotation.
- **Roles**: `STUDENT`, `CONTRIBUTOR`, `ADMIN`. Role‑based access control (RBAC) protects endpoints.

### 2. Document Management
- **Upload**: Admin/contributor uploads PDF/DOCX (max 50 MB). File is streamed directly to object storage; metadata saved to DB.
- **Duplicate Detection**: SHA‑256 checksum prevents duplicates.
- **Virus Scanning**: Celery task sends file to ClamAV; infected files are rejected and deleted.
- **Thumbnail Generation**: First page rendered as JPEG, stored in object storage.
- **Approval Workflow**: Contributor uploads → `PENDING_APPROVAL` → Admin approves/rejects.
- **Versioning**: New versions can be uploaded; each version stored separately with change log.
- **Metadata**: Title, description, course, level, uploader, download count, timestamps.

### 3. Document Access
- **Browsing**: Endpoints for levels, courses, and documents (paginated). Filter by level/course.
- **Viewing**: `GET /documents/{id}/view` returns a presigned URL for inline viewing (logs `VIEW`).
- **Downloading**: `GET /documents/{id}/download` returns a presigned URL with attachment disposition (logs `DOWNLOAD`).
- **Search**: Full‑text search across title, description, course code, and extracted PDF text (PostgreSQL tsvector).
- **Bulk Download**: `POST /bulk-downloads` with list of document IDs. Returns a job ID; a background worker creates a ZIP and provides a temporary download link.

### 4. Audit Logging
- All significant actions (`LOGIN`, `LOGOUT`, `UPLOAD`, `VIEW`, `DOWNLOAD`, `APPROVE`, `REJECT`, `DELETE`) are recorded in `audit_logs`.
- Includes user ID, IP address, user agent, timestamp, and optional metadata (e.g., rejection reason).
- Admins can query logs via `/audit-logs` endpoint with filters.

### 5. Admin Analytics
- `/admin/stats/overview`: Total users, documents, downloads, storage.
- `/admin/stats/daily`: Daily activity trends (last N days).
- `/admin/stats/top-documents`: Most downloaded documents.
- `/admin/stats/top-users`: Most active users.
- `/admin/stats/storage-by-level`: Storage per academic level.

### 6. Monitoring & Health
- `/metrics` endpoint exposing Prometheus metrics (request count, duration, queue sizes, etc.).
- `/health` endpoint verifying database, Redis, object storage, ClamAV connectivity.

### 7. High Availability Design
- Multiple backend instances behind a load balancer (HAProxy).
- PostgreSQL primary + standby with automated failover (repmgr).
- PgBouncer for connection pooling.
- Redis for caching and Celery broker (Sentinel for HA optional).
- Stateless application; all persistent data in database and object storage.

---

## Getting Started

### Prerequisites
- **Node.js** 18+ and npm/yarn (for frontend)
- **Python** 3.10+ and pip (for backend)
- **PostgreSQL** 15+
- **Redis** 7+
- **MinIO** (or AWS S3 account)
- **ClamAV** (with clamd running)
- **Poppler** (for thumbnail generation; e.g., `brew install poppler` on macOS, `apt-get install poppler-utils` on Linux)
- **Optional**: Docker for containerized setup

### Installation

#### 1. Clone the repository
```bash
git clone https://github.com/your-org/cyber-drive.git
cd cyber-drive
```

#### 2. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your database, Redis, MinIO, etc. settings
alembic upgrade head
python scripts/seed.py  # seed levels and courses
uvicorn app.main:app --reload  # start backend (http://localhost:8000)
# In another terminal, start Celery worker
celery -A app.tasks worker --loglevel=info
```

#### 3. Frontend Setup
```bash
cd ../frontend
cp .env.example .env
# Set VITE_API_URL=http://localhost:8000
npm install
npm run dev  # start frontend (http://localhost:5173)
```

#### 4. Ensure Required Services Are Running
- PostgreSQL
- Redis
- MinIO (or configure S3)
- ClamAV daemon (`clamd`)

### Running with Docker (Alternative)
A `docker-compose.yml` is provided in the `backend` directory. It sets up PostgreSQL, Redis, MinIO, and ClamAV. However, note that ClamAV in Docker requires additional configuration; refer to the `docker-compose` file for details.

```bash
cd backend
docker-compose up -d
# Then start the backend and frontend locally as above, pointing to the Docker services.
```

---

## Project Structure

```
cyber-drive/
├── backend/                 # Python FastAPI backend
│   ├── app/
│   │   ├── api/             # Route handlers (controllers)
│   │   ├── core/            # Configuration, security, dependencies
│   │   ├── models/          # SQLAlchemy models
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── services/        # Business logic
│   │   ├── tasks/           # Celery tasks
│   │   └── utils/           # Helper functions
│   ├── migrations/           # Alembic migrations
│   ├── scripts/              # Seed scripts, maintenance
│   ├── tests/                # Test suite
│   ├── .env.example
│   ├── docker-compose.yml
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                # React frontend
│   ├── public/
│   ├── src/
│   │   ├── components/      # Reusable UI components
│   │   ├── pages/           # Page-level components
│   │   ├── hooks/           # Custom React hooks
│   │   ├── services/        # API client (axios)
│   │   ├── utils/           # Helper functions
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── .env.example
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   └── ...
├── docs/                    # Additional documentation
├── README.md
└── LICENSE
```

---

## Development

### Running Tests
- **Backend**:
  ```bash
  cd backend
  pytest tests/unit
  pytest tests/integration
  ```
- **Frontend**:
  ```bash
  cd frontend
  npm test
  ```

### Linting & Formatting
- Backend: `flake8`, `black`
- Frontend: ESLint, Prettier

### API Documentation
When the backend is running, interactive API docs are available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## Deployment

For production deployment: None for now 
---

## Limitations & Future Work

- **Search**: Currently uses PostgreSQL full‑text search; could be enhanced with Elasticsearch for more advanced features (fuzzy matching, relevance tuning).
- **Real‑time notifications**: Not implemented; could be added with WebSockets for admin alerts (e.g., new upload pending approval).
- **Machine learning**: No recommendation engine; could suggest documents based on user behavior.
- **Microservices**: The monolith can be split into independent services (auth, documents, analytics) if the platform grows significantly.
- **Mobile app**: A React Native or Flutter app could be built to consume the same API.

---

## License

This project is licensed under the MIT License – see the [LICENSE](LICENSE) file for details.

---

## Acknowledgements

- FastAPI, SQLAlchemy, Celery, and React communities for their excellent documentation.
- PostgreSQL, Redis, MinIO for robust open‑source solutions.
- ClamAV for virus scanning capabilities.
- Our instructors and peers for guidance and feedback.

---
CONTRIBUTORS 

**Note**: Cyber Drive was developed as a school project to demonstrate full‑stack development skills. It is not intended for production use without a thorough security review and load testing.
