from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional, List
from app.features.license_type.model import LicenseType, LicenseTypeCategory
from app.features.license_type.schema import (
    LicenseTypeCreate,
    LicenseTypeUpdate,
    LicenseTypeCategoryCreate,
    LicenseTypeCategoryUpdate,
)


class LicenseTypeService:
    @staticmethod
    def list_license_types(db: Session, include_inactive: bool = False) -> List[LicenseType]:
        q = db.query(LicenseType)
        if not include_inactive:
            q = q.filter(LicenseType.is_active == True)
        return q.order_by(LicenseType.degree_order.asc(), LicenseType.id.asc()).all()

    @staticmethod
    def get_license_type(db: Session, license_type_id: int) -> Optional[LicenseType]:
        return db.query(LicenseType).filter(LicenseType.id == license_type_id).first()

    @staticmethod
    def create_license_type(db: Session, data: LicenseTypeCreate) -> LicenseType:
        lt = LicenseType(
            name=data.name,
            degree_order=data.degree_order,
            validity_years=data.validity_years,
            top_color=data.top_color,
            has_categories=data.has_categories,
            allowed_vehicles=data.allowed_vehicles,
            is_active=data.is_active,
        )
        if data.categories:
            lt.has_categories = True
            for c in data.categories:
                lt.categories.append(
                    LicenseTypeCategory(
                        code=c.code.strip().upper(),
                        label=c.label,
                        allowed_vehicles=c.allowed_vehicles,
                    )
                )

        db.add(lt)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise ValueError("اسم نوع الرخصة موجود بالفعل")
        db.refresh(lt)
        return lt

    @staticmethod
    def update_license_type(db: Session, license_type_id: int, data: LicenseTypeUpdate) -> Optional[LicenseType]:
        lt = db.query(LicenseType).filter(LicenseType.id == license_type_id).first()
        if not lt:
            return None

        update_data = data.dict(exclude_unset=True)
        for k, v in update_data.items():
            setattr(lt, k, v)

        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise ValueError("اسم نوع الرخصة موجود بالفعل")
        db.refresh(lt)
        return lt

    @staticmethod
    def delete_license_type(db: Session, license_type_id: int) -> bool:
        lt = db.query(LicenseType).filter(LicenseType.id == license_type_id).first()
        if not lt:
            return False
        db.delete(lt)
        db.commit()
        return True

    # ===== Categories =====

    @staticmethod
    def add_category(db: Session, license_type_id: int, data: LicenseTypeCategoryCreate) -> Optional[LicenseTypeCategory]:
        lt = db.query(LicenseType).filter(LicenseType.id == license_type_id).first()
        if not lt:
            return None
        lt.has_categories = True
        cat = LicenseTypeCategory(
            license_type_id=license_type_id,
            code=data.code.strip().upper(),
            label=data.label,
            allowed_vehicles=data.allowed_vehicles,
        )
        db.add(cat)
        db.commit()
        db.refresh(cat)
        return cat

    @staticmethod
    def update_category(
        db: Session, license_type_id: int, category_id: int, data: LicenseTypeCategoryUpdate
    ) -> Optional[LicenseTypeCategory]:
        cat = (
            db.query(LicenseTypeCategory)
            .filter(LicenseTypeCategory.id == category_id, LicenseTypeCategory.license_type_id == license_type_id)
            .first()
        )
        if not cat:
            return None
        update_data = data.dict(exclude_unset=True)
        for k, v in update_data.items():
            setattr(cat, k, v)
        db.commit()
        db.refresh(cat)
        return cat

    @staticmethod
    def delete_category(db: Session, license_type_id: int, category_id: int) -> bool:
        cat = (
            db.query(LicenseTypeCategory)
            .filter(LicenseTypeCategory.id == category_id, LicenseTypeCategory.license_type_id == license_type_id)
            .first()
        )
        if not cat:
            return False
        db.delete(cat)
        db.commit()
        return True
































