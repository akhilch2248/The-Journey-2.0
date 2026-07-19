"""Unit tests for the progression engine — pure logic, no database."""

from app.services.progression import next_targets


def _sets(*reps, weight=50.0, amrap_last=False):
    out = [{"weight_kg": weight, "reps": r, "is_amrap": False} for r in reps]
    if amrap_last and out:
        out[-1]["is_amrap"] = True
    return out


def test_first_session_sets_baseline_from_logged_weight():
    r = next_targets(
        target_weight_kg=None, rep_low=6, rep_high=10, consecutive_misses=0,
        equipment="barbell", category="compound", sets=_sets(8, 8, 7, weight=60),
    )
    assert r["decision"] == "baseline"
    assert r["next_weight_kg"] == 60.0
    assert r["consecutive_misses"] == 0


def test_bodyweight_baseline_has_no_weight():
    r = next_targets(
        target_weight_kg=None, rep_low=6, rep_high=10, consecutive_misses=0,
        equipment="bodyweight", category="compound",
        sets=[{"weight_kg": None, "reps": 10, "is_amrap": False}],
    )
    assert r["decision"] == "baseline"
    assert r["next_weight_kg"] is None


def test_all_sets_at_top_increases_load_by_compound_increment():
    r = next_targets(
        target_weight_kg=60, rep_low=6, rep_high=10, consecutive_misses=0,
        equipment="barbell", category="compound", sets=_sets(10, 10, 11),
    )
    assert r["decision"] == "increase"
    assert r["next_weight_kg"] == 62.5  # +2.5 barbell compound


def test_dumbbell_isolation_increment_is_one_kg():
    r = next_targets(
        target_weight_kg=12, rep_low=10, rep_high=15, consecutive_misses=0,
        equipment="dumbbell", category="isolation", sets=_sets(15, 15, 15, weight=12),
    )
    assert r["decision"] == "increase"
    assert r["next_weight_kg"] == 13.0


def test_mid_range_holds_load_and_chases_reps():
    r = next_targets(
        target_weight_kg=60, rep_low=6, rep_high=10, consecutive_misses=0,
        equipment="barbell", category="compound", sets=_sets(9, 8, 7),
    )
    assert r["decision"] == "add_rep"
    assert r["next_weight_kg"] == 60
    assert r["consecutive_misses"] == 0


def test_below_bottom_once_holds_and_counts_the_miss():
    r = next_targets(
        target_weight_kg=60, rep_low=6, rep_high=10, consecutive_misses=0,
        equipment="barbell", category="compound", sets=_sets(6, 5, 4),
    )
    assert r["decision"] == "hold"
    assert r["next_weight_kg"] == 60
    assert r["consecutive_misses"] == 1


def test_second_consecutive_miss_deloads_ten_percent():
    r = next_targets(
        target_weight_kg=60, rep_low=6, rep_high=10, consecutive_misses=1,
        equipment="barbell", category="compound", sets=_sets(5, 5, 4),
    )
    assert r["decision"] == "deload"
    assert r["next_weight_kg"] == 54.0  # 60 * 0.9
    assert r["consecutive_misses"] == 0


def test_amrap_blowout_triggers_increase_even_mid_range():
    # Last set AMRAP at rep_high + 3 — clear signal the load is light.
    r = next_targets(
        target_weight_kg=60, rep_low=6, rep_high=10, consecutive_misses=0,
        equipment="barbell", category="compound", sets=_sets(9, 9, 13, amrap_last=True),
    )
    assert r["decision"] == "increase"
    assert r["next_weight_kg"] == 62.5


def test_bodyweight_at_top_keeps_chasing_reps():
    r = next_targets(
        target_weight_kg=0, rep_low=6, rep_high=12, consecutive_misses=0,
        equipment="bodyweight", category="compound",
        sets=[{"weight_kg": None, "reps": 12, "is_amrap": False}] * 3,
    )
    assert r["decision"] == "add_rep"


def test_load_rounds_to_quarter_kg():
    r = next_targets(
        target_weight_kg=41, rep_low=6, rep_high=10, consecutive_misses=1,
        equipment="barbell", category="compound", sets=_sets(4, 4, 4, weight=41),
    )
    assert r["decision"] == "deload"
    assert r["next_weight_kg"] == 37.0  # 36.9 → nearest 0.25


def test_no_sets_changes_nothing():
    r = next_targets(
        target_weight_kg=60, rep_low=6, rep_high=10, consecutive_misses=1,
        equipment="barbell", category="compound", sets=[],
    )
    assert r["decision"] == "hold"
    assert r["next_weight_kg"] == 60
    assert r["consecutive_misses"] == 1
