# The Journey — API Reference (v0.2)

All endpoints except `/`, `/healthz`, and `/auth/apple|google` require
`Authorization: Bearer <app JWT>`.

## Health

| Method | Path | Description |
|---|---|---|
| GET | `/` | Liveness message |
| GET | `/healthz` | Liveness + database connectivity check |

## Auth (DEV MODE)

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/auth/apple` | `{"id_token": "<any string>"}` | `{access_token, token_type}` |
| POST | `/auth/google` | same | same |
| GET | `/auth/me` | — | Current user profile |

DEV MODE treats the `id_token` string as the identity. The same string on the
same provider always maps to the same user; the same string on a different
provider is a different user. Set `DEV_AUTH_ENABLED=false` to turn these off
(Step 10 replaces them with real Apple/Google token verification).

## Weights

| Method | Path | Notes |
|---|---|---|
| POST | `/weights` | Body: `{date, weight_kg, source?, note?}`. One entry per day — a second POST for the same date returns **409** (use PUT to change it). Weight must be 0–500 kg; date can't be in the future. |
| GET | `/weights` | Query: `start_date`, `end_date`, `limit` (default 100), `offset`. Sorted newest first. |
| GET | `/weights/latest` | 404 if nothing logged yet |
| GET | `/weights/stats` | See below |
| PUT | `/weights/{id}` | Body: `{weight_kg?, note?}` — partial update |
| DELETE | `/weights/{id}` | 204 on success |

Accessing another user's entry by id returns **404** (never 403 — ids are not
revealed as existing).

### `GET /weights/stats`

```json
{
  "count": 5,
  "first_date": "2026-06-01",
  "latest_date": "2026-07-13",
  "start_weight_kg": 96.0,
  "latest_weight_kg": 93.0,
  "min_weight_kg": 93.0,
  "max_weight_kg": 96.0,
  "total_change_kg": -3.0,
  "moving_avg_7d_kg": 93.25,
  "avg_weekly_change_kg": -0.5
}
```

- `moving_avg_7d_kg`: average of entries within 7 days of the latest entry.
- `avg_weekly_change_kg`: total change normalized to kg/week (null with <2 days of span).

## Goals

| Method | Path | Notes |
|---|---|---|
| PUT | `/goals` | Body: `{target_weight_kg, target_date?}`. Sets the active goal, replacing any previous one. Starting weight is snapshotted from the latest log; 400 if no weights logged yet. |
| GET | `/goals/current` | Goal + progress: `current_weight_kg`, `lost_kg`, `remaining_kg`, `percent_complete` (0–100). 404 if no active goal. |
