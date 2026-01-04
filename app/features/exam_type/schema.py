from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from decimal import Decimal

class ExamTypeBase(BaseModel):
    name: str
    description: Optional[str] = None
    passing_score: int = 70
    duration_minutes: Optional[int] = None
    price: Decimal = Decimal('0.00')
    is_active: bool = True

class ExamTypeCreate(ExamTypeBase):
    pass

class ExamTypeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    passing_score: Optional[int] = None
    duration_minutes: Optional[int] = None
    price: Optional[Decimal] = None
    is_active: Optional[bool] = None

class ExamTypeResponse(ExamTypeBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True




