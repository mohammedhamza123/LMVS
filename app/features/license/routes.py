from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
import os
import uuid
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.features.user.model import User
from app.models.enums import UserRole, LicenseStatus
from app.features.license.model import License
from app.features.license.schema import (
    LicenseResponse,
    LicenseReview,
    LicenseCreate,
    LicenseExamSchedule,
    LicenseExamScheduleBundle,
    LicenseImportantInfoUpdate,
)
from app.features.license.service import LicenseService
from app.features.exam.service import ExamService
from app.features.exam.schema import ExamResponse, ExamCreate, ExamSchedule, ExamResult
from app.features.exam_type.model import ExamType
from app.features.license_type.schema import LicenseTypeResponse
from app.features.license_type.service import LicenseTypeService

router = APIRouter()

# مجلد حفظ الصور
UPLOAD_DIR = "uploads/photos"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/apply", response_model=LicenseResponse, status_code=status.HTTP_201_CREATED)
def apply_for_license(
    license_data: LicenseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """تقديم طلب رخصة جديد"""
    try:
        license = LicenseService.create_license_application(db, current_user.id, license_data)
        return license
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/saved-data", response_model=dict)
def get_saved_license_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """الحصول على البيانات المحفوظة من الرخصة المقبولة/الصادرة للمواطن"""
    # البحث عن رخصة مقبولة أولاً (APPROVED) - البيانات الرسمية بعد قبول مسؤول الرخص
    saved_license = db.query(License).filter(
        License.user_id == current_user.id,
        License.status == LicenseStatus.APPROVED
    ).order_by(License.review_date.desc().nullslast(), License.application_date.desc()).first()
    
    # إذا لم توجد رخصة مقبولة، نبحث عن رخصة صادرة
    if not saved_license:
        saved_license = db.query(License).filter(
            License.user_id == current_user.id,
            License.status == LicenseStatus.ISSUED
        ).order_by(License.issued_date.desc().nullslast(), License.application_date.desc()).first()
    
    if not saved_license:
        return {
            "has_saved_data": False,
            "data": None
        }
    
    return {
        "has_saved_data": True,
        "data": {
            "full_name": saved_license.full_name,
            "birth_date": saved_license.birth_date.isoformat() if saved_license.birth_date else None,
            "gender": saved_license.gender.value if saved_license.gender else None,
            "passport_number": saved_license.passport_number,
            "nationality": saved_license.nationality,
            "blood_type": saved_license.blood_type.value if saved_license.blood_type else None,
            "place_of_birth": saved_license.place_of_birth,
            "residence_address": saved_license.residence_address,
            "email": saved_license.email,
            "photo_path": saved_license.photo_path,
        }
    }

@router.get("/my-licenses", response_model=List[LicenseResponse])
def get_my_licenses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """الحصول على جميع رخص المستخدم الحالي"""
    licenses = LicenseService.get_user_licenses(db, current_user.id)
    return licenses


@router.get("/license-types", response_model=List[LicenseTypeResponse])
def list_license_types_for_citizen(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    قائمة أنواع الرخص (من الجدول) لاستخدامها في تطبيق المواطن عند تقديم الطلب.
    """
    return LicenseTypeService.list_license_types(db, include_inactive=False)

@router.get("/{license_id}", response_model=LicenseResponse)
def get_license(
    license_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """الحصول على رخصة"""
    license = LicenseService.get_license_by_id(db, license_id)
    if not license:
        raise HTTPException(status_code=404, detail="الرخصة غير موجودة")
    
    if current_user.role == UserRole.CITIZEN and license.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="ليس لديك صلاحية للوصول")
    
    return license

@router.get("/pending/list", response_model=List[LicenseResponse])
def get_pending_licenses(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.LICENSE_OFFICER]))
):
    """الحصول على طلبات الرخص المعلقة"""
    licenses = LicenseService.get_pending_licenses(db)
    return licenses

@router.post("/{license_id}/review", response_model=LicenseResponse)
def review_license(
    license_id: int,
    review_data: LicenseReview,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.LICENSE_OFFICER]))
):
    """مراجعة طلب رخصة"""
    try:
        license = LicenseService.review_license(db, license_id, review_data, actor_user_id=current_user.id)
        if not license:
            raise HTTPException(status_code=404, detail="الرخصة غير موجودة")
        return license
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# ========== Endpoints لمسؤول الرخص ==========

@router.get("/officer/all", response_model=List[LicenseResponse])
def get_all_licenses_for_officer(
    license_type: Optional[str] = Query(None, description="نوع الرخصة"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.LICENSE_OFFICER]))
):
    """الحصول على جميع طلبات الرخص لمسؤول الرخص (مصنفة حسب النوع)"""
    licenses = LicenseService.get_all_licenses_for_officer(db, license_type)
    return licenses


@router.get("/officer/printable", response_model=List[LicenseResponse])
def get_printable_licenses_for_officer(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.LICENSE_OFFICER]))
):
    """الرخص القابلة للطباعة (الرخص الصادرة فقط بعد اجتياز 3 امتحانات)"""
    return LicenseService.get_printable_licenses_for_officer(db)


@router.get("/officer/dept-approval/queue", response_model=List[LicenseResponse])
def get_dept_approval_queue_for_officer(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.LICENSE_OFFICER])),
):
    """
    الرخص التي اجتازت الامتحانات (تم إصدارها) لكنها بانتظار ترحيلها لاعتماد/توقيع رئيس القسم.
    تظهر مباشرة بعد النجاح (ISSUED) لكن قبل الترحيل.
    """
    from app.features.license.model import License
    rows = (
        db.query(License)
        .filter(
            License.status == LicenseStatus.ISSUED,
            (License.dept_approval_requested == 0) | (License.dept_approval_requested == None),
            (License.dept_approval_approved == 0) | (License.dept_approval_approved == None),
        )
        .order_by(License.issued_date.desc().nullslast(), License.application_date.desc())
        .all()
    )
    return rows


@router.post("/officer/dept-approval/{license_id}/submit", response_model=LicenseResponse)
def submit_license_for_dept_approval(
    license_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.LICENSE_OFFICER])),
):
    """ترحيل الرخصة لاعتماد/توقيع رئيس القسم."""
    from datetime import datetime
    from app.features.license.model import License

    lic = db.query(License).filter(License.id == license_id).first()
    if not lic:
        raise HTTPException(status_code=404, detail="الرخصة غير موجودة")
    if lic.status != LicenseStatus.ISSUED:
        raise HTTPException(status_code=400, detail="لا يمكن ترحيل هذه الرخصة حالياً")
    if (lic.dept_approval_approved or 0) == 1:
        raise HTTPException(status_code=400, detail="هذه الرخصة تم اعتمادها بالفعل")
    if (lic.dept_approval_requested or 0) == 1:
        raise HTTPException(status_code=400, detail="هذه الرخصة تم ترحيلها بالفعل")

    lic.dept_approval_requested = 1
    lic.dept_approval_requested_at = datetime.now()
    lic.dept_approval_requested_by_user_id = current_user.id
    db.commit()
    db.refresh(lic)
    return lic

@router.get("/{license_id}/exams", response_model=List[ExamResponse])
def get_license_exams(
    license_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.LICENSE_OFFICER]))
):
    """الحصول على جميع امتحانات الرخصة"""
    license = LicenseService.get_license_by_id(db, license_id)
    if not license:
        raise HTTPException(status_code=404, detail="الرخصة غير موجودة")
    
    exams = ExamService.get_license_exams(db, license_id)
    return exams

@router.post("/{license_id}/exams/schedule", response_model=ExamResponse)
def schedule_exam_for_license(
    license_id: int,
    data: LicenseExamSchedule,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.LICENSE_OFFICER]))
):
    """تحديد موعد امتحان للرخصة - فقط لمسؤول الرخص"""
    # حماية إضافية: التأكد من أن المستخدم ليس مواطن
    if current_user.role == UserRole.CITIZEN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ليس لديك صلاحية لتحديد موعد امتحان. فقط مسؤولي الرخص والامتحانات يمكنهم تحديد المواعيد."
        )
    
    license = LicenseService.get_license_by_id(db, license_id)
    if not license:
        raise HTTPException(status_code=404, detail="الرخصة غير موجودة")

    # لا يسمح بجدولة الامتحانات قبل الموافقة على الطلب
    if license.status not in [LicenseStatus.APPROVED, LicenseStatus.EXAM_PASSED, LicenseStatus.EXAM_FAILED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="لا يمكن جدولة الامتحانات قبل الموافقة على الطلب"
        )
    
    exam_data = ExamCreate(
        user_id=data.user_id or license.user_id,
        license_id=license_id,
        exam_type_id=data.exam_type_id
    )
    schedule_data = ExamSchedule(scheduled_date=data.scheduled_date)
    
    # إنشاء امتحان جديد
    exam = ExamService.create_exam(db, exam_data, current_user.id)
    
    # تحديد الموعد
    exam = ExamService.schedule_exam(db, exam.id, schedule_data, current_user.id, current_user.role.value)
    
    return exam


@router.post("/{license_id}/exams/schedule-bundle", response_model=List[ExamResponse])
def schedule_exams_bundle_for_license(
    license_id: int,
    data: LicenseExamScheduleBundle,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.LICENSE_OFFICER]))
):
    """جدولة عدة امتحانات (مثل الثلاثة) مرة واحدة"""
    # حماية إضافية: التأكد من أن المستخدم ليس مواطن
    if current_user.role == UserRole.CITIZEN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ليس لديك صلاحية لتحديد موعد امتحان. فقط مسؤولي الرخص والامتحانات يمكنهم تحديد المواعيد."
        )

    license = LicenseService.get_license_by_id(db, license_id)
    if not license:
        raise HTTPException(status_code=404, detail="الرخصة غير موجودة")

    # لا يسمح بجدولة الامتحانات قبل الموافقة على الطلب
    if license.status not in [LicenseStatus.APPROVED, LicenseStatus.EXAM_PASSED, LicenseStatus.EXAM_FAILED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="لا يمكن جدولة الامتحانات قبل الموافقة على الطلب"
        )

    from app.features.exam.model import Exam

    results: list[Exam] = []
    for item in data.exams:
        existing = (
            db.query(Exam)
            .filter(Exam.license_id == license_id, Exam.exam_type_id == item.exam_type_id)
            .order_by(Exam.created_at.desc())
            .first()
        )
        if existing:
            exam = existing
        else:
            exam_data = ExamCreate(
                user_id=data.user_id or license.user_id,
                license_id=license_id,
                exam_type_id=item.exam_type_id
            )
            exam = ExamService.create_exam(db, exam_data, current_user.id)

        schedule_data = ExamSchedule(scheduled_date=item.scheduled_date)
        exam = ExamService.schedule_exam(db, exam.id, schedule_data, current_user.id, current_user.role.value)
        results.append(exam)

    return results

@router.post("/exams/{exam_id}/schedule", response_model=ExamResponse)
def schedule_existing_exam(
    exam_id: int,
    schedule_data: ExamSchedule,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.LICENSE_OFFICER]))
):
    """تحديد موعد امتحان موجود - فقط لمسؤول الرخص"""
    # حماية إضافية: التأكد من أن المستخدم ليس مواطن
    if current_user.role == UserRole.CITIZEN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ليس لديك صلاحية لتحديد موعد امتحان. فقط مسؤولي الرخص والامتحانات يمكنهم تحديد المواعيد."
        )
    
    # تأكد أن الامتحان مرتبط بطلب موافق عليه قبل الجدولة
    db_exam = ExamService.get_exam_by_id(db, exam_id)
    if not db_exam:
        raise HTTPException(status_code=404, detail="الامتحان غير موجود")
    if db_exam.license_id:
        db_license = LicenseService.get_license_by_id(db, db_exam.license_id)
        if db_license and db_license.status not in [LicenseStatus.APPROVED, LicenseStatus.EXAM_PASSED, LicenseStatus.EXAM_FAILED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="لا يمكن جدولة الامتحانات قبل الموافقة على الطلب"
            )

    exam = ExamService.schedule_exam(db, exam_id, schedule_data, current_user.id, current_user.role.value)
    if not exam:
        raise HTTPException(status_code=404, detail="الامتحان غير موجود")
    return exam

@router.post("/exams/{exam_id}/result", response_model=ExamResponse)
def submit_exam_result_for_license(
    exam_id: int,
    result_data: ExamResult,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.LICENSE_OFFICER]))
):
    """إدخال نتيجة امتحان"""
    exam = ExamService.submit_exam_result(db, exam_id, result_data, current_user.id)
    if not exam:
        raise HTTPException(status_code=404, detail="الامتحان غير موجود")
    return exam

@router.get("/exam-types/list")
def get_exam_types(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.LICENSE_OFFICER]))
):
    """الحصول على أنواع الامتحانات"""
    exam_types = db.query(ExamType).filter(ExamType.is_active == True).all()
    return exam_types

@router.post("/upload-photo")
async def upload_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """رفع صورة شخصية"""
    # التحقق من نوع الملف
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="يجب أن يكون الملف صورة")
    
    # إنشاء اسم ملف فريد
    file_ext = os.path.splitext(file.filename)[1] if file.filename else '.jpg'
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    # حفظ الملف
    try:
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"فشل حفظ الملف: {str(e)}")
    
    return JSONResponse(content={"path": f"uploads/photos/{unique_filename}"})

@router.post("/upload-document")
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """رفع وثيقة (شهادة إقامة، شهادة ميلاد، صورة جواز)"""
    # التحقق من نوع الملف (صورة أو PDF)
    allowed_types = ['image/', 'application/pdf']
    if not file.content_type or not any(file.content_type.startswith(t) for t in allowed_types):
        raise HTTPException(status_code=400, detail="يجب أن يكون الملف صورة أو PDF")
    
    # إنشاء مجلد للوثائق
    documents_dir = "uploads/documents"
    os.makedirs(documents_dir, exist_ok=True)
    
    # إنشاء اسم ملف فريد
    file_ext = os.path.splitext(file.filename)[1] if file.filename else '.pdf'
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(documents_dir, unique_filename)
    
    # حفظ الملف
    try:
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"فشل حفظ الملف: {str(e)}")
    
    return JSONResponse(content={"path": f"uploads/documents/{unique_filename}"})

# ========== فحص الرخصة بالباركود (بدون تسجيل دخول) ==========

@router.get("/by-barcode/{barcode}", response_model=LicenseResponse)
def get_license_by_barcode_for_officer(
    barcode: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.TRAFFIC_POLICE, UserRole.VIOLATION_OFFICER, UserRole.LICENSE_OFFICER]))
):
    """الحصول على معلومات الرخصة بالباركود (لشرطي المرور ومسؤول المخالفات)"""
    license = LicenseService.get_license_by_barcode(db, barcode)
    if not license:
        raise HTTPException(status_code=404, detail="الرخصة غير موجودة")
    return license

@router.get("/verify/{barcode}")
def verify_license_by_barcode(
    barcode: str,
    db: Session = Depends(get_db)
):
    """فحص الرخصة بالباركود (بدون تسجيل دخول)"""
    license = LicenseService.get_license_by_barcode(db, barcode)
    
    if not license:
        raise HTTPException(status_code=404, detail="الرخصة غير موجودة")
    
    if license.status not in [LicenseStatus.ISSUED, LicenseStatus.EXPIRED]:
        raise HTTPException(status_code=400, detail="الرخصة غير صالحة")
    
    # التحقق من انتهاء الرخصة
    today = date.today()
    is_expired = license.expiry_date and license.expiry_date < today
    
    # الحصول على المخالفات
    from app.features.violation.model import Violation
    from app.models.enums import ViolationStatus
    violations = db.query(Violation).filter(
        Violation.license_id == license.id,
        Violation.status.in_([ViolationStatus.PENDING, ViolationStatus.APPEALED])
    ).all()
    
    return {
        "license": {
            "license_number": license.license_number,
            "full_name": license.full_name,
            "license_type": license.license_type,
            "issued_date": license.issued_date,
            "expiry_date": license.expiry_date,
            "is_expired": is_expired,
            "status": license.status,
            "chronic_disease": getattr(license, "chronic_disease", None),
            "emergency_contact_name": getattr(license, "emergency_contact_name", None),
            "emergency_contact_phone": getattr(license, "emergency_contact_phone", None),
        },
        "violations": [
            {
                "violation_number": v.violation_number,
                "violation_type": v.violation_type,
                "description": v.description,
                "violation_date": v.violation_date,
                "fine_amount": v.fine_amount,
                "status": v.status
            }
            for v in violations
        ],
        "has_violations": len(violations) > 0,
        "violations_count": len(violations)
    }


@router.put("/{license_id}/important-info", response_model=LicenseResponse)
def update_license_important_info(
    license_id: int,
    data: LicenseImportantInfoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """تحديث المعلومات المهمة عبر تطبيق المواطن بعد إصدار الرخصة (يتطلب تسجيل دخول)."""
    license = LicenseService.get_license_by_id(db, license_id)
    if not license:
        raise HTTPException(status_code=404, detail="الرخصة غير موجودة")

    if current_user.role != UserRole.CITIZEN or license.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="ليس لديك صلاحية للتعديل")

    if license.status != LicenseStatus.ISSUED:
        raise HTTPException(status_code=400, detail="لا يمكن تعديل هذه المعلومات قبل إصدار الرخصة")

    if data.chronic_disease is not None:
        license.chronic_disease = data.chronic_disease.strip() or None
    if data.emergency_contact_name is not None:
        license.emergency_contact_name = data.emergency_contact_name.strip() or None
    if data.emergency_contact_phone is not None:
        license.emergency_contact_phone = data.emergency_contact_phone.strip() or None

    db.commit()
    db.refresh(license)
    return license

