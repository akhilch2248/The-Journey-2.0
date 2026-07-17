from datetime import date, timedelta


def post_weight(client, headers, d="2026-07-01", kg=94.5, **extra):
    return client.post(
        "/weights", json={"date": d, "weight_kg": kg, **extra}, headers=headers
    )


def test_create_weight(client, auth_headers):
    res = post_weight(client, auth_headers, note="after gym")
    assert res.status_code == 201
    body = res.json()
    assert body["weight_kg"] == 94.5
    assert body["date"] == "2026-07-01"
    assert body["source"] == "manual"
    assert body["note"] == "after gym"
    assert body["id"] > 0


def test_requires_auth(client):
    assert client.post("/weights", json={"date": "2026-07-01", "weight_kg": 90}).status_code == 401
    assert client.get("/weights").status_code == 401


def test_duplicate_date_conflict(client, auth_headers):
    assert post_weight(client, auth_headers).status_code == 201
    res = post_weight(client, auth_headers, kg=95.0)
    assert res.status_code == 409


def test_validation_rejects_bad_weight(client, auth_headers):
    assert post_weight(client, auth_headers, kg=0).status_code == 422
    assert post_weight(client, auth_headers, kg=-5).status_code == 422
    assert post_weight(client, auth_headers, kg=750).status_code == 422


def test_validation_rejects_future_date(client, auth_headers):
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    assert post_weight(client, auth_headers, d=tomorrow).status_code == 422


def test_list_sorted_desc(client, auth_headers):
    post_weight(client, auth_headers, d="2026-07-01", kg=95)
    post_weight(client, auth_headers, d="2026-07-03", kg=94)
    post_weight(client, auth_headers, d="2026-07-02", kg=94.5)
    res = client.get("/weights", headers=auth_headers)
    assert res.status_code == 200
    dates = [w["date"] for w in res.json()]
    assert dates == ["2026-07-03", "2026-07-02", "2026-07-01"]


def test_list_date_range(client, auth_headers):
    for i in range(1, 6):
        post_weight(client, auth_headers, d=f"2026-07-0{i}", kg=95 - i * 0.1)
    res = client.get(
        "/weights?start_date=2026-07-02&end_date=2026-07-04", headers=auth_headers
    )
    assert [w["date"] for w in res.json()] == ["2026-07-04", "2026-07-03", "2026-07-02"]


def test_list_pagination(client, auth_headers):
    for i in range(1, 6):
        post_weight(client, auth_headers, d=f"2026-07-0{i}", kg=95)
    page = client.get("/weights?limit=2&offset=2", headers=auth_headers).json()
    assert [w["date"] for w in page] == ["2026-07-03", "2026-07-02"]


def test_latest(client, auth_headers):
    post_weight(client, auth_headers, d="2026-07-01", kg=95)
    post_weight(client, auth_headers, d="2026-07-05", kg=93.8)
    res = client.get("/weights/latest", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["date"] == "2026-07-05"


def test_latest_empty_404(client, auth_headers):
    assert client.get("/weights/latest", headers=auth_headers).status_code == 404


def test_update_weight(client, auth_headers):
    wid = post_weight(client, auth_headers).json()["id"]
    res = client.put(f"/weights/{wid}", json={"weight_kg": 93.9}, headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["weight_kg"] == 93.9


def test_update_empty_body_400(client, auth_headers):
    wid = post_weight(client, auth_headers).json()["id"]
    assert client.put(f"/weights/{wid}", json={}, headers=auth_headers).status_code == 400


def test_delete_weight(client, auth_headers):
    wid = post_weight(client, auth_headers).json()["id"]
    assert client.delete(f"/weights/{wid}", headers=auth_headers).status_code == 204
    assert client.get("/weights", headers=auth_headers).json() == []


def test_delete_missing_404(client, auth_headers):
    assert client.delete("/weights/12345", headers=auth_headers).status_code == 404
