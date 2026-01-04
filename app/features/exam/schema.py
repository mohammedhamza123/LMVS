from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ExamBase(BaseModel):
    user_id: int
    license_id: Optional[int] = None
    exam_type_id: Optional[int] = None

class ExamCreate(ExamBase):
    pass

class ExamSchedule(BaseModel):
    scheduled_date: datetime

class ExamUpdate(BaseModel):
    score: Optional[int] = None
    result: Optional[str] = None
    notes: Optional[str] = None

class ExamResponse(BaseModel):
    id: int
    user_id: int
    license_id: Optional[int]
    exam_type_id: Optional[int]
    scheduled_date: Optional[datetime]
    exam_date: Optional[datetime]
    score: Optional[int]
    result: Optional[str]
    notes: Optional[str]
    conducted_by: Optional[int]
    conducted_by_national_id: Optional[str] = None
    created_by_user_id: Optional[int] = None
    created_by_national_id: Optional[str] = None
    scheduled_by_user_id: Optional[int] = None
    scheduled_by_national_id: Optional[str] = None
    paid_at: Optional[datetime] = None
    paid_by_user_id: Optional[int] = None
    paid_amount: Optional[float] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class ExamResult(BaseModel):
    score: Optional[int] = None
    result: str
    notes: Optional[str] = None

