from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date

from app.models.enums import LicenseRenewalStatus


class LicenseReplacementCreate(BaseModel):
    license_id: int
    police_report_path: str = Field(..., min_length=1)
    citizen_notes: Optional[str] = None


class LicenseReplacementApprove(BaseModel):
    payment_confirmed: bool = True
    payment_code: str = Field(..., min_length=1)
    officer_notes: Optional[str] = None


class LicenseReplacementReject(BaseModel):
    officer_notes: Optional[str] = None


class LicenseReplacementResponse(BaseModel):
    id: int
    tracking_code: str
    payment_code: str
    license_id: int
    user_id: int
    police_report_path: str
    status: LicenseRenewalStatus
    payment_confirmed: bool
    citizen_notes: Optional[str] = None
    officer_notes: Optional[str] = None
    requested_at: datetime
    reviewed_at: Optional[datetime] = None
    reviewed_by_user_id: Optional[int] = None
    old_barcode: Optional[str] = None
    new_barcode: Optional[str] = None

    # convenience fields
    license_number: Optional[str] = None
    full_name: Optional[str] = None
    user_national_id: Optional[str] = None
    expiry_date: Optional[date] = None

    class Config:
        from_attributes = True


