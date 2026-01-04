from sqlalchemy.orm import Session
from app.features.exam_type.model import ExamType
from app.features.exam_type.schema import ExamTypeCreate, ExamTypeUpdate
from typing import Optional, List

class ExamTypeService:
    @staticmethod
    def create_exam_type(db: Session, exam_type_data: ExamTypeCreate) -> ExamType:
        """إنشاء نوع امتحان جديد"""
        existing = db.query(ExamType).filter(ExamType.name == exam_type_data.name).first()
        if existing:
            raise ValueError("نوع الامتحان موجود بالفعل")
        
        db_exam_type = ExamType(
            name=exam_type_data.name,
            description=exam_type_data.description,
            passing_score=exam_type_data.passing_score,
            duration_minutes=exam_type_data.duration_minutes,
            price=exam_type_data.price,
            is_active=exam_type_data.is_active
        )
        db.add(db_exam_type)
        db.commit()
        db.refresh(db_exam_type)
        return db_exam_type
    
    @staticmethod
    def get_exam_type_by_id(db: Session, exam_type_id: int) -> Optional[ExamType]:
        """الحصول على نوع امتحان بالمعرف"""
        return db.query(ExamType).filter(ExamType.id == exam_type_id).first()
    
    @staticmethod
    def get_all_exam_types(db: Session, include_inactive: bool = False) -> List[ExamType]:
        """الحصول على جميع أنواع الامتحانات"""
        query = db.query(ExamType)
        if not include_inactive:
            query = query.filter(ExamType.is_active == True)
        return query.all()
    
    @staticmethod
    def update_exam_type(db: Session, exam_type_id: int, exam_type_data: ExamTypeUpdate) -> Optional[ExamType]:
        """تحديث نوع امتحان"""
        exam_type = db.query(ExamType).filter(ExamType.id == exam_type_id).first()
        if not exam_type:
            return None
        
        if exam_type_data.name and exam_type_data.name != exam_type.name:
            existing = db.query(ExamType).filter(
                ExamType.name == exam_type_data.name,
                ExamType.id != exam_type_id
            ).first()
            if existing:
                raise ValueError("نوع الامتحان موجود بالفعل")
        
        update_data = exam_type_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(exam_type, field, value)
        
        db.commit()
        db.refresh(exam_type)
        return exam_type
    
    @staticmethod
    def delete_exam_type(db: Session, exam_type_id: int) -> bool:
        """حذف نوع امتحان"""
        exam_type = db.query(ExamType).filter(ExamType.id == exam_type_id).first()
        if not exam_type:
            return False
        
        db.delete(exam_type)
        db.commit()
        return True




