from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, date
from app.models.enums import LicenseStatus, Gender, BloodType, LicenseType

class LicenseCreate(BaseModel):
    # النظام الجديد: نوع الرخصة من جدول (يدخلها الأدمن)
    license_type_id: Optional[int] = None
    license_category: Optional[str] = None  # A / B (اختياري حسب النوع)
    # النظام القديم (للتوافق)
    license_type: Optional[LicenseType] = None
    full_name: str
    birth_date: date  # تاريخ الميلاد
    gender: Gender
    passport_number: str
    nationality: str
    blood_type: BloodType
    place_of_birth: Optional[str] = None  # مكان الميلاد
    residence_address: Optional[str] = None  # محل الإقامة
    email: Optional[EmailStr] = None
    photo_path: Optional[str] = None  # مسار الصورة الشخصية
    residence_certificate_path: Optional[str] = None  # شهادة الإقامة
    birth_certificate_path: Optional[str] = None  # شهادة الميلاد
    passport_image_path: Optional[str] = None  # صورة جواز السفر

class LicenseUpdate(BaseModel):
    status: Optional[LicenseStatus] = None
    review_notes: Optional[str] = None
    rejection_reason: Optional[str] = None

class LicenseResponse(BaseModel):
    id: int
    user_id: int
    user_national_id: Optional[str] = None
    license_number: Optional[str]
    barcode: Optional[str] = None  # باركود الرخصة
    license_type: LicenseType
    license_type_id: Optional[int] = None
    license_category: Optional[str] = None
    # معلومات النوع من الجدول (للطباعة/العرض في Flutter)
    license_type_name: Optional[str] = None
    license_degree_order: Optional[int] = None
    license_top_color: Optional[str] = None
    license_validity_years: Optional[int] = None
    license_allowed_vehicles: Optional[str] = None
    issued_by_user_id: Optional[int] = None
    issued_by_national_id: Optional[str] = None
    full_name: str
    birth_date: Optional[date] = None  # اختياري للتوافق مع البيانات القديمة
    age: int
    gender: Gender
    passport_number: str
    nationality: str
    blood_type: BloodType
    place_of_birth: Optional[str] = None
    residence_address: Optional[str] = None
    email: Optional[str]
    photo_path: Optional[str]
    residence_certificate_path: Optional[str] = None
    birth_certificate_path: Optional[str] = None
    passport_image_path: Optional[str] = None
    status: LicenseStatus
    application_date: datetime
    exam_date: Optional[datetime]
    exam_result: Optional[str]
    exam_score: Optional[int]
    review_date: Optional[datetime]
    review_notes: Optional[str]
    issued_date: Optional[datetime]
    expiry_date: Optional[date]
    rejection_reason: Optional[str]

    # Department approval/signature
    dept_approval_requested: Optional[int] = 0
    dept_approval_requested_at: Optional[datetime] = None
    dept_approval_requested_by_user_id: Optional[int] = None
    dept_approval_approved: Optional[int] = 0
    dept_approval_approved_at: Optional[datetime] = None
    dept_approval_approved_by_user_id: Optional[int] = None
    dept_approval_notes: Optional[str] = None
    signature_image_path: Optional[str] = None  # مسار صورة التوقيع الحقيقي

    chronic_disease: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    
    class Config:
        from_attributes = True

class LicenseReview(BaseModel):
    status: LicenseStatus
    review_notes: Optional[str] = None
    rejection_reason: Optional[str] = None

class LicenseExamSchedule(BaseModel):
    exam_type_id: int
    scheduled_date: datetime
    user_id: Optional[int] = None


class LicenseExamScheduleItem(BaseModel):
    exam_type_id: int
    scheduled_date: datetime


class LicenseExamScheduleBundle(BaseModel):
    """جدولة عدة امتحانات (مثلاً الامتحانات الثلاثة) مرة واحدة لنفس الرخصة"""
    user_id: Optional[int] = None
    exams: list[LicenseExamScheduleItem]


class LicenseImportantInfoUpdate(BaseModel):
    """معلومات مهمة يضيفها المواطن بعد إصدار الرخصة (عبر تطبيق المواطن بعد تسجيل الدخول)."""
    chronic_disease: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None

