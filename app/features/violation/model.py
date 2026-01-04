from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum, Numeric, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.models.enums import ViolationStatus

class Violation(Base):
    __tablename__ = "violations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    license_id = Column(Integer, ForeignKey("licenses.id"), nullable=True)
    violation_number = Column(String, unique=True, index=True, nullable=False)
    # الاسم النصي (يبقى للعرض/التوافق)، لكن العلاقة الحقيقية عبر violation_type_id
    violation_type_id = Column(Integer, ForeignKey("violation_types.id"), nullable=True, index=True)
    violation_type = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    location = Column(String, nullable=False)
    violation_date = Column(DateTime, nullable=False)
    fine_amount = Column(Numeric(10, 2), nullable=False)
    status = Column(SQLEnum(ViolationStatus), default=ViolationStatus.PENDING, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    paid_at = Column(DateTime, nullable=True)
    paid_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    appeal_reason = Column(Text, nullable=True)
    # حقول الإلغاء
    cancelled_at = Column(DateTime, nullable=True)
    cancelled_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    # حقول التعديل
    modified_at = Column(DateTime, nullable=True)
    modified_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    modification_reason = Column(Text, nullable=True)
    
    user = relationship("User", foreign_keys=[user_id], back_populates="violations")
    license = relationship("License", back_populates="violations")
    officer = relationship("User", foreign_keys=[created_by])
    paid_by_user = relationship("User", foreign_keys=[paid_by_user_id])
    cancelled_by_user = relationship("User", foreign_keys=[cancelled_by_user_id])
    modified_by_user = relationship("User", foreign_keys=[modified_by_user_id])
    violation_type_obj = relationship("ViolationType", back_populates="violations")














