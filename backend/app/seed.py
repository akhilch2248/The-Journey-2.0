"""Seed the exercise library from the domain knowledge files.

Idempotent upsert by name: existing rows are updated in place (so evolving the
knowledge file evolves the library on next seed), new rows are inserted,
nothing is deleted. Runs automatically on app startup when the table is empty;
run `python -m app.seed` after editing exercises.json in production.
"""

from sqlalchemy.orm import Session

from .domain import load_exercises
from .models import Exercise


def seed_exercises(db: Session) -> int:
    data = load_exercises()
    existing = {ex.name: ex for ex in db.query(Exercise).all()}
    count = 0
    for row in data["exercises"]:
        ex = existing.get(row["name"])
        if ex is None:
            ex = Exercise(name=row["name"])
            db.add(ex)
        ex.primary_muscle = row["primary_muscle"]
        ex.secondary_muscles = row["secondary_muscles"]
        ex.equipment = row["equipment"]
        ex.movement_pattern = row["movement_pattern"]
        ex.category = row["category"]
        ex.contraindications = row["contraindications"]
        ex.cue = row["cue"]
        count += 1
    db.commit()
    return count


if __name__ == "__main__":
    from .database import SessionLocal

    with SessionLocal() as session:
        n = seed_exercises(session)
        print(f"Seeded {n} exercises")
