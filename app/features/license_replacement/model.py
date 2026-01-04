from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Enum as SQLEnum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.enums import LicenseRenewalStatus


class LicenseReplacement(Base):
    """
    طلب بدل فاقد.
    نستخدم LicenseRenewalStatus كحالات عامة (pending/approved/rejected) لتفادي إضافة Enum جديد.
    """

    __tablename__ = "license_replacements"

    id = Column(Integer, primary_key=True, index=True)
    tracking_code = Column(String, unique=True, index=True, nullable=False)
    payment_code = Column(String, unique=True, index=True, nullable=False)

    license_id = Column(Integer, ForeignKey("licenses.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    police_report_path = Column(String, nullable=False)  # بلاغ فقد إلزامي (uploads/documents/...)

    status = Column(SQLEnum(LicenseRenewalStatus), default=LicenseRenewalStatus.PENDING, nullable=False)
    payment_confirmed = Column(Boolean, default=False, nullable=False)

    citizen_notes = Column(Text, nullable=True)
    officer_notes = Column(Text, nullable=True)

    requested_at = Column(DateTime, server_default=func.now(), nullable=False)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Evidence that old license card was invalidated:
    old_barcode = Column(String, nullable=True)
    new_barcode = Column(String, nullable=True)

    license = relationship("License", lazy="selectin")
    user = relationship("User", foreign_keys=[user_id], lazy="selectin")
    reviewed_by_user = relationship("User", foreign_keys=[reviewed_by_user_id], lazy="selectin")


