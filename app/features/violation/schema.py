from pydantic import BaseModel, model_validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from app.models.enums import ViolationStatus
from pydantic import Field

class ViolationBase(BaseModel):
    # العلاقة الحقيقية
    violation_type_id: Optional[int] = None
    # للتوافق مع الإصدارات القديمة (سيتم ربطه/إنشاء نوع تلقائياً في الخدمة)
    violation_type: Optional[str] = None
    description: str
    location: str
    violation_date: datetime
    # إذا أرسلت violation_type_id سيتم حسابها من نوع المخالفة، وإلا يجب إرسالها مع violation_type
    fine_amount: Optional[Decimal] = None

    @model_validator(mode="after")
    def _validate_type(self):
        if self.violation_type_id is None and not self.violation_type:
            raise ValueError("يجب إرسال violation_type_id أو violation_type")
        return self

class ViolationCreate(ViolationBase):
    user_id: int
    license_id: Optional[int] = None


class ViolationCreateByLicenseNumber(BaseModel):
    license_number: str
    violation_type_id: int
    description: str
    location: str
    violation_date: datetime = Field(default_factory=datetime.utcnow)

class ViolationCreateByNationalId(BaseModel):
    national_id: str
    violation_type_id: int
    description: str
    location: str
    violation_date: datetime = Field(default_factory=datetime.utcnow)

class ViolationUpdate(BaseModel):
    status: Optional[ViolationStatus] = None
    appeal_reason: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    violation_type_id: Optional[int] = None
    fine_amount: Optional[Decimal] = None
    modification_reason: Optional[str] = None

class ViolationCancelRequest(BaseModel):
    cancellation_reason: str

class ViolationModifyRequest(BaseModel):
    description: Optional[str] = None
    location: Optional[str] = None
    violation_type_id: Optional[int] = None
    fine_amount: Optional[Decimal] = None
    modification_reason: str

class ViolationResponse(BaseModel):
    id: int
    user_id: int
    license_id: Optional[int]
    violation_number: str
    violation_type_id: Optional[int] = None
    violation_type: str
    description: str
    location: str
    violation_date: datetime
    fine_amount: Decimal
    status: ViolationStatus
    created_by: int
    created_at: datetime
    paid_at: Optional[datetime]
    paid_by_user_id: Optional[int] = None
    appeal_reason: Optional[str]
    cancelled_at: Optional[datetime] = None
    cancelled_by_user_id: Optional[int] = None
    cancellation_reason: Optional[str] = None
    modified_at: Optional[datetime] = None
    modified_by_user_id: Optional[int] = None
    modification_reason: Optional[str] = None
    
    class Config:
        from_attributes = True


class LicenseBasicInfo(BaseModel):
    id: int
    license_number: Optional[str]
    full_name: str
    status: str


class ViolationsByLicenseResponse(BaseModel):
    license: LicenseBasicInfo
    violations: List[ViolationResponse]
    has_violations: bool
    violations_count: int


class CitizenBasicInfo(BaseModel):
    id: int
    national_id: str
    phone: str


class ViolationsByNationalIdResponse(BaseModel):
    citizen: CitizenBasicInfo
    violations: List[ViolationResponse]
    has_violations: bool
    violations_count: int


class PaymentReceiptResponse(BaseModel):
    receipt_number: str
    violation_number: str
    national_id: str
    citizen_name: Optional[str] = None
    fine_amount: Decimal
    payment_date: datetime
    officer_name: str
    officer_username: Optional[str] = None


class ViolationStatisticsResponse(BaseModel):
    total_violations: int
    pending_violations: int
    paid_violations: int
    cancelled_violations: int
    total_amount: Decimal
    paid_amount: Decimal
    pending_amount: Decimal
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None














