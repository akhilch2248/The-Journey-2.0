def test_metrics_endpoint(client, auth_headers):
    client.get("/weights", headers=auth_headers)
    res = client.get("/metrics")
    assert res.status_code == 200
    body = res.text
    assert "http_requests_total" in body
    assert 'path="/weights"' in body


def test_metrics_use_route_template_not_raw_path(client, auth_headers):
    wid = client.post(
        "/weights", json={"date": "2026-07-01", "weight_kg": 90}, headers=auth_headers
    ).json()["id"]
    client.delete(f"/weights/{wid}", headers=auth_headers)
    body = client.get("/metrics").text
    assert 'path="/weights/{weight_id}"' in body
    assert f'path="/weights/{wid}"' not in body
