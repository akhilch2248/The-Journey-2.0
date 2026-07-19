"""Rule-based program generation.

Deterministic: the same gap report, equipment, and library always produce the
same program (candidates are sorted, never sampled). The gap report's emphasis
regions get extra sets (priority 2+) and an extra isolation slot (priority 3);
spine-conscious generation filters out every exercise tagged with an excluded
contraindication before any selection happens.
"""

from ..domain import REGION_MUSCLES, SPINE_EXCLUDED_TAGS, load_progression, load_splits
from ..models import Exercise


def _emphasized_muscles(gap_report: dict, min_priority: int) -> set[str]:
    out: set[str] = set()
    for region, priority in (gap_report or {}).get("emphasis", {}).items():
        if priority >= min_priority:
            out.update(REGION_MUSCLES.get(region, []))
    return out


def allowed_pool(exercises: list[Exercise], equipment: list[str], spine_conscious: bool) -> list[Exercise]:
    """Equipment + contraindication filter. Bodyweight is always available."""
    allowed_equipment = set(equipment) | {"bodyweight"}
    pool = []
    for ex in exercises:
        if ex.equipment not in allowed_equipment:
            continue
        if spine_conscious and set(ex.contraindications or []) & SPINE_EXCLUDED_TAGS:
            continue
        pool.append(ex)
    return pool


def _pick(pool, slot, used_counts, boost_muscles):
    """Best exercise for a slot: prefer emphasized muscles, then least-used,
    then name (for determinism). Falls back to ignoring the pattern before
    giving up, so a sparse library still fills the slot."""
    def candidates(match_pattern: bool):
        out = []
        for ex in pool:
            if ex.primary_muscle != slot["muscle"]:
                continue
            if ex.category != slot["category"]:
                continue
            if match_pattern and slot.get("pattern") and ex.movement_pattern != slot["pattern"]:
                continue
            out.append(ex)
        return out

    for match_pattern in (True, False):
        cands = candidates(match_pattern)
        if cands:
            cands.sort(key=lambda ex: (
                0 if ex.primary_muscle in boost_muscles else 1,
                used_counts.get(ex.id, 0),
                ex.name,
            ))
            return cands[0]
    return None


def build_program_spec(
    exercises: list[Exercise],
    gap_report: dict,
    days_per_week: int,
    equipment: list[str],
    spine_conscious: bool,
) -> dict:
    """Returns {"split_id", "split_name", "days": [{"label", "exercises": [
    {"exercise", "target_sets", "rep_low", "rep_high", "target_rir", "unit"}]}]}
    ready to be persisted by the route."""
    splits = load_splits()
    rules = load_progression()
    rep_ranges = rules["rep_ranges"]
    max_sets = rules["max_sets_per_exercise"]
    max_per_day = rules["max_exercises_per_day"]

    split_id = splits["by_days_per_week"][str(days_per_week)]
    template = next(t for t in splits["templates"] if t["id"] == split_id)

    pool = allowed_pool(exercises, equipment, spine_conscious)
    add_set_muscles = _emphasized_muscles(gap_report, 2)   # priority >= 2: +1 set
    extra_slot_muscles = _emphasized_muscles(gap_report, 3)  # priority 3: extra isolation
    used_counts: dict[int, int] = {}

    days = []
    for day_tpl in template["days"]:
        chosen = []
        for slot in day_tpl["slots"]:
            ex = _pick(pool, slot, used_counts, add_set_muscles)
            if ex is None:
                continue
            used_counts[ex.id] = used_counts.get(ex.id, 0) + 1
            rr = rep_ranges[ex.category]
            sets = rr["sets"] + (1 if ex.primary_muscle in add_set_muscles else 0)
            chosen.append({
                "exercise": ex,
                "target_sets": min(sets, max_sets),
                "rep_low": rr["low"],
                "rep_high": rr["high"],
                "target_rir": rr["rir"],
                "unit": rr.get("unit", "reps"),
            })
        days.append({"label": day_tpl["label"], "exercises": chosen})

    # Priority-3 regions earn one extra isolation movement, appended to the day
    # already training that muscle with the most room left.
    for muscle in sorted(extra_slot_muscles):
        slot = {"muscle": muscle, "pattern": None, "category": "isolation"}
        target_days = [d for d in days if any(
            e["exercise"].primary_muscle == muscle or muscle in (e["exercise"].secondary_muscles or [])
            for e in d["exercises"]
        )] or days
        target_days = [d for d in target_days if len(d["exercises"]) < max_per_day]
        if not target_days:
            continue
        day = min(target_days, key=lambda d: len(d["exercises"]))
        ex = _pick(pool, slot, used_counts, set())
        if ex is None:
            continue
        used_counts[ex.id] = used_counts.get(ex.id, 0) + 1
        rr = rep_ranges[ex.category]
        day["exercises"].append({
            "exercise": ex,
            "target_sets": rr["sets"],
            "rep_low": rr["low"],
            "rep_high": rr["high"],
            "target_rir": rr["rir"],
            "unit": rr.get("unit", "reps"),
        })

    return {"split_id": split_id, "split_name": template["name"], "days": days}
