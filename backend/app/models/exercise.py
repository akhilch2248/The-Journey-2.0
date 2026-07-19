from sqlalchemy import JSON, Column, Integer, String, Text

from ..database import Base


class Exercise(Base):
    """One library movement, seeded from app/domain/exercises.json.

    contraindications carries tags like "axial_load" — the generator filters on
    these so a spine-conscious program never contains a flagged movement.
    """

    __tablename__ = "exercises"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    primary_muscle = Column(String, nullable=False, index=True)
    secondary_muscles = Column(JSON, nullable=False, default=list)
    equipment = Column(String, nullable=False)
    movement_pattern = Column(String, nullable=False)
    category = Column(String, nullable=False)  # compound | isolation | conditioning
    contraindications = Column(JSON, nullable=False, default=list)
    cue = Column(Text, nullable=False, default="")
