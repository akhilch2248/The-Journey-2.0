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

## Training (Forge Phase 1)

All routes require the same Bearer auth; every resource is scoped to its owner
(404 for anything that isn't yours). Coaching knowledge (exercise library,
split templates, progression rules) lives in `backend/app/domain/*.json`.

### Physique goals

| Method | Path | Notes |
|---|---|---|
| POST | `/physique-goals` | Multipart: `reference_label` + optional `reference_image`. Supersedes (never deletes) the previous goal. Images are re-encoded — EXIF/GPS stripped — and served only through the authenticated image endpoint. |
| GET | `/physique-goals/active` | 404 if none. |
| POST | `/physique-goals/{id}/assessment` | Body: `{emphasis: {region: 0-3}, notes?}`. Regions: shoulder_width, back_width, back_thickness, chest, arms, midsection, quads, glutes_hams, calves, conditioning. At least one must be >0. |
| GET | `/physique-goals/{id}/image` | The reference image (JPEG). |

### Programs

| Method | Path | Notes |
|---|---|---|
| POST | `/programs/generate` | Body: `{days_per_week: 2-6, equipment: [...], spine_conscious: true}`. Builds from the active goal's gap report (400 without goal/assessment). Archives the previous active program. Spine-conscious filters every exercise tagged `axial_load`, `loaded_spinal_flexion`, `unsupported_hinge`, or `loaded_rotation`. Emphasis ≥2 adds a set; 3 adds an extra isolation movement. |
| GET | `/programs/active` | Full program: days → exercises with targets. |
| GET | `/programs/{id}` | Any of your programs (incl. archived). |

### Sessions & progression

| Method | Path | Notes |
|---|---|---|
| POST | `/sessions` | Body: `{program_day_id}`. 409 if another session is in progress. Response includes stale-exercise suggestions (14+ days → resume ~10% lighter). |
| POST | `/sessions/{id}/sets` | Body: `{program_exercise_id, set_number, weight_kg?, reps, rir?, is_amrap?}`. 400 if the exercise isn't part of the session's day. |
| POST | `/sessions/{id}/complete` | Runs the progression engine per logged exercise. Decisions: `baseline` (first session sets the working weight), `increase` (all sets at rep-range top → +increment, e.g. +2.5 kg barbell compound), `add_rep` (in range → chase reps), `hold` (below range once), `deload` (twice → −10%). |
| GET | `/sessions` | Latest 20. |
| GET | `/sessions/{id}` | One session with its sets. |

### Progress photos

| Method | Path | Notes |
|---|---|---|
| GET | `/progress-photos` | Newest first. |
| POST | `/progress-photos` | Multipart: `image` + optional `taken_at`, `note`. Same EXIF-stripping pipeline. |
| GET | `/progress-photos/{id}/image` | The photo (JPEG). |
| DELETE | `/progress-photos/{id}` | Removes the row **and** the file. |

### Exercise library

| Method | Path | Notes |
|---|---|---|
| GET | `/exercises` | Optional `?muscle=` / `?equipment=`. Each entry carries movement pattern, category, contraindication tags, and a coaching cue. |
