from sqlalchemy import Column, Integer, String, Enum as SQLEnum, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.models.enums import UserRole

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    national_id = Column(String, unique=True, index=True, nullable=True)
    username = Column(String, unique=True, index=True, nullable=True)
    phone = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.CITIZEN, nullable=False)
    is_active = Column(Boolean, default=True)
    suspended_until = Column(DateTime, nullable=True)
    suspension_reason = Column(Text, nullable=True)
    fcm_token = Column(String, nullable=True)  # Firebase Cloud Messaging token
    
    # العلاقات
    licenses = relationship("License", foreign_keys="License.user_id", back_populates="user")
    issued_licenses = relationship(
        "License",
        foreign_keys="License.issued_by_user_id",
        back_populates="issued_by_user",
    )
    violations = relationship("Violation", foreign_keys="[Violation.user_id]", back_populates="user")
    exams = relationship("Exam", foreign_keys="[Exam.user_id]", back_populates="user")

















