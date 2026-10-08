# CyberGurukul Backend — Core API

Enterprise backend for the CyberGurukul Workshop & Digital Certificate Management Platform.

## Tech stack
- **FastAPI** + Python 3.12 (async)
- **PostgreSQL** via async SQLAlchemy 2.0 + asyncpg
- **JWT** auth (access + refresh), **bcrypt** password hashing
- **Pydantic v2** schemas, **Alembic** for migrations

## Quick start (local)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then edit DATABASE_URL + JWT_SECRET_KEY
# create tables (dev only; use Alembic in production):
python -c "import asyncio; from app.database import init_db; asyncio.run(init_db())"
uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs

## API surface (all under /api/v1)

| Method | Route | Auth | Description |
|---|---|---|---|
| POST | /auth/signup | public | Create student account |
| POST | /auth/login | public | Get access + refresh tokens |
| POST | /auth/refresh | public | Refresh tokens |
| GET | /auth/me | user | Current user |
| GET | /workshops | public | List workshops |
| GET | /workshops/{slug} | public | Workshop detail |
| POST | /workshops | staff+ | Create workshop |
| PUT | /workshops/{slug} | staff+ | Update workshop |
| DELETE | /workshops/{slug} | staff+ | Delete workshop |
| POST | /registrations/{slug} | user | Register for workshop |
| GET | /registrations/me | user | My registrations |
| GET | /registrations | staff+ | All registrations |
| POST | /certificates/issue | staff+ | Issue certificate |
| GET | /certificates/verify/{cert_id} | public | Verify certificate |
| POST | /certificates/{id}/revoke | staff+ | Revoke certificate |
| POST | /certificates/{id}/restore | staff+ | Restore certificate |
| GET | /certificates/me | user | My certificates |
| GET | /health | public | Health check |

## Roles
`student < instructor < certificate_manager < workshop_manager < admin < super_admin`
Higher roles inherit lower-role permissions; `super_admin` bypasses all guards.

## Notes
- `.env` is required (see `.env.example`); never commit real secrets.
- Phase 2 (not built yet): MFA/2FA, Redis, email service, attendance QR, assessments, analytics.
