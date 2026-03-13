# Cyber Drive — Frontend

React + Vite frontend for the Cyber Drive academic repository.  
Connects to the FastAPI backend at `http://localhost:3000`.

## Quick start

```bash
npm install
cp .env.example .env   # set VITE_API_URL if backend runs on a different port
npm run dev
```

Opens at **http://localhost:5173**.

## Backend first

Make sure the FastAPI backend is running:

```bash
# In the backend folder:
uvicorn app.main:app --reload --port 3000
celery -A app.workers.tasks worker --loglevel=info
```

## Pages & routes

| Route | Page | Auth required |
|-------|------|---------------|
| `/` | Home — hero, level cards, recent uploads | No |
| `/materials` | Browse by level/course, search, filter | No |
| `/document/:id` | Document detail, PDF viewer, download | View: no · Download: yes |
| `/upload` | Upload form (PDF, title, level, course) | Yes |
| `/login` | OTP login — email → 6-digit code | — |
| `/profile` | Uploads, saved, badges, activity tabs | Yes |

## Auth flow

1. `POST /auth/register` — sends OTP to email.
2. `POST /auth/verify-otp` — verifies code, returns access token (in body) and refresh token (HttpOnly cookie).
3. Access token lives in memory only (never localStorage).
4. On 401, the Axios interceptor silently calls `POST /auth/refresh` using the cookie.

## Theme

Three themes — Dark · Light · High Contrast — switched from the navbar.  
The preference is persisted in `localStorage`.
