from sqlalchemy.orm import Session
from app.features.violation_type.model import ViolationType
from app.features.violation_type.schema import ViolationTypeCreate, ViolationTypeUpdate
from typing import Optional, List


class ViolationTypeService:
    @staticmethod
    def create_violation_type(db: Session, data: ViolationTypeCreate) -> ViolationType:
        existing = db.query(ViolationType).filter(ViolationType.name == data.name).first()
        if existing:
            raise ValueError("نوع المخالفة موجود بالفعل")

        vt = ViolationType(
            name=data.name,
            description=data.description,
            fine_amount=data.fine_amount,
            is_active=data.is_active,
        )
        db.add(vt)
        db.commit()
        db.refresh(vt)
        return vt

    @staticmethod
    def get_violation_type_by_id(db: Session, violation_type_id: int) -> Optional[ViolationType]:
        return db.query(ViolationType).filter(ViolationType.id == violation_type_id).first()

    @staticmethod
    def get_all_violation_types(db: Session, include_inactive: bool = False) -> List[ViolationType]:
        query = db.query(ViolationType)
        if not include_inactive:
            query = query.filter(ViolationType.is_active == True)
        return query.all()

    @staticmethod
    def update_violation_type(
        db: Session, violation_type_id: int, data: ViolationTypeUpdate
    ) -> Optional[ViolationType]:
        vt = db.query(ViolationType).filter(ViolationType.id == violation_type_id).first()
        if not vt:
            return None

        if data.name and data.name != vt.name:
            existing = db.query(ViolationType).filter(
                ViolationType.name == data.name, ViolationType.id != violation_type_id
            ).first()
            if existing:
                raise ValueError("نوع المخالفة موجود بالفعل")

        update_data = data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(vt, field, value)

        db.commit()
        db.refresh(vt)
        return vt

    @staticmethod
    def delete_violation_type(db: Session, violation_type_id: int) -> bool:
        vt = db.query(ViolationType).filter(ViolationType.id == violation_type_id).first()
        if not vt:
            return False
        db.delete(vt)
        db.commit()
        return True



































