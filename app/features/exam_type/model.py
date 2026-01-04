from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Numeric
from sqlalchemy.sql import func
from app.core.database import Base

class ExamType(Base):
    __tablename__ = "exam_types"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(Text, nullable=True)
    passing_score = Column(Integer, default=70, nullable=False)
    duration_minutes = Column(Integer, nullable=True)
    price = Column(Numeric(10, 2), default=0.00, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)




