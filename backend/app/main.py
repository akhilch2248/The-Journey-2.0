from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from .database import Base, engine
from .models import Goal, User, WeightLog  # noqa: F401 — registers tables on Base
from .observability import install_observability, setup_logging
from .routes import auth, goal, health, weight

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Dev convenience: create missing tables on startup.
    # Production uses Alembic migrations instead (alembic upgrade head).
    Base.metadata.create_all(bind=engine)
    yield


setup_logging()

app = FastAPI(
    title="The Journey API",
    description="Weight tracking backend — auth, weight logs, goals, and trends.",
    version="1.0.0",
    lifespan=lifespan,
)

install_observability(app)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(weight.router)
app.include_router(goal.router)

# The web app: a static SPA served at /app, talking to this same API.
app.mount("/app", StaticFiles(directory=STATIC_DIR, html=True), name="app")


@app.middleware("http")
async def static_no_cache(request, call_next):
    """Make browsers revalidate app assets so UI updates ship immediately.
    (ETags still allow 304s, so repeat loads stay cheap.)"""
    response = await call_next(request)
    if request.url.path.startswith("/app"):
        response.headers["Cache-Control"] = "no-cache"
    return response


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/app/")
