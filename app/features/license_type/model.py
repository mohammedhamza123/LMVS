from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class LicenseType(Base):
    __tablename__ = "license_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)

    # ترتيب/درجة النوع (1 = الدرجة الأولى ... الخ)
    degree_order = Column(Integer, nullable=False, default=1)

    # صلاحية الرخصة بالسنوات
    validity_years = Column(Integer, nullable=False, default=10)

    # لون الشريط العلوي عند الطباعة/العرض (Hex)
    top_color = Column(String, nullable=False, default="#facc15")  # أصفر

    # في حال النوع يحتوي تفرع فئات (A/B)
    has_categories = Column(Boolean, nullable=False, default=False)

    # وصف عام للمركبات المسموحة (إذا لا يوجد فئات)
    allowed_vehicles = Column(Text, nullable=True)

    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    categories = relationship(
        "LicenseTypeCategory",
        back_populates="license_type",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    licenses = relationship("License", back_populates="license_type_ref")


class LicenseTypeCategory(Base):
    __tablename__ = "license_type_categories"

    id = Column(Integer, primary_key=True, index=True)
    license_type_id = Column(Integer, ForeignKey("license_types.id"), nullable=False, index=True)

    # مثال: A / B
    code = Column(String, nullable=False)

    # اسم الفئة المعروض (اختياري)
    label = Column(String, nullable=True)

    # وصف المركبات المسموحة داخل هذه الفئة
    allowed_vehicles = Column(Text, nullable=True)

    license_type = relationship("LicenseType", back_populates="categories")
































