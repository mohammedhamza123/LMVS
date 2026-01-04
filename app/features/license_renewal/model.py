from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Enum as SQLEnum, Text, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from decimal import Decimal

from app.core.database import Base
from app.models.enums import LicenseRenewalStatus


class LicenseRenewal(Base):
    __tablename__ = "license_renewals"

    id = Column(Integer, primary_key=True, index=True)
    tracking_code = Column(String, unique=True, index=True, nullable=False)

    license_id = Column(Integer, ForeignKey("licenses.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # صورة جديدة مطلوبة لتحديث الرخصة
    new_photo_path = Column(String, nullable=False)

    status = Column(SQLEnum(LicenseRenewalStatus), default=LicenseRenewalStatus.PENDING, nullable=False)

    # يقوم مسؤول الرخص بتأكيد الدفع قبل الاعتماد
    payment_confirmed = Column(Boolean, default=False, nullable=False)

    officer_notes = Column(Text, nullable=True)
    citizen_notes = Column(Text, nullable=True)

    requested_at = Column(DateTime, server_default=func.now(), nullable=False)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # snapshot fields (اختياري لعرض سريع بدون join)
    old_expiry_date = Column(DateTime, nullable=True)
    
    # امتحان النظر
    vision_exam_date = Column(DateTime, nullable=True)  # موعد امتحان النظر
    vision_exam_result = Column(String, nullable=True)  # نتيجة امتحان النظر: 'passed' أو 'failed'
    vision_exam_conducted_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # من أجرى الامتحان
    
    # سعر التجديد
    renewal_fee = Column(Numeric(10, 2), nullable=True, default=Decimal('8.50'))  # سعر التجديد (8.5 دينار)

    license = relationship("License", lazy="selectin")
    user = relationship("User", foreign_keys=[user_id], lazy="selectin")
    reviewed_by_user = relationship("User", foreign_keys=[reviewed_by_user_id], lazy="selectin")
    vision_exam_conducted_by = relationship("User", foreign_keys=[vision_exam_conducted_by_user_id], lazy="selectin")

















