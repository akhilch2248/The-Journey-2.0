def log(client, headers, d, kg):
    res = client.post("/weights", json={"date": d, "weight_kg": kg}, headers=headers)
    assert res.status_code == 201


def test_goal_requires_a_logged_weight(client, auth_headers):
    res = client.put("/goals", json={"target_weight_kg": 85}, headers=auth_headers)
    assert res.status_code == 400


def test_set_goal_snapshots_start_weight(client, auth_headers):
    log(client, auth_headers, "2026-07-01", 95.0)
    res = client.put(
        "/goals",
        json={"target_weight_kg": 85, "target_date": "2026-12-31"},
        headers=auth_headers,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["start_weight_kg"] == 95.0
    assert body["target_weight_kg"] == 85.0
    assert body["active"] is True


def test_progress_math(client, auth_headers):
    log(client, auth_headers, "2026-07-01", 95.0)
    client.put("/goals", json={"target_weight_kg": 85}, headers=auth_headers)
    log(client, auth_headers, "2026-07-10", 91.0)

    body = client.get("/goals/current", headers=auth_headers).json()
    assert body["current_weight_kg"] == 91.0
    assert body["lost_kg"] == 4.0
    assert body["remaining_kg"] == 6.0
    assert body["percent_complete"] == 40.0


def test_new_goal_replaces_old(client, auth_headers):
    log(client, auth_headers, "2026-07-01", 95.0)
    client.put("/goals", json={"target_weight_kg": 85}, headers=auth_headers)
    client.put("/goals", json={"target_weight_kg": 88}, headers=auth_headers)

    body = client.get("/goals/current", headers=auth_headers).json()
    assert body["goal"]["target_weight_kg"] == 88.0


def test_no_goal_404(client, auth_headers):
    assert client.get("/goals/current", headers=auth_headers).status_code == 404


def test_goal_validation(client, auth_headers):
    log(client, auth_headers, "2026-07-01", 95.0)
    assert client.put("/goals", json={"target_weight_kg": 0}, headers=auth_headers).status_code == 422
    assert client.put("/goals", json={"target_weight_kg": 600}, headers=auth_headers).status_code == 422
