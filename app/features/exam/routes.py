from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.features.user.model import User
from app.models.enums import UserRole
from app.features.exam.schema import ExamResponse, ExamCreate, ExamResult, ExamSchedule
from app.features.exam.service import ExamService

router = APIRouter()

@router.post("/create", response_model=ExamResponse, status_code=status.HTTP_201_CREATED)
def create_exam(
    exam_data: ExamCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.LICENSE_OFFICER]))
):
    """إنشاء امتحان جديد"""
    exam = ExamService.create_exam(db, exam_data, current_user.id)
    return exam

@router.get("/my-exams", response_model=List[ExamResponse])
def get_my_exams(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """الحصول على جميع امتحانات المستخدم الحالي"""
    exams = ExamService.get_user_exams(db, current_user.id)
    return exams

@router.get("/pending/list", response_model=List[ExamResponse])
def get_pending_exams(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.LICENSE_OFFICER]))
):
    """الحصول على الامتحانات المعلقة"""
    exams = ExamService.get_pending_exams(db)
    return exams

@router.post("/{exam_id}/schedule", response_model=ExamResponse)
def schedule_exam(
    exam_id: int,
    schedule_data: ExamSchedule,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.LICENSE_OFFICER]))
):
    """تحديد موعد الامتحان - فقط لمسؤول الرخص"""
    # حماية إضافية: التأكد من أن المستخدم ليس مواطن
    if current_user.role == UserRole.CITIZEN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ليس لديك صلاحية لتحديد موعد امتحان. فقط مسؤول الرخص يمكنه تحديد المواعيد."
        )
    
    exam = ExamService.schedule_exam(db, exam_id, schedule_data, current_user.id, current_user.role.value)
    if not exam:
        raise HTTPException(status_code=404, detail="الامتحان غير موجود")
    return exam

@router.post("/{exam_id}/result", response_model=ExamResponse)
def submit_exam_result(
    exam_id: int,
    result_data: ExamResult,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.LICENSE_OFFICER]))
):
    """تسجيل نتيجة الامتحان"""
    exam = ExamService.submit_exam_result(db, exam_id, result_data, current_user.id)
    if not exam:
        raise HTTPException(status_code=404, detail="الامتحان غير موجود")
    return exam

@router.get("/{exam_id}", response_model=ExamResponse)
def get_exam(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """الحصول على امتحان"""
    exam = ExamService.get_exam_by_id(db, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="الامتحان غير موجود")
    
    if current_user.role == UserRole.CITIZEN and exam.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="ليس لديك صلاحية للوصول")
    
    return exam

