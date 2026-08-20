# Northern New Mexico College Student Planning Hub

The NNMC Student Planning Hub is a React/FastAPI application dedicated to
Northern New Mexico College. Students can explore NNMC career pathways and
official catalog programs, complete an academic intake, and build and save a
semester-by-semester education plan.

## Architecture

- `ChatbotUI/`: React 18 single-page application built with Vite and Tailwind
- `fastapi_backend/`: async FastAPI API using SQLAlchemy 2, Alembic, and PostgreSQL
- College Scorecard: external federal institution metrics
- Optional integrations: SMTP advisor email, Twilio SMS, and OpenRouter
- Deployment: Vercel-compatible frontend and a non-root Python container for the API

The frontend defaults to same-origin `/api` requests in production. A reverse
proxy must route `/api` to the backend, or `VITE_API_BASE_URL` must be set at
frontend build time. If a separate API origin is used, add only that exact HTTPS
origin to the `connect-src` directive in `ChatbotUI/vercel.json`.

## Prerequisites

- Node.js 22.12-22.x (CI uses 22.20.0)
- npm with the committed `package-lock.json`
- Python 3.13 recommended (the package metadata supports Python 3.11+)
- PostgreSQL 14+ recommended
- A [College Scorecard API key](https://collegescorecard.ed.gov/data/documentation/)

Docker is optional for the backend.

## Environment configuration

Copy the safe examples and replace placeholders locally. Never commit real credentials.

```powershell
Copy-Item fastapi_backend/.env.example fastapi_backend/.env
Copy-Item ChatbotUI/.env.example ChatbotUI/.env
```

Backend variables required for a real deployment:

- `ENVIRONMENT=production`
- `DATABASE_URL`: async PostgreSQL URL using the `postgresql+asyncpg` scheme
- `JWT_SECRET`: at least 32 unpredictable characters
- `COLLEGE_SCORECARD_API_KEY`
- `CORS_ORIGINS`: comma-separated exact HTTPS frontend origins; no wildcard

SMTP, Twilio, and OpenRouter variables are optional unless those product
features are enabled. See both `.env.example` files for the complete list.

## Local development

### Backend

```powershell
cd fastapi_backend
py -3.13 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.lock
.venv\Scripts\python.exe -m alembic upgrade head
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

The API is available at `http://localhost:8000`. Liveness and dependency
readiness endpoints are `GET /health/live` and `GET /health/ready`.

### Frontend

```powershell
cd ChatbotUI
npm ci
npm run dev
```

The development site is available at `http://localhost:5173`.

## Database and catalog setup

Run migrations as an explicit release step before starting new application instances:

```powershell
cd fastapi_backend
.venv\Scripts\python.exe -m alembic heads
.venv\Scripts\python.exe -m alembic upgrade head
```

The backend also contains `scripts/sync_nnmc_catalog.py` for an intentional NNMC
catalog synchronization. Review its arguments and take a database backup before
running it against persistent data. Never run a destructive migration or catalog
sync against production without a tested restore point.

## Verification

Frontend:

```powershell
cd ChatbotUI
npm ci
npm run lint
npm test
npm run build
npm audit --omit=dev --audit-level=high
```

Backend:

```powershell
cd fastapi_backend
.venv\Scripts\python.exe -m ruff check app tests scripts
.venv\Scripts\python.exe -m black --check app tests scripts
.venv\Scripts\python.exe -m mypy app
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m pip check
.venv\Scripts\python.exe -m pip_audit -r requirements.lock --disable-pip --no-deps
```

The frontend is JavaScript, so there is no separate TypeScript type check. The
backend mypy check is the static type gate.

## Production build and start

Frontend static build:

```powershell
cd ChatbotUI
npm ci
npm run build
```

Serve `ChatbotUI/dist` behind HTTPS with the headers and SPA rewrites represented
in `ChatbotUI/vercel.json`.

Backend without Docker:

```powershell
cd fastapi_backend
.venv\Scripts\python.exe -m pip install -r requirements.lock
.venv\Scripts\python.exe -m alembic upgrade head
.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers
```

Backend container:

```powershell
docker build -t nnmc-edplan-api fastapi_backend
docker run --rm -p 8000:8000 --env-file fastapi_backend/.env nnmc-edplan-api
```

The image runs as a non-root user and exposes a liveness health check. Migrations
remain a separate release job so multiple replicas do not race at startup.

## Security and operations

- Public registration creates only student/customer accounts; administrative
  roles are never accepted from the client.
- Education-plan and advisor APIs require bearer authentication and enforce
  resource ownership on the server.
- Browser tokens use session storage. Do not add tokens to URLs or logs.
- Configure distributed rate limits at the load balancer/WAF before public launch.
- Email verification is intentionally reported as unavailable until a genuine
  token-delivery flow is implemented; do not represent accounts as verified.
- Configure centralized logs, error monitoring, uptime checks, alerts, database
  backups, and a tested restore procedure before launch.

See [PRODUCTION_READINESS_REPORT.md](PRODUCTION_READINESS_REPORT.md) and
[LAUNCH_CHECKLIST.md](LAUNCH_CHECKLIST.md) for the current evidence and blockers.
