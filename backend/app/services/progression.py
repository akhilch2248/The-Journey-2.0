"""The progression engine — double progression, exactly as a coach runs it.

Reps move first, load second: hit the top of the rep range on every set and the
load goes up (and reps reset to the bottom); land mid-range and you chase reps
at the same load; fall below the bottom and the load holds — twice in a row and
it deloads 10%. Pure functions over plain values so every rule is unit-testable
without a database.
"""

from ..domain import load_progression


def _round_load(kg: float) -> float:
    """Nearest 0.25 kg — the smallest change plates/stacks can express."""
    return round(round(kg * 4) / 4, 2)


def increment_for(equipment: str, category: str, rules: dict | None = None) -> float:
    rules = rules or load_progression()
    table = rules["increments_kg"]
    return table.get(equipment, table["machine"]).get(category, 2.5)


def next_targets(
    *,
    target_weight_kg: float | None,
    rep_low: int,
    rep_high: int,
    consecutive_misses: int,
    equipment: str,
    category: str,
    sets: list[dict],
    rules: dict | None = None,
) -> dict:
    """Decide next session's target from this session's logged sets.

    sets: [{"weight_kg": float|None, "reps": int, "is_amrap": bool}, ...]
    Returns {"decision", "next_weight_kg", "consecutive_misses", "message"}.
    """
    rules = rules or load_progression()
    if not sets:
        return {
            "decision": "hold",
            "next_weight_kg": target_weight_kg,
            "consecutive_misses": consecutive_misses,
            "message": "No sets logged — targets unchanged.",
        }

    top_weight = max((s.get("weight_kg") or 0.0) for s in sets)

    # First session ever for this slot: whatever was lifted becomes the baseline.
    if target_weight_kg is None:
        baseline = _round_load(top_weight) if top_weight > 0 else None
        label = f"{baseline} kg" if baseline is not None else "bodyweight"
        return {
            "decision": "baseline",
            "next_weight_kg": baseline,
            "consecutive_misses": 0,
            "message": f"Baseline set at {label} — progression starts next session.",
        }

    all_at_top = all(s["reps"] >= rep_high for s in sets)
    amrap_blowout = any(
        s.get("is_amrap") and s["reps"] >= rep_high + rules["amrap_jump_margin"] for s in sets
    )
    any_below_bottom = any(s["reps"] < rep_low for s in sets)

    if all_at_top or amrap_blowout:
        inc = increment_for(equipment, category, rules)
        if inc <= 0:  # bodyweight/band: nothing to add — keep chasing reps
            return {
                "decision": "add_rep",
                "next_weight_kg": target_weight_kg,
                "consecutive_misses": 0,
                "message": f"Top of the range everywhere — add reps beyond {rep_high} or add external load.",
            }
        new = _round_load(target_weight_kg + inc)
        return {
            "decision": "increase",
            "next_weight_kg": new,
            "consecutive_misses": 0,
            "message": f"All sets at {rep_high}+ — load moves up to {new} kg, reps reset to {rep_low}.",
        }

    if any_below_bottom:
        misses = consecutive_misses + 1
        if misses >= rules["deload_after_misses"]:
            new = _round_load(target_weight_kg * rules["deload_factor"])
            return {
                "decision": "deload",
                "next_weight_kg": new,
                "consecutive_misses": 0,
                "message": f"Two sessions under {rep_low} reps — deload to {new} kg and rebuild.",
            }
        return {
            "decision": "hold",
            "next_weight_kg": target_weight_kg,
            "consecutive_misses": misses,
            "message": f"Fell under {rep_low} reps — repeat this load; one more miss triggers a deload.",
        }

    return {
        "decision": "add_rep",
        "next_weight_kg": target_weight_kg,
        "consecutive_misses": 0,
        "message": f"In the range — same load, chase {rep_high} reps on every set.",
    }
