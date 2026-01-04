from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date

from app.models.enums import LicenseRenewalStatus


class LicenseRenewalCreate(BaseModel):
    license_id: int
    new_photo_path: str = Field(..., min_length=1)
    citizen_notes: Optional[str] = None


class LicenseRenewalApprove(BaseModel):
    payment_confirmed: bool = True
    officer_notes: Optional[str] = None


class LicenseRenewalVisionExamSchedule(BaseModel):
    vision_exam_date: datetime


class LicenseRenewalReject(BaseModel):
    officer_notes: Optional[str] = None


class LicenseRenewalVisionExamResult(BaseModel):
    vision_exam_result: str  # 'passed' أو 'failed'
    officer_notes: Optional[str] = None


class LicenseRenewalResponse(BaseModel):
    id: int
    tracking_code: str
    license_id: int
    user_id: int
    new_photo_path: str
    status: LicenseRenewalStatus
    payment_confirmed: bool
    citizen_notes: Optional[str] = None
    officer_notes: Optional[str] = None
    requested_at: datetime
    reviewed_at: Optional[datetime] = None
    reviewed_by_user_id: Optional[int] = None

    # convenience fields
    license_number: Optional[str] = None
    full_name: Optional[str] = None
    user_national_id: Optional[str] = None
    expiry_date: Optional[date] = None
    
    # امتحان النظر
    vision_exam_date: Optional[datetime] = None
    vision_exam_result: Optional[str] = None
    vision_exam_conducted_by_user_id: Optional[int] = None
    
    # سعر التجديد
    renewal_fee: Optional[float] = None

    class Config:
        from_attributes = True

















