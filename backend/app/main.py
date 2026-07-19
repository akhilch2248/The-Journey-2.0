from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from .database import Base, SessionLocal, engine
from .models import Exercise  # noqa: F401 — importing the package registers all tables
from .observability import install_observability, setup_logging
from .routes import (
    auth,
    exercises,
    goal,
    health,
    physique_goals,
    programs,
    progress_photos,
    weight,
    workout_sessions,
)
from .seed import seed_exercises

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Dev convenience: create missing tables on startup.
    # Production uses Alembic migrations instead (alembic upgrade head).
    Base.metadata.create_all(bind=engine)
    # Keep the exercise library present (idempotent; prod re-runs app.seed
    # after editing the domain knowledge files).
    with SessionLocal() as db:
        if db.query(Exercise).count() == 0:
            seed_exercises(db)
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
app.include_router(exercises.router)
app.include_router(physique_goals.router)
app.include_router(programs.router)
app.include_router(workout_sessions.router)
app.include_router(progress_photos.router)

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
