"""Physique goals, assessment, program generation, sessions, and isolation."""

from app.domain import SPINE_EXCLUDED_TAGS

from .conftest import login


def make_goal(client, headers, label="Vidyut Jammwal"):
    res = client.post("/physique-goals", data={"reference_label": label}, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()


def assess(client, headers, goal_id, emphasis=None):
    emphasis = emphasis or {"back_width": 3, "shoulder_width": 2, "chest": 1}
    res = client.post(f"/physique-goals/{goal_id}/assessment", json={"emphasis": emphasis}, headers=headers)
    assert res.status_code == 200, res.text
    return res.json()


def generate(client, headers, days=4, equipment=None, spine=True):
    res = client.post("/programs/generate", json={
        "days_per_week": days,
        "equipment": equipment or ["barbell", "dumbbell", "cable", "machine", "bodyweight"],
        "spine_conscious": spine,
    }, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()


# ---------- goals & assessment ----------

def test_goal_lifecycle_and_supersede(client, auth_headers):
    g1 = make_goal(client, auth_headers, "Goku")
    g2 = make_goal(client, auth_headers, "Batman")
    active = client.get("/physique-goals/active", headers=auth_headers).json()
    assert active["id"] == g2["id"]
    assert active["reference_label"] == "Batman"
    assert g1["superseded_at"] is None  # was active when returned…
    # …but a fresh read of goal 1 via active shows it's gone: only g2 is active.


def test_assessment_validation(client, auth_headers):
    goal = make_goal(client, auth_headers)
    bad_region = client.post(f"/physique-goals/{goal['id']}/assessment",
                             json={"emphasis": {"wings": 3}}, headers=auth_headers)
    assert bad_region.status_code == 422
    bad_priority = client.post(f"/physique-goals/{goal['id']}/assessment",
                               json={"emphasis": {"chest": 7}}, headers=auth_headers)
    assert bad_priority.status_code == 422
    all_zero = client.post(f"/physique-goals/{goal['id']}/assessment",
                           json={"emphasis": {"chest": 0}}, headers=auth_headers)
    assert all_zero.status_code == 422


def test_assessment_saves_gap_report(client, auth_headers):
    goal = make_goal(client, auth_headers)
    updated = assess(client, auth_headers, goal["id"])
    assert updated["gap_report"]["emphasis"] == {"back_width": 3, "shoulder_width": 2, "chest": 1}
    assert updated["gap_report"]["source"] == "self_report"


def test_goals_are_isolated_between_users(client):
    h_a = login(client, "user-a")
    h_b = login(client, "user-b")
    goal = make_goal(client, h_a)
    assert client.get("/physique-goals/active", headers=h_b).status_code == 404
    res = client.post(f"/physique-goals/{goal['id']}/assessment",
                      json={"emphasis": {"chest": 2}}, headers=h_b)
    assert res.status_code == 404


# ---------- program generation ----------

def test_generate_requires_goal_then_assessment(client, auth_headers):
    res = client.post("/programs/generate", json={
        "days_per_week": 4, "equipment": ["machine"], "spine_conscious": True,
    }, headers=auth_headers)
    assert res.status_code == 400
    goal = make_goal(client, auth_headers)
    res2 = client.post("/programs/generate", json={
        "days_per_week": 4, "equipment": ["machine"], "spine_conscious": True,
    }, headers=auth_headers)
    assert res2.status_code == 400
    assess(client, auth_headers, goal["id"])
    program = generate(client, auth_headers)
    assert program["status"] == "active"


def test_program_structure_matches_split(client, auth_headers):
    goal = make_goal(client, auth_headers)
    assess(client, auth_headers, goal["id"])
    program = generate(client, auth_headers, days=6)
    assert program["split_type"] == "ulplp_athlete_6"
    assert len(program["days"]) == 6
    labels = [d["day_label"] for d in program["days"]]
    assert labels == ["Upper", "Lower", "Push", "Legs", "Pull", "Athlete"]
    for day in program["days"]:
        assert 1 <= len(day["exercises"]) <= 8
        for pe in day["exercises"]:
            assert pe["target_sets"] >= 2
            assert pe["rep_low"] < pe["rep_high"]
            assert pe["target_weight_kg"] is None  # baseline comes from session 1


def test_spine_conscious_program_has_no_flagged_exercises(client, auth_headers):
    goal = make_goal(client, auth_headers)
    assess(client, auth_headers, goal["id"])
    program = generate(client, auth_headers, days=6, spine=True)
    for day in program["days"]:
        for pe in day["exercises"]:
            tags = set(pe["exercise"]["contraindications"])
            assert not (tags & SPINE_EXCLUDED_TAGS), \
                f"{pe['exercise']['name']} carries {tags & SPINE_EXCLUDED_TAGS}"


def test_spine_filter_swaps_barbell_squat(client, auth_headers):
    goal = make_goal(client, auth_headers)
    assess(client, auth_headers, goal["id"])
    barbell_only = ["barbell", "bodyweight"]
    risky = generate(client, auth_headers, days=4, equipment=barbell_only, spine=False)
    names_risky = {pe["exercise"]["name"] for d in risky["days"] for pe in d["exercises"]}
    assert "Barbell Back Squat" in names_risky
    safe = generate(client, auth_headers, days=4, equipment=barbell_only, spine=True)
    names_safe = {pe["exercise"]["name"] for d in safe["days"] for pe in d["exercises"]}
    assert "Barbell Back Squat" not in names_safe


def test_equipment_filter_is_respected(client, auth_headers):
    goal = make_goal(client, auth_headers)
    assess(client, auth_headers, goal["id"])
    program = generate(client, auth_headers, days=3, equipment=["dumbbell", "bodyweight"])
    for day in program["days"]:
        for pe in day["exercises"]:
            assert pe["exercise"]["equipment"] in {"dumbbell", "bodyweight"}


def test_emphasis_adds_volume_and_an_extra_movement(client, auth_headers):
    goal = make_goal(client, auth_headers)
    # Neutral: single low-priority region vs boosted delts_side at priority 3.
    assess(client, auth_headers, goal["id"], emphasis={"chest": 1})
    neutral = generate(client, auth_headers, days=4)
    assess(client, auth_headers, goal["id"], emphasis={"shoulder_width": 3})
    boosted = generate(client, auth_headers, days=4)

    def delts_side_stats(program):
        count, max_sets = 0, 0
        for d in program["days"]:
            for pe in d["exercises"]:
                if pe["exercise"]["primary_muscle"] == "delts_side":
                    count += 1
                    max_sets = max(max_sets, pe["target_sets"])
        return count, max_sets

    n_count, n_sets = delts_side_stats(neutral)
    b_count, b_sets = delts_side_stats(boosted)
    assert b_sets == n_sets + 1      # priority ≥2 → +1 set on the slot
    assert b_count > n_count         # priority 3 → extra isolation appended


def test_generate_archives_previous_program(client, auth_headers):
    goal = make_goal(client, auth_headers)
    assess(client, auth_headers, goal["id"])
    p1 = generate(client, auth_headers)
    p2 = generate(client, auth_headers)
    old = client.get(f"/programs/{p1['id']}", headers=auth_headers).json()
    assert old["status"] == "archived"
    active = client.get("/programs/active", headers=auth_headers).json()
    assert active["id"] == p2["id"]


def test_programs_are_isolated(client):
    h_a = login(client, "gen-a")
    h_b = login(client, "gen-b")
    goal = make_goal(client, h_a)
    assess(client, h_a, goal["id"])
    program = generate(client, h_a)
    assert client.get("/programs/active", headers=h_b).status_code == 404
    assert client.get(f"/programs/{program['id']}", headers=h_b).status_code == 404


# ---------- sessions & progression over the wire ----------

def setup_program(client, headers, days=4):
    goal = make_goal(client, headers)
    assess(client, headers, goal["id"])
    return generate(client, headers, days=days)


def log_full_exercise(client, headers, session_id, pe, reps, weight=40.0):
    for n in range(1, pe["target_sets"] + 1):
        res = client.post(f"/sessions/{session_id}/sets", json={
            "program_exercise_id": pe["id"], "set_number": n,
            "weight_kg": weight, "reps": reps, "rir": 2,
        }, headers=headers)
        assert res.status_code == 201, res.text


def test_session_baseline_then_increase(client, auth_headers):
    program = setup_program(client, auth_headers)
    day = program["days"][0]
    pe = day["exercises"][0]

    s1 = client.post("/sessions", json={"program_day_id": day["id"]}, headers=auth_headers)
    assert s1.status_code == 201, s1.text
    sid1 = s1.json()["session"]["id"]
    log_full_exercise(client, auth_headers, sid1, pe, reps=8, weight=40)
    done1 = client.post(f"/sessions/{sid1}/complete", headers=auth_headers).json()
    d1 = next(d for d in done1["decisions"] if d["program_exercise_id"] == pe["id"])
    assert d1["decision"] == "baseline"
    assert d1["next_weight_kg"] == 40.0

    s2 = client.post("/sessions", json={"program_day_id": day["id"]}, headers=auth_headers)
    sid2 = s2.json()["session"]["id"]
    log_full_exercise(client, auth_headers, sid2, pe, reps=pe["rep_high"], weight=40)
    done2 = client.post(f"/sessions/{sid2}/complete", headers=auth_headers).json()
    d2 = next(d for d in done2["decisions"] if d["program_exercise_id"] == pe["id"])
    assert d2["decision"] == "increase"
    assert d2["next_weight_kg"] > 40.0

    refreshed = client.get("/programs/active", headers=auth_headers).json()
    pe_after = next(p for d in refreshed["days"] for p in d["exercises"] if p["id"] == pe["id"])
    assert pe_after["target_weight_kg"] == d2["next_weight_kg"]


def test_only_one_session_in_progress(client, auth_headers):
    program = setup_program(client, auth_headers)
    day = program["days"][0]
    first = client.post("/sessions", json={"program_day_id": day["id"]}, headers=auth_headers)
    assert first.status_code == 201
    second = client.post("/sessions", json={"program_day_id": day["id"]}, headers=auth_headers)
    assert second.status_code == 409


def test_set_must_belong_to_the_sessions_day(client, auth_headers):
    program = setup_program(client, auth_headers)
    day0, day1 = program["days"][0], program["days"][1]
    sid = client.post("/sessions", json={"program_day_id": day0["id"]},
                      headers=auth_headers).json()["session"]["id"]
    foreign_pe = day1["exercises"][0]
    res = client.post(f"/sessions/{sid}/sets", json={
        "program_exercise_id": foreign_pe["id"], "set_number": 1, "weight_kg": 20, "reps": 8,
    }, headers=auth_headers)
    assert res.status_code == 400


def test_completed_session_rejects_more_work(client, auth_headers):
    program = setup_program(client, auth_headers)
    day = program["days"][0]
    sid = client.post("/sessions", json={"program_day_id": day["id"]},
                      headers=auth_headers).json()["session"]["id"]
    assert client.post(f"/sessions/{sid}/complete", headers=auth_headers).status_code == 200
    again = client.post(f"/sessions/{sid}/complete", headers=auth_headers)
    assert again.status_code == 409
    late_set = client.post(f"/sessions/{sid}/sets", json={
        "program_exercise_id": day["exercises"][0]["id"], "set_number": 1, "weight_kg": 20, "reps": 8,
    }, headers=auth_headers)
    assert late_set.status_code == 409


def test_sessions_are_isolated(client):
    h_a = login(client, "sess-a")
    h_b = login(client, "sess-b")
    program = setup_program(client, h_a)
    day = program["days"][0]
    sid = client.post("/sessions", json={"program_day_id": day["id"]},
                      headers=h_a).json()["session"]["id"]
    assert client.get(f"/sessions/{sid}", headers=h_b).status_code == 404
    assert client.post(f"/sessions/{sid}/complete", headers=h_b).status_code == 404
    # B can't start a session on A's program day either.
    assert client.post("/sessions", json={"program_day_id": day["id"]}, headers=h_b).status_code == 404
