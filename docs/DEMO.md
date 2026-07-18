# The Journey — Self-Contained Demo

## Overview

`demo.html` is a **completely self-contained, no-backend-required** version of The Journey web app. It runs entirely in the browser with an in-memory mock backend, making it easy to showcase the app without spinning up a server.

**URL:** https://claude.ai/code/artifact/52d89f1b-eb0b-4f55-a0c1-dbad77e9ad19

## What Changed

### Architecture

The demo is a single HTML file that combines:
- **All HTML, CSS, and JavaScript** inlined (no external files, no CDN requests)
- **In-memory mock backend** replacing the real FastAPI API layer
- **Seeded demo data** — 90 days of realistic weight entries with a goal

### Key Implementation Details

#### 1. In-Memory Backend

Replaced the `api()` network function with a local handler that simulates the FastAPI endpoints:

```javascript
function handle(method, path, body) {
  // Routes mimic /auth/*, /weights*, /goals*
  // Returns the same response shapes
  // Throws ApiError with real HTTP status codes (400, 404, 409, 422)
}

async function api(path, options = {}) {
  await new Promise((r) => setTimeout(r, 55)); // simulated latency
  const method = (options.method || "GET").toUpperCase();
  const body = options.body ? JSON.parse(options.body) : null;
  const result = handle(method, path, body);
  return result;
}
```

**Endpoints implemented:**
- `POST /auth/apple`, `POST /auth/google` — dev-mode login (any name works)
- `GET /auth/config` — returns `{mode: "dev"}`
- `GET /auth/me` — returns a dummy user
- `GET /weights` — returns all entries (descending)
- `GET /weights/stats` — computes stats (current, 7d avg, pace, weekly change)
- `POST /weights` — adds entry, validates (0 < weight ≤ 500), enforces date uniqueness (409)
- `PUT /weights/:id` — updates weight and note
- `DELETE /weights/:id` — deletes entry
- `PUT /goals` — sets goal with target weight and date
- `GET /goals/current` — returns goal progress (lost_kg, remaining_kg, percent_complete)

#### 2. Stats Calculations

Replicated the exact same math as the backend:

```javascript
function computeStats() {
  // Returns same fields as FastAPI WeightStats:
  // - moving_avg_7d_kg: mean of weights in past 7 days (inclusive)
  // - avg_weekly_change_kg: (latest - first) / days * 7
  // - total_change_kg: latest - first
  // - min/max weight, entry count, date range
}

function goalProgress() {
  // Returns GoalProgress: lost_kg, remaining_kg, percent_complete
  // percent_complete scaled to [0, 100] based on (lost / planned) * 100
}
```

#### 3. Seeded Demo Data

Uses a **seeded pseudorandom generator** (mulberry32) + Gaussian distribution to create realistic, reproducible data:

```javascript
function seedDb() {
  const rng = mulberry32(11); // fixed seed for consistency
  const trend = 97.8 - 4.9 * Math.pow(i / 90, 0.9); // realistic loss curve
  const noise = gauss(rng) * 0.42 + 0.3 * Math.sin(i / 3.1); // daily variation
  // Result: 90-day journey, ~97.8 kg → ~92.6 kg, with goal at 88 kg
}
```

**Data seeded:**
- **57 entries** across 90 days (~5 per week, realistic logging frequency)
- **Trend:** 97.8 kg → 92.6 kg (realistic slowing loss curve)
- **Goal:** 88 kg by Dec 31, 2026
- **Notes:** Randomly selected from ["", "post gym", "travel day", "late dinner", etc.]

#### 4. State Management

Data lives in memory (in a `db` object):
```javascript
const db = {
  entries: [...],  // array of WeightLog records
  goal: {...},     // current goal or null
  wid: 57,         // next weight ID
  goalId: 1,       // goal ID counter
};
```

**Persistence:** Theme and unit preference survive page reload via `localStorage`, but weight data resets on refresh (always returns to the seeded demo state).

#### 5. UI Enhancements

Added a **"Demo" chip** to the topbar to distinguish the sandbox from the real app:

```html
<span class="demo-chip" title="Self-contained demo. Data lives in this page only.">Demo</span>
```

Styled as a small emerald badge next to the app title.

### What's the Same

- **Every line of HTML, CSS, and JavaScript** from the production web client
- **All interactive features:** log/edit/delete weights, set/change goal, chart ranges (30D/90D/1Y/All), theme toggle, kg↔lb conversion
- **All validations:** 0 < weight ≤ 500, no future dates, duplicate-date guard (409), goal requires ≥1 logged weight (400)
- **All calculations:** 7-day moving average, weekly pace with ETA, goal progress bar
- **Responsive design:** mobile single-column, tablet 2fr/1fr split, desktop full width
- **Both themes:** light and dark, with both CSS variables properly overridden

### What's Different

| Aspect | Production | Demo |
|--------|-----------|------|
| **Backend** | Real FastAPI server | In-memory mock |
| **Auth** | Dev mode or real OAuth (Apple/Google) | Dev mode only (any name works) |
| **Data** | Persisted in database | In-memory, resets on reload |
| **Latency** | Network + server | 55ms simulated (for visual consistency) |
| **Seeded data** | None (start fresh) | 90-day realistic journey pre-loaded |

## Use Cases

1. **Instant Showcase** — Share the link; no setup needed. Works offline (except the page load itself).
2. **Feature Preview** — Test UI changes without touching the backend or database.
3. **Onboarding** — Let new users explore the app in a sandbox before signing up.
4. **Testing** — Reproduce UI behaviors (validation toasts, chart range switches, goal animations) without an API server.

## Limitations

- **No real authentication.** Dev mode only; any string works as an account name.
- **No data persistence.** Reload the page → back to the seeded demo.
- **No user isolation.** All demo users see the same data (it's a single in-memory store).
- **No backend features.** Alembic migrations, Prometheus metrics, production auth (Step 10), Postgres—all backend-only—don't apply.

## How It Works at Runtime

1. **Boot:** Page applies saved theme from localStorage, calls `api("/auth/config")`.
2. **Auto-login:** If token exists in localStorage, calls `api("/auth/me")` to verify and enter the app.
3. **Load:** `loadData()` calls `api("/weights")`, `api("/weights/stats")`, `api("/goals/current")` in parallel.
4. **Render:** Same `renderAll()` as production — stats, entries, goal, chart, all from the in-memory state.
5. **Interact:** User adds/edits/deletes weights or goal; mutations call mock `api()`, which updates `db`, then refresh reloads the UI.

## Deployment

The demo is **not** committed to the git repo (it's 50KB, and the production web client is the canonical source). It's published as a Claude Artifact at the URL above.

To self-host it:
1. Copy the `.html` file to a web server.
2. Serve it as-is—no build step, no dependencies, no CORS needed.
3. Open in any modern browser (ES6+, `<dialog>`, CSS variables, `ResizeObserver` required).

## Future Enhancements

- Add a "Download as CSV" button to export the demo data.
- Add a "Reset" button to re-seed the demo data.
- Extend to test production auth paths (Apple/Google JWKS verification mock).
- Add a "Preview Mode" toggle in the real app that uses this same in-memory backend for testing.
