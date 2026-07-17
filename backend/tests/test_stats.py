def seed(client, headers, entries):
    for d, kg in entries:
        res = client.post("/weights", json={"date": d, "weight_kg": kg}, headers=headers)
        assert res.status_code == 201


def test_stats_empty(client, auth_headers):
    res = client.get("/weights/stats", headers=auth_headers)
    assert res.status_code == 200
    body = res.json()
    assert body["count"] == 0
    assert body["latest_weight_kg"] is None


def test_stats_single_entry(client, auth_headers):
    seed(client, auth_headers, [("2026-07-01", 95.0)])
    body = client.get("/weights/stats", headers=auth_headers).json()
    assert body["count"] == 1
    assert body["total_change_kg"] == 0.0
    assert body["moving_avg_7d_kg"] == 95.0
    assert body["avg_weekly_change_kg"] is None  # zero-day span


def test_stats_trend(client, auth_headers):
    seed(
        client,
        auth_headers,
        [
            ("2026-06-01", 96.0),
            ("2026-06-15", 95.0),
            ("2026-06-29", 94.0),
            ("2026-07-10", 93.5),
            ("2026-07-13", 93.0),  # latest; 7d window covers Jul 10 + Jul 13
        ],
    )
    body = client.get("/weights/stats", headers=auth_headers).json()
    assert body["count"] == 5
    assert body["start_weight_kg"] == 96.0
    assert body["latest_weight_kg"] == 93.0
    assert body["min_weight_kg"] == 93.0
    assert body["max_weight_kg"] == 96.0
    assert body["total_change_kg"] == -3.0
    assert body["moving_avg_7d_kg"] == 93.25
    # -3.0 kg over 42 days => -0.5 kg/week
    assert body["avg_weekly_change_kg"] == -0.5
