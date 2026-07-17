from sqlalchemy import Column, DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import relationship

from ..database import Base


class User(Base):
    __tablename__ = "users"
    # The same person can exist under both Apple and Google, and provider ids
    # are only unique per provider — so the constraint spans both columns.
    __table_args__ = (UniqueConstraint("provider", "provider_id", name="uq_provider_identity"),)

    id = Column(Integer, primary_key=True)
    provider = Column(String, nullable=False)  # "apple" | "google"
    provider_id = Column(String, nullable=False)
    email = Column(String, nullable=True)
    display_name = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    weights = relationship("WeightLog", back_populates="user", cascade="all, delete-orphan")
    goals = relationship("Goal", back_populates="user", cascade="all, delete-orphan")
