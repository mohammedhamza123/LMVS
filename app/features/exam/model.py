from sqlalchemy import Column, Integer, DateTime, ForeignKey, String, Text, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Exam(Base):
    __tablename__ = "exams"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    license_id = Column(Integer, ForeignKey("licenses.id"), nullable=True)
    exam_type_id = Column(Integer, ForeignKey("exam_types.id"), nullable=True)
    scheduled_date = Column(DateTime, nullable=True)  # موعد الامتحان المحدد
    exam_date = Column(DateTime, nullable=True)  # تاريخ إجراء الامتحان الفعلي
    score = Column(Integer, nullable=True)
    result = Column(String, nullable=True)  # passed, failed, pending
    notes = Column(Text, nullable=True)
    conducted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    scheduled_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    # حقول الدفع
    paid_at = Column(DateTime, nullable=True)  # تاريخ الدفع
    paid_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # من سجل الدفع
    paid_amount = Column(Numeric(10, 2), nullable=True)  # المبلغ المدفوع
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    
    user = relationship("User", foreign_keys=[user_id], back_populates="exams")
    license = relationship("License", back_populates="exams")
    examiner = relationship("User", foreign_keys=[conducted_by])
    creator = relationship("User", foreign_keys=[created_by_user_id])
    scheduler = relationship("User", foreign_keys=[scheduled_by_user_id])
    paid_by_user = relationship("User", foreign_keys=[paid_by_user_id])
    exam_type = relationship("ExamType")

    @property
    def conducted_by_national_id(self) -> str | None:
        try:
            return self.examiner.national_id if self.examiner else None
        except Exception:
            return None

    @property
    def scheduled_by_national_id(self) -> str | None:
        try:
            return self.scheduler.national_id if self.scheduler else None
        except Exception:
            return None

    @property
    def created_by_national_id(self) -> str | None:
        try:
            return self.creator.national_id if self.creator else None
        except Exception:
            return None

