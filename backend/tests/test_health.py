def test_root_serves_web_app(client):
    res = client.get("/")  # follows the redirect to /app/
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/html")


def test_healthz(client):
    res = client.get("/healthz")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "database": "ok"}
