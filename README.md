# QR Attendance Management System

A production-oriented HR attendance system built around QR-code check-ins. HR
displays one QR code at the entrance (printable, doesn't change); employees
scan it with their own phone to check in or out. The scan happens through
their own authenticated session — no separate device, no separate identifier,
no biometric hardware. On-time/late status is calculated against configurable
working hours, the HR dashboard updates in real time over WebSocket, and HR
can request an explanation letter from an employee for any specific late
arrival, which the employee can respond to with text and/or an uploaded file.

---

## 1. Overview

- **Backend:** FastAPI + PostgreSQL + SQLAlchemy (async) + Alembic
- **Frontend:** React + TypeScript + Vite + Tailwind CSS
- **Real-time:** native WebSockets, no polling
- **PDF:** ReportLab, generated on demand and cached
- **Auth:** JWT (short-lived access token + rotating refresh token), two roles (HR, Employee)

The core scenario from the specification — Mohira Sobirjonova checks in at
08:57:31 (on time), Hasan Karimov checks in at 09:38:21 (38 minutes late,
triggering an auto-generated explanation letter) — is reproduced exactly by the
seed data and by the automated test suite (`tests/test_attendance.py`).

## 2. Architecture

```
project/
├── backend/            FastAPI application (see backend/app/ for the full layout)
├── frontend/            React application
├── docker-compose.yml   Postgres + backend + frontend, one command
└── .env.example          Copy to .env before running anything
```

**Backend layering:** `api/routes` (thin HTTP layer) → `services` (all business
rules) → `models` (SQLAlchemy ORM). `app/services/attendance_service.py` is the
core: `process_scan` resolves check-in vs. check-out direction from whether the
employee already has an open record, applies the duplicate-scan window,
calculates lateness, and broadcasts over WebSocket - called by the single
`POST /api/attendance/scan` endpoint, authenticated as the scanning employee's
own account.

**Why Alembic instead of a `database/init.sql`:** the original brief's folder
sketch listed a separate `database/` directory with an init script. Since
Alembic is already the schema-of-record (as the spec's own technology list
requires), a parallel raw SQL script would be a second, competing source of
truth for the schema. Alembic migrations are applied automatically on every
backend startup (`alembic upgrade head`), which serves the same purpose more
safely.

**Known limitation — WebSocket broadcast is single-worker only.** The connection
manager (`app/websocket/manager.py`) keeps live connections in an in-process
Python list. This is correct and sufficient for the default single-worker
deployment (`uvicorn app.main:app`, no `--workers`). Running multiple workers or
horizontally scaling the backend would require moving the broadcast to a shared
layer (e.g. Redis pub/sub) — not implemented here, since it's out of scope for
a single-instance deployment.

## 3. Technologies

| Layer | Choice |
|---|---|
| Backend framework | FastAPI (async) |
| Database | PostgreSQL (SQLite for the automated test suite only) |
| ORM / migrations | SQLAlchemy 2.0 (async) + Alembic |
| Auth | PyJWT, bcrypt |
| Real-time | Native FastAPI WebSockets |
| PDF | ReportLab |
| Export | openpyxl (Excel), stdlib `csv` |
| Scheduling | APScheduler |
| Frontend | React 18 + TypeScript + Vite |
| Styling | Tailwind CSS |
| Server state | TanStack Query |
| Charts | Recharts |

## 4. Installation

Requires Docker and Docker Compose (recommended), or Python 3.12+ and Node 20+
for running the two halves directly.

### Option A — Docker Compose (recommended)

```bash
cp .env.example .env
# Edit .env: set a real value for JWT_SECRET at minimum (16+ characters;
# the placeholder in .env.example is valid but not something you should
# actually deploy with).

docker compose up --build
```

This starts PostgreSQL, runs migrations, seeds demo data on first boot, and
serves the frontend at **http://localhost:5173** (proxying `/api` and `/ws` to
the backend) and the backend directly at **http://localhost:8000**.

### Option B — Run backend and frontend directly

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt   # includes runtime deps + test deps
cp ../.env.example ../.env             # then edit DATABASE_URL to point at your Postgres,
                                        # or use SQLite for a quick local run (see below)
alembic upgrade head
python -m scripts.seed
uvicorn app.main:app --reload

