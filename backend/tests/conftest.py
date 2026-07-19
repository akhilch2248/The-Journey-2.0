import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.database import Base, get_db
from app.main import app
from app.seed import seed_exercises

# One shared in-memory SQLite per test (StaticPool keeps every session on the
# same connection, otherwise each connection would see an empty database).
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def tmp_uploads(tmp_path):
    """Uploaded images land in a per-test temp dir, never ./uploads."""
    settings = get_settings()
    original = settings.upload_dir
    settings.upload_dir = str(tmp_path / "uploads")
    yield
    settings.upload_dir = original


@pytest.fixture()
def client():
    Base.metadata.create_all(bind=engine)
    with TestingSessionLocal() as seed_db:
        seed_exercises(seed_db)  # the generator needs the library present

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def login(client: TestClient, id_token: str = "test-user", provider: str = "apple") -> dict:
    """Log in via dev auth and return auth headers."""
    res = client.post(f"/auth/{provider}", json={"id_token": id_token})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.fixture()
def auth_headers(client):
    return login(client)
