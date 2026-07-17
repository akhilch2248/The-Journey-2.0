from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, func
from sqlalchemy.orm import relationship

from ..database import Base


class Goal(Base):
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    target_weight_kg = Column(Float, nullable=False)
    start_weight_kg = Column(Float, nullable=False)
    target_date = Column(Date, nullable=True)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="goals")