# Frontend, in a second terminal
cd frontend
npm install
npm run dev
```

For a quick local run without PostgreSQL, set in `.env`:
```
DATABASE_URL=sqlite+aiosqlite:///./dev.db
```

## 5. Environment Variables

See `.env.example` at the project root for the full, commented list. The ones
you must change before any real deployment:

| Variable | Purpose |
|---|---|
| `JWT_SECRET` | Signs all access/refresh tokens. Min 16 chars; use 32+ in production. |
| `COMPANY_TIMEZONE` | IANA timezone (e.g. `Asia/Tashkent`) — working hours are defined in this timezone. |

## 6. Database Setup & Migration

Schema is entirely managed by Alembic. The single migration
(`backend/alembic/versions/0001_initial_schema.py`) creates all eleven tables.

```bash
cd backend
alembic upgrade head        # apply migrations
alembic revision --autogenerate -m "description"   # after changing models
alembic downgrade -1         # roll back one revision
```

## 7. Seed / Demo Data

```bash
cd backend
python -m scripts.seed            # refuses to run if data already exists
python -m scripts.seed --reset    # wipes all tables first, then reseeds
```

Creates 6 departments, 22 employees (one inactive, one on approved leave, one
with a personal working-hours override), a login for every employee, 30 days of
realistic attendance history, and a mix of states for today. **EMP001**
(Mohira Sobirjonova), **EMP002** (Hasan Karimov), EMP003, and EMP011 are left
without a record for "today" specifically so you can run the section 22 demo
scenario live (see §10).

## 8. Running the Pieces Individually

**Backend:** `uvicorn app.main:app --reload` (add `--host 0.0.0.0` to expose
beyond localhost). API docs at `/api/docs` (Swagger) and `/api/redoc`.

**WebSocket:** no separate process — it's mounted on the same FastAPI app at
`/ws`, authenticated with the same access token as REST calls, passed as a
query parameter (`?token=...`) since browsers can't set custom headers on the
WebSocket handshake.

**Scheduler:** starts automatically with the backend (APScheduler, in-process).
Runs the missing-checkout sweep every 30 minutes and once immediately at
startup. Trigger it manually: `POST /api/scheduler/run-missing-checkout-check`
(HR-authenticated).

**Frontend:** `npm run dev` (Vite dev server, proxies `/api` and `/ws` to
`localhost:8000` — see `frontend/vite.config.ts`).

## 9. The QR Code and How Scanning Works

HR opens **QR Code** in the sidebar, which shows one code encoding
`{your-frontend-url}/scan`. Print it or display it on a screen at the
entrance — it doesn't change, so it's a one-time setup, not something
regenerated per employee or per day.

An employee scans it with their own phone's camera, which opens `/scan` in
their browser. If they're not already logged in, they're sent to the login
page and returned to `/scan` automatically afterward (standard redirect-back
behavior - see `RequireAuth` in `frontend/src/components/RouteGuards.tsx`).
Once authenticated, the page immediately calls `POST /api/attendance/scan`
with no body at all - the backend already knows who's calling from their own
access token, so there's no identifier to pass, spoof, or mismatch. The
backend decides check-in vs. check-out itself, based on whether that employee
already has an open record for today.

There's no hardware, no device API key, and no separate recognition or
resolution service to configure - the "device" is just the employee's own
already-authenticated session.

## 10. Running the Section 22 Demo Scenario

With the seed data loaded (EMP001/EMP002 have no record for today):

1. Log in as HR (`hr@company.com` / see §11) in one browser tab.
2. In a second tab (or an incognito window), log in as `mohira.sobirjonova@company.com`
   (EMP001) and visit `/scan` directly - or scan the actual QR code from the
   **QR Code** page with a phone on the same network as the dev server.
3. She appears immediately in the green "On Time" section of HR's Attendance
   page and the Dashboard card counts update, live, with no page refresh.
4. Log in as `hasan.karimov@company.com` (EMP002) and visit `/scan` at a time
   more than 15 minutes past 09:00 (or adjust the system clock / working hours
   in Settings to reproduce this on demand) - he appears in the red "Late"
   section.
5. Back in the HR tab, on the Attendance page, click **Request Explanation**
   on his late row - he's notified, and can respond from his own Explanation
   Letters page with text and/or an uploaded file.

This exact flow — including the live WebSocket update — is also covered by
`backend/tests/test_attendance.py` and `backend/tests/test_websocket.py`.

## 11. Test Accounts

All seeded accounts share the password set by `SEED_PASSWORD` (default
`Password123!`).

| Role | Email | Notes |
|---|---|---|
| HR / Administrator | `hr@company.com` | Not linked to an employee record |
| HR (also an employee) | `dilnoza.rashidova@company.com` | Has both HR access and an employee dashboard |
| Employee | `mohira.sobirjonova@company.com` | EMP001 — the on-time example |
| Employee | `hasan.karimov@company.com` | EMP002 — the late example |
| Employee (deactivated) | — | EMP021, login disabled — demonstrates the deactivated-employee edge case |

## 12. API Documentation

Interactive Swagger UI: **`/api/docs`**. ReDoc: **`/api/redoc`**. Both are live
against your running backend and reflect every route, request/response schema,
and status code exactly.

## 13. Downloading Explanation Letter PDFs

`GET /api/explanation-letters/{id}/pdf` (HR, or the employee it belongs to).
PDFs are generated on first download and cached (`pdf_path` on the
`explanation_letters` row); submitting an explanation or an HR review
invalidates the cache so the next download reflects the new content. From the
UI: Explanation Letters page → "PDF" next to any letter.

## 14. Testing

```bash
cd backend
pip install -r requirements-dev.txt
pytest                    # 105 tests: auth, employees, departments, leave
                           # management, explanation letters (including file
                           # uploads), the full attendance/scan engine
                           # (check-in/out, late calculation, duplicate
                           # prevention, overnight shifts, WebSocket events,
                           # role authorization), plus regression tests
                           # locking in bugs found (and fixed) during
                           # development.
pytest -v                 # verbose, one line per test
```

```bash
cd frontend
npm run build              # TypeScript check + production build
npm run lint                # ESLint
```

## 15. Known Gaps

Being direct about what isn't (fully) built, rather than leaving it implicit:

- **Frontend bundle is not code-split** (single chunk, ~900KB / ~260KB gzipped).
  Functions correctly; not optimized for a slow-network first load.
- **No browser-automation testing was performed** on the frontend during
  development — verified via a clean strict-TypeScript build, a clean ESLint
  pass, and live integration checks of the dev proxy and WebSocket connection,
  but not interactive click-through testing in an actual browser.
- **Multi-worker / horizontal scaling** would need a shared WebSocket broadcast
  layer (see §2) — not implemented, as it's outside a single-instance deployment.
