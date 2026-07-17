# The Journey — Runbook

## Service overview

| Component | What | Where |
|---|---|---|
| API | FastAPI + Uvicorn | `backend/`, port 8000 |
| Web app | Static SPA served by the API | `/app/` on the same port |
| Database | Postgres 14 (Docker) or SQLite (dev default) | `infra/docker-compose.yml` |

## Health & observability

- `GET /healthz` — liveness + DB connectivity. Returns `{"status":"ok","database":"ok"}`.
- `GET /metrics` — Prometheus format: `http_requests_total{method,path,status}` and `http_request_duration_seconds` histograms, labeled by route template.
- Access logs: one JSON line per request (`event`, `method`, `path`, `status`, `duration_ms`) on stdout.

## Common operations

### Start / stop (full Docker stack)
```bash
cd infra
docker compose up -d --build   # api + db; api runs migrations on boot
docker compose down            # stop (keep data)
docker compose down -v         # stop AND WIPE DATA — dev only
```

### Run migrations manually
```bash
cd backend
alembic upgrade head           # apply
alembic revision --autogenerate -m "describe change"   # create after model edits
alembic downgrade -1           # roll back one revision
```
Never edit an applied migration; create a new one.

### Backups
```bash
cd infra
./backup-db.sh                       # writes backups/journey_<ts>.sql.gz, keeps newest 14
./restore-db.sh backups/journey_<ts>.sql.gz
```
Restore drill: run a backup, `docker compose down -v && docker compose up -d`,
restore, then `./check-db.sh` to confirm rows are back.

## Incident quick-reference

| Symptom | First checks |
|---|---|
| 500s on all endpoints | `GET /healthz` — if `database` fails: is the db container up? `docker ps`, `docker logs thejourney-db` |
| 401s for all users | Was `APP_SECRET` rotated? Every rotation invalidates all issued tokens — users must sign in again. |
| 401s in production auth | Check `AUTH_MODE`, `APPLE_AUDIENCE`/`GOOGLE_AUDIENCE` match the client app's bundle/client id. |
| Slow requests | `GET /metrics` → `http_request_duration_seconds` per route; check db container CPU. |
| Migration failed on deploy | `docker logs thejourney-api`; fix forward with a new revision, restore from backup if data was damaged. |

## Secrets

- `APP_SECRET` signs all session JWTs. Long random string, per environment, never committed.
- Rotation invalidates every active session (acceptable for now; refresh tokens are a future step).
