from sqlalchemy import JSON, Column, Date, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from ..database import Base


class PhysiqueGoal(Base):
    """A visual training target: "look like <reference>".

    The active goal is the one with superseded_at NULL; setting a new goal
    stamps the old one instead of deleting it, so re-assessment history stays.
    gap_report is filled by the structured self-report form (Phase 1) or a
    vision model (Phase 2) — same schema either way.
    """

    __tablename__ = "physique_goals"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    reference_label = Column(String, nullable=False)
    reference_image_path = Column(String, nullable=True)
    gap_report = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    superseded_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="physique_goals")


class ProgressPhoto(Base):
    __tablename__ = "progress_photos"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    image_path = Column(String, nullable=False)
    taken_at = Column(Date, nullable=False)
    note = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="progress_photos")
