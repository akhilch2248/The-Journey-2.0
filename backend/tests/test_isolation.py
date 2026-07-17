"""The security property that matters most: users can never see or touch
each other's data."""

from .conftest import login


def test_users_see_only_their_own_weights(client):
    alice = login(client, "alice")
    bob = login(client, "bob")

    client.post("/weights", json={"date": "2026-07-01", "weight_kg": 70}, headers=alice)
    client.post("/weights", json={"date": "2026-07-01", "weight_kg": 90}, headers=bob)

    alice_rows = client.get("/weights", headers=alice).json()
    bob_rows = client.get("/weights", headers=bob).json()
    assert [r["weight_kg"] for r in alice_rows] == [70]
    assert [r["weight_kg"] for r in bob_rows] == [90]


def test_cannot_update_someone_elses_weight(client):
    alice = login(client, "alice")
    bob = login(client, "bob")
    wid = client.post(
        "/weights", json={"date": "2026-07-01", "weight_kg": 70}, headers=alice
    ).json()["id"]

    res = client.put(f"/weights/{wid}", json={"weight_kg": 60}, headers=bob)
    assert res.status_code == 404  # not 403: existence is not revealed

    unchanged = client.get("/weights/latest", headers=alice).json()
    assert unchanged["weight_kg"] == 70


def test_cannot_delete_someone_elses_weight(client):
    alice = login(client, "alice")
    bob = login(client, "bob")
    wid = client.post(
        "/weights", json={"date": "2026-07-01", "weight_kg": 70}, headers=alice
    ).json()["id"]

    assert client.delete(f"/weights/{wid}", headers=bob).status_code == 404
    assert len(client.get("/weights", headers=alice).json()) == 1


def test_stats_and_goals_are_isolated(client):
    alice = login(client, "alice")
    bob = login(client, "bob")
    client.post("/weights", json={"date": "2026-07-01", "weight_kg": 70}, headers=alice)
    client.put("/goals", json={"target_weight_kg": 65}, headers=alice)

    assert client.get("/weights/stats", headers=bob).json()["count"] == 0
    assert client.get("/goals/current", headers=bob).status_code == 404
