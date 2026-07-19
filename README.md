# The Journey

Weight tracking, full stack: FastAPI backend, a web app it serves itself, and a
SwiftUI iOS client — now evolving into **Forge**, an idol-physique training app.

```
TheJourney/
├── backend/
│   ├── app/            FastAPI API: auth, weights, goals, stats, /metrics
│   │   └── static/     The web app (vanilla JS SPA, served at /app)
│   ├── alembic/        Database migrations
│   ├── tests/          51 pytest tests (run on in-memory SQLite)
│   └── Dockerfile
├── infra/              docker-compose (Postgres + API), backups, DB inspection
├── docs/               API reference, runbook, and the Forge project plan
└── ios-app/            SwiftUI client (Xcode project)
```

## Where this is going: Forge

The vision has expanded from weight tracking to **training programming against a
visual target**: upload a reference physique (an idol, a character), log your
current stats, and the app generates a personalized program aimed at closing that
specific gap — then auto-regulates it from your logged sets.

Full plan: [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md). The short version:

| Phase | Scope |
|---|---|
| **1 (next)** | Workout data models (programs, sessions, set logs, exercise library), structured self-report gap assessment, rule-based plan generator + progression |
| **2** | Vision-model gap assessment behind the same schema |
| **3** | iOS surfaces the training features |
| **4** | Nutrition module (expenditure from weight trend + food log) |
| **5** | AI coach layer over training + nutrition data |

Everything below — the weight tracking core, auth, and infra — is built, tested,
and stays as the foundation Phase 1 extends.

## Quick start (no Docker needed)

```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open **http://127.0.0.1:8000** — the web app loads (SQLite file database, zero
setup). Swagger stays at `/docs`, health at `/healthz`, Prometheus at `/metrics`.

Sign in with any account name (dev mode), log weights, set a goal. The dashboard
shows current/change/7-day-average/pace tiles, a trend chart with a 7-day
average line and crosshair tooltip, kg/lb toggle, light/dark theme, and full
entry editing with undo.

## Tests

```bash
cd backend && ./venv/bin/python -m pytest
```

Covers auth (dev + production token verification), user isolation, weights CRUD
and validation, stats math, goals, health, and metrics.

## Production auth (Step 10)

Set in `backend/.env`:

```
AUTH_MODE=production
APPLE_AUDIENCE=<your iOS bundle id>
GOOGLE_AUDIENCE=<your Google OAuth client id>
```

`/auth/apple` and `/auth/google` then verify real id_tokens against the
providers' JWKS (signature, audience, issuer, expiry). Tests cover this path
with locally-generated RSA keys.

## Postgres + Docker (Steps 11-12)

```bash
cd infra
docker compose up -d --build   # Postgres + API; migrations run on boot
./check-db.sh                  # inspect tables and ownership
./backup-db.sh                 # timestamped pg_dump, keeps newest 14
```

Migrations: `alembic upgrade head` / `alembic revision --autogenerate -m "..."`.
CI (GitHub Actions) runs the test suite and applies migrations against a real
Postgres on every push. Operations guide: [docs/RUNBOOK.md](docs/RUNBOOK.md).

## iOS app (Step 9)

The Xcode project lives at `~/Desktop/The Journey App/The Journey`. It contains
the complete SwiftUI client: keychain-stored session, dev-mode login, dashboard
with Swift Charts trend (weight + 7-day average + goal line), stat tiles, entry
list with swipe to edit/delete, add/edit/goal sheets, kg/lb setting, and a
configurable server URL (use your Mac's LAN address on a physical device).
Open the project in Xcode and run; the backend must be running.

## API

Full endpoint reference: [docs/API.md](docs/API.md)
