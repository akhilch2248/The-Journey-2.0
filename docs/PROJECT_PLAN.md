# Project Plan — Idol Physique Training App
*(working name: pick one later — "Ascend", "Icon", "Reforge" all fit; placeholder = **Forge**)*

Extends the **TheJourney** backend. v1 scope: **training programming only** — no nutrition
tracking, no AI chat coach. Those are explicitly Phase-4/5, not now.

---

## 1. The one-liner

BWS gives you an algorithm-personalized program. MacroFactor gives you an algorithm that
learns your metabolism. Forge gives you a program that's personalized against a *visual
target you choose* — a photo of an idol, character, or physique — instead of a generic
"goal: build muscle" dropdown. You upload the reference, log your current stats, and the
app generates a plan aimed at closing that specific gap.

This is close to what you've already been doing manually for your own 24-week plan
(Vidyut Jammwal as the physique reference) — this project productizes that process so it
works for any user with any reference image.

## 2. Core user flow (v1)

1. **Onboarding** — height, weight (pulls from existing `WeightLog`), age, training
   experience, available equipment, days/week available, any movement constraints
   (you'll want your own spine-conscious flags representable here).
2. **Goal capture** — upload one reference image (idol/character/superhero). Optionally
   upload a current physique photo of themselves.
3. **Gap assessment** — the system compares "reference physique" to "current physique /
   current stats" and produces a structured gap report: which regions to prioritize
   (e.g., "reference shows broader delts/lat V-taper → emphasize shoulder width + back
   width"), not just "gain muscle."
4. **Plan generation** — a split + exercise selection + progression scheme is generated
   from the gap report, constrained by equipment/days/injury flags.
5. **Logging & progression** — per-set logging (weight, reps, RIR), the app auto-regulates
   next-session targets (this is the BWS/MacroFactor-Workouts core loop — progressive
   overload guidance based on actual logged performance, not a fixed spreadsheet).
6. **Re-assessment** — periodically (e.g., every 4–6 weeks) prompt a new physique photo,
   re-run the gap comparison, adjust emphasis.

## 3. The hard design problem: image → gap assessment

This is the one genuinely novel piece, so it deserves its own decision before any code.
Two viable approaches, not mutually exclusive:

**Option A — AI vision assessment (higher fidelity, more moving parts).**
Send both images to a vision-capable model with a structured prompt asking for
*relative, qualitative* proportions (shoulder-to-waist ratio, apparent muscularity by
region, estimated build type) — never precise body-fat % or medical-style claims, since
that's unreliable from a photo and easy to get wrong in a way that's discouraging. Output
a fixed schema (JSON) the plan-generator consumes.

**Option B — Structured self-report (lower fidelity, ships faster).**
Skip vision entirely for v1: user tags the reference with a short structured form
("broad shoulders", "V-taper back", "lean midsection", "arm size") from a fixed
checklist, and separately self-reports their own current emphasis/weak points. Same
downstream schema, zero AI dependency, zero risk of a bad auto-assessment discouraging
someone on day one.

**Recommendation: build B first, wire in A as a Phase 2 enhancement behind the same
schema.** The plan-generation logic only needs the structured gap report — it shouldn't
care whether a human filled it in or a model did. That keeps v1 shippable without
depending on vision-model reliability/cost, and upgrading later is additive, not a
rewrite.

One framing note worth building in from the start regardless of A or B: keep the language
comparative and constructive ("prioritize" / "emphasize"), not evaluative of the user's
current body. This is a design choice, not a compliance footnote — it's what keeps a
photo-comparison feature motivating instead of something that just tells someone what's
wrong with them.

## 4. Data model additions

Everything below is additive to the existing `users` / `weights` tables — no changes to
what's already built.

```
PhysiqueGoal
  id, user_id (FK → users)
  reference_image_url
  reference_label            # e.g. "Vidyut Jammwal", "Goku", "Batman" — user's own text
  gap_report (JSON)           # structured output from Option A or B, same schema either way
  created_at, superseded_at   # keep history as re-assessments happen

ProgressPhoto
  id, user_id, image_url, taken_at, note

Exercise
  id, name, primary_muscle, equipment, movement_pattern,
  contraindications (JSON)    # e.g. tags like "axial_load", "loaded_flexion" —
                               # lets the generator respect constraints like yours

WorkoutProgram
  id, user_id, goal_id (FK → PhysiqueGoal), name,
  split_type, days_per_week, status (active/completed/archived), created_at

ProgramDay
  id, program_id, day_label, order_index

ProgramExercise
  id, program_day_id, exercise_id, target_sets, target_rep_range, order_index

WorkoutSession
  id, user_id, program_day_id, performed_at, status

SetLog
  id, session_id, program_exercise_id, set_number,
  weight_kg, reps, rir, is_amrap
```

`SetLog` is the row that lets progression be computed rather than guessed — same idea as
MacroFactor Workouts' "smart progression": compare logged performance against the
target, widen/tighten the next target automatically.

## 5. API surface (v1)

```
POST   /goals                    upload reference image + label → creates PhysiqueGoal
POST   /goals/{id}/assessment     submit structured gap report (Option B form)
GET    /goals/active

POST   /programs/generate         from active goal + equipment/days/constraints → WorkoutProgram
GET    /programs/active
GET    /programs/{id}

POST   /sessions                  start a session for a given program day
POST   /sessions/{id}/sets        log a set
POST   /sessions/{id}/complete    triggers next-session target recalculation

GET    /progress-photos
POST   /progress-photos
```

All routes sit behind the existing `get_current_user` Bearer-token dependency — no new
auth work needed.

## 6. Progression logic (the actual "intelligence")

Keep this rule-based for v1, not ML — it's what BWS and MacroFactor Workouts both
actually run underneath the marketing:

- Hit top of rep range for all sets at target RIR → increase load next session (defer to
  a standard %/absolute increment by exercise category — compound vs isolation).
- Miss bottom of rep range → hold load, repeat.
- Consistently miss for 2+ sessions → deload or widen rep range (this is the "smart
  progression" behavior MacroFactor Workouts recently added — reasonable to copy the
  shape of it).

This lives entirely in `SetLog` → `ProgramExercise.target_*` comparison logic — no
external dependency, testable in isolation, cheap to ship.

## 7. What's explicitly OUT of v1

- Nutrition/macro tracking, food logging, expenditure algorithm (Phase 4 — this is where
  MacroFactor's core actually lives; big enough to be its own project phase)
- AI chat coach (Phase 5)
- Vision-based auto-assessment (Phase 2 — v1 ships with the structured self-report form)
- Social/sharing features
- Wearables integration

## 8. Phased roadmap

| Phase | Scope |
|---|---|
| **1 (this)** | Data models above, structured self-report gap assessment, rule-based plan generator, set logging, rule-based progression |
| **2** | Swap/augment gap assessment with real vision-model analysis behind the same schema |
| **3** | iOS app (per TheJourney's existing Step 9 plan) surfacing all of this |
| **4** | Nutrition module — expenditure estimate from logged weight trend + food log (MacroFactor's actual core mechanic) |
| **5** | AI coach chat layer over both training + nutrition data |

## 9. Open questions before Phase 1 coding starts

- Exercise library: build a seed list (~50–80 exercises tagged by muscle/equipment/
  contraindication) or start smaller and grow it as programs are generated?
- Split library: start with just your ULPLP + Athlete Day template as the one built-in
  split, generalized with parameters, or build a small library of 3–4 split types
  (full-body, upper/lower, PPL) from day one?
- Image storage: local disk for dev (matches current setup) vs. S3/equivalent — worth
  deciding early since `PhysiqueGoal` and `ProgressPhoto` both depend on it.
