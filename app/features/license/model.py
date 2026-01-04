from sqlalchemy import Column, Integer, String, Date, ForeignKey, Enum as SQLEnum, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.models.enums import LicenseStatus, Gender, BloodType, LicenseType

class License(Base):
    __tablename__ = "licenses"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    license_number = Column(String, unique=True, index=True)
    barcode = Column(String, unique=True, index=True, nullable=True)  # باركود الرخصة
    public_edit_token = Column(String, index=True, nullable=True)  # توكن سري لتعديل البيانات العامة عبر QR
    license_type = Column(SQLEnum(LicenseType), nullable=False)
    # أنواع الرخص (جدول جديد) + فئة A/B اختيارية
    license_type_id = Column(Integer, ForeignKey("license_types.id"), nullable=True)
    license_category = Column(String, nullable=True)  # مثال: A أو B
    issued_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    full_name = Column(String, nullable=False)
    birth_date = Column(Date, nullable=False)  # تاريخ الميلاد
    age = Column(Integer, nullable=False)
    gender = Column(SQLEnum(Gender), nullable=False)
    passport_number = Column(String, nullable=False)
    nationality = Column(String, nullable=False)
    blood_type = Column(SQLEnum(BloodType), nullable=False)
    email = Column(String, nullable=True)
    photo_path = Column(String, nullable=True)  # مسار الصورة الشخصية
    residence_certificate_path = Column(String, nullable=True)  # شهادة الإقامة
    birth_certificate_path = Column(String, nullable=True)  # شهادة الميلاد
    passport_image_path = Column(String, nullable=True)  # صورة جواز السفر
    status = Column(SQLEnum(LicenseStatus), default=LicenseStatus.PENDING, nullable=False)
    application_date = Column(DateTime, server_default=func.now(), nullable=False)
    exam_date = Column(DateTime, nullable=True)
    exam_result = Column(String, nullable=True)
    exam_score = Column(Integer, nullable=True)
    review_date = Column(DateTime, nullable=True)
    review_notes = Column(Text, nullable=True)
    issued_date = Column(DateTime, nullable=True)
    expiry_date = Column(Date, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # ===== Department head signature/approval flow =====
    # After passing exams, the license exists but shouldn't be printable until approved/signed by department head.
    dept_approval_requested = Column(Integer, nullable=True, default=0)  # 0/1
    dept_approval_requested_at = Column(DateTime, nullable=True)
    dept_approval_requested_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    dept_approval_approved = Column(Integer, nullable=True, default=0)  # 0/1
    dept_approval_approved_at = Column(DateTime, nullable=True)
    dept_approval_approved_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    dept_approval_notes = Column(Text, nullable=True)
    signature_image_path = Column(String, nullable=True)  # مسار صورة التوقيع الحقيقي

    # معلومات عامة يمكن للمواطن إضافتها بعد إصدار الرخصة
    chronic_disease = Column(Text, nullable=True)  # هل لديه مرض مزمن / تفاصيله
    emergency_contact_name = Column(String, nullable=True)  # اسم أقرب شخص
    emergency_contact_phone = Column(String, nullable=True)  # رقم أقرب شخص

    # حقول مطلوبة للطباعة (واجهة الرخصة)
    place_of_birth = Column(String, nullable=True)  # مكان الميلاد
    residence_address = Column(String, nullable=True)  # محل الإقامة
    
    user = relationship("User", foreign_keys=[user_id], back_populates="licenses")
    exams = relationship("Exam", back_populates="license")
    violations = relationship("Violation", back_populates="license")

    # relationship إلى جدول license_types (اختياري)
    license_type_ref = relationship("LicenseType", back_populates="licenses", lazy="selectin")
    issued_by_user = relationship(
        "User",
        foreign_keys=[issued_by_user_id],
        back_populates="issued_licenses",
        lazy="selectin",
    )

    dept_approval_requested_by_user = relationship(
        "User",
        foreign_keys=[dept_approval_requested_by_user_id],
        lazy="selectin",
    )
    dept_approval_approved_by_user = relationship(
        "User",
        foreign_keys=[dept_approval_approved_by_user_id],
        lazy="selectin",
    )

    @property
    def user_national_id(self) -> str | None:
        """الرقم الوطني الحقيقي للمواطن (من جدول المستخدمين)."""
        try:
            return self.user.national_id if self.user else None
        except Exception:
            return None

    @property
    def license_type_name(self) -> str | None:
        try:
            return self.license_type_ref.name if self.license_type_ref else None
        except Exception:
            return None

    @property
    def license_degree_order(self) -> int | None:
        try:
            return int(self.license_type_ref.degree_order) if self.license_type_ref else None
        except Exception:
            return None

    @property
    def license_top_color(self) -> str | None:
        try:
            return self.license_type_ref.top_color if self.license_type_ref else None
        except Exception:
            return None

    @property
    def license_validity_years(self) -> int | None:
        try:
            return int(self.license_type_ref.validity_years) if self.license_type_ref else None
        except Exception:
            return None

    @property
    def license_allowed_vehicles(self) -> str | None:
        """
        وصف المركبات المسموحة:
        - إذا كان النوع يحتوي فئات (A/B) نأخذ وصف الفئة المختارة
        - غير ذلك نأخذ allowed_vehicles من النوع
        """
        try:
            lt = self.license_type_ref
            if not lt:
                return None
            if getattr(lt, "has_categories", False) and self.license_category:
                code = str(self.license_category).strip().upper()
                for c in getattr(lt, "categories", []) or []:
                    if str(getattr(c, "code", "")).strip().upper() == code:
                        return getattr(c, "allowed_vehicles", None) or getattr(c, "label", None)
            return getattr(lt, "allowed_vehicles", None)
        except Exception:
            return None

    @property
    def issued_by_national_id(self) -> str | None:
        try:
            return self.issued_by_user.national_id if self.issued_by_user else None
        except Exception:
            return None



