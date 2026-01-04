from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.features.user.model import User
from app.features.user.schema import UserCreate, UserResponse, UserUpdate, UserSuspendRequest
from app.features.user.service import UserService
from app.features.exam_type.schema import ExamTypeCreate, ExamTypeUpdate, ExamTypeResponse
from app.features.exam_type.service import ExamTypeService
from app.features.violation_type.schema import (
    ViolationTypeCreate,
    ViolationTypeUpdate,
    ViolationTypeResponse,
)
from app.features.violation_type.service import ViolationTypeService
from app.features.license_type.schema import (
    LicenseTypeCreate,
    LicenseTypeUpdate,
    LicenseTypeResponse,
    LicenseTypeCategoryCreate,
    LicenseTypeCategoryUpdate,
    LicenseTypeCategoryResponse,
)
from app.features.license_type.service import LicenseTypeService
from app.features.admin.service import AdminService
from app.features.license.schema import LicenseResponse
from app.features.exam.schema import ExamResponse
from app.features.violation.schema import ViolationResponse
from app.models.enums import UserRole, LicenseStatus, ViolationStatus
from datetime import datetime, timedelta

router = APIRouter()

# ========== إدارة المستخدمين ==========

@router.get("/users", response_model=List[UserResponse])
def get_all_users_admin(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.SUPER_ADMIN]))
):
    """الحصول على جميع المستخدمين"""
    return db.query(User).all()

@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user_admin(
    user_data: UserCreate,
    role: UserRole,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.SUPER_ADMIN]))
):
    """إنشاء مستخدم جديد"""
    try:
        user = UserService.create_user(db, user_data, role=role)
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/users/{user_id}", response_model=UserResponse)
def update_user_admin(
    user_id: int,
    user_data: UserUpdate,
    role: Optional[UserRole] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.SUPER_ADMIN]))
):
    """تحديث مستخدم"""
    user = UserService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")
    
    updated_user = UserService.update_user(db, user_id, user_data)
    if role is not None:
        updated_user.role = role
        db.commit()
        db.refresh(updated_user)
    return updated_user

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_admin(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.SUPER_ADMIN]))
):
    """حذف مستخدم"""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="لا يمكنك حذف حسابك الخاص")
    
    user = UserService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")
    
    db.delete(user)
    db.commit()
    return None

@router.put("/users/{user_id}/toggle-active")
def toggle_user_active(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.SUPER_ADMIN]))
):
    """تفعيل/تعطيل مستخدم"""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="لا يمكنك تعطيل حسابك الخاص")
    
    user = UserService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")
    
    user.is_active = not user.is_active
    db.commit()
    db.refresh(user)
    return {"message": f"تم {'تفعيل' if user.is_active else 'تعطيل'} المستخدم بنجاح", "is_active": user.is_active}


@router.post("/users/{user_id}/suspend", response_model=UserResponse)
def suspend_user_temporarily(
    user_id: int,
    data: UserSuspendRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.SUPER_ADMIN])),
):
    """
    إيقاف مؤقت (يُستخدم لمسؤول الرخص/المخالفات حسب طلب النظام).
    """
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="لا يمكنك إيقاف حسابك")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")

    if user.role not in [UserRole.LICENSE_OFFICER, UserRole.VIOLATION_OFFICER]:
        raise HTTPException(status_code=400, detail="الإيقاف المؤقت متاح فقط لمسؤول الرخص ومسؤول المخالفات")

    minutes = max(1, int(data.minutes))
    user.suspended_until = datetime.now() + timedelta(minutes=minutes)
    user.suspension_reason = (data.reason.strip() if data.reason else None)
    db.commit()
    db.refresh(user)
    return user


@router.post("/users/{user_id}/unsuspend", response_model=UserResponse)
def unsuspend_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.SUPER_ADMIN])),
):
    """إلغاء الإيقاف المؤقت"""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="لا يمكنك تعديل حسابك بهذه الطريقة")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")

    user.suspended_until = None
    user.suspension_reason = None
    db.commit()
    db.refresh(user)
    return user

# ========== إدارة أنواع الامتحانات ==========

@router.get("/exam-types", response_model=List[ExamTypeResponse])
def get_all_exam_types(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.SUPER_ADMIN]))
):
    """الحصول على جميع أنواع الامتحانات"""
    return ExamTypeService.get_all_exam_types(db, include_inactive)

@router.post("/exam-types", response_model=ExamTypeResponse, status_code=status.HTTP_201_CREATED)
def create_exam_type(
    exam_type_data: ExamTypeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.SUPER_ADMIN]))
):
    """إنشاء نوع امتحان جديد"""
    try:
        return ExamTypeService.create_exam_type(db, exam_type_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/exam-types/{exam_type_id}", response_model=ExamTypeResponse)
def update_exam_type(
    exam_type_id: int,
    exam_type_data: ExamTypeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.SUPER_ADMIN]))
):
    """تحديث نوع امتحان"""
    try:
        exam_type = ExamTypeService.update_exam_type(db, exam_type_id, exam_type_data)
        if not exam_type:
            raise HTTPException(status_code=404, detail="نوع الامتحان غير موجود")
        return exam_type
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/exam-types/{exam_type_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exam_type(
    exam_type_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.SUPER_ADMIN]))
):
    """حذف نوع امتحان"""
    success = ExamTypeService.delete_exam_type(db, exam_type_id)
    if not success:
        raise HTTPException(status_code=404, detail="نوع الامتحان غير موجود")
    return None

# ========== إدارة أنواع المخالفات ==========

@router.get("/violation-types", response_model=List[ViolationTypeResponse])
def get_all_violation_types(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.SUPER_ADMIN]))
):
    """الحصول على جميع أنواع المخالفات"""
    return ViolationTypeService.get_all_violation_types(db, include_inactive)


@router.post(
    "/violation-types",
    response_model=ViolationTypeResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_violation_type(
    data: ViolationTypeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.SUPER_ADMIN]))
):
    """إنشاء نوع مخالفة جديد"""
    try:
        return ViolationTypeService.create_violation_type(db, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/violation-types/{violation_type_id}", response_model=ViolationTypeResponse)
def update_violation_type(
    violation_type_id: int,
    data: ViolationTypeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.SUPER_ADMIN]))
):
    """تحديث نوع مخالفة"""
    try:
        vt = ViolationTypeService.update_violation_type(db, violation_type_id, data)
        if not vt:
            raise HTTPException(status_code=404, detail="نوع المخالفة غير موجود")
        return vt
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/violation-types/{violation_type_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_violation_type(
    violation_type_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.SUPER_ADMIN]))
):
    """حذف نوع مخالفة"""
    success = ViolationTypeService.delete_violation_type(db, violation_type_id)
    if not success:
        raise HTTPException(status_code=404, detail="نوع المخالفة غير موجود")
    return None

# ========== إدارة أنواع الرخص (جدول) ==========

@router.get("/license-types", response_model=List[LicenseTypeResponse])
def get_all_license_types_admin(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.SUPER_ADMIN])),
):
    """الحصول على جميع أنواع الرخص (للأدمن)"""
    return LicenseTypeService.list_license_types(db, include_inactive=include_inactive)


@router.post("/license-types", response_model=LicenseTypeResponse, status_code=status.HTTP_201_CREATED)
def create_license_type_admin(
    data: LicenseTypeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.SUPER_ADMIN])),
):
    """إنشاء نوع رخصة جديد"""
    try:
        return LicenseTypeService.create_license_type(db, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/license-types/{license_type_id}", response_model=LicenseTypeResponse)
def update_license_type_admin(
    license_type_id: int,
    data: LicenseTypeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.SUPER_ADMIN])),
):
    """تحديث نوع رخصة"""
    try:
        lt = LicenseTypeService.update_license_type(db, license_type_id, data)
        if not lt:
            raise HTTPException(status_code=404, detail="نوع الرخصة غير موجود")
        return lt
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/license-types/{license_type_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_license_type_admin(
    license_type_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.SUPER_ADMIN])),
):
    """حذف نوع رخصة"""
    ok = LicenseTypeService.delete_license_type(db, license_type_id)
    if not ok:
        raise HTTPException(status_code=404, detail="نوع الرخصة غير موجود")
    return None


@router.post(
    "/license-types/{license_type_id}/categories",
    response_model=LicenseTypeCategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_license_type_category_admin(
    license_type_id: int,
    data: LicenseTypeCategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.SUPER_ADMIN])),
):
    """إضافة فئة (A/B) لنوع رخصة"""
    cat = LicenseTypeService.add_category(db, license_type_id, data)
    if not cat:
        raise HTTPException(status_code=404, detail="نوع الرخصة غير موجود")
    return cat


@router.put(
    "/license-types/{license_type_id}/categories/{category_id}",
    response_model=LicenseTypeCategoryResponse,
)
def update_license_type_category_admin(
    license_type_id: int,
    category_id: int,
    data: LicenseTypeCategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.SUPER_ADMIN])),
):
    """تحديث فئة (A/B)"""
    cat = LicenseTypeService.update_category(db, license_type_id, category_id, data)
    if not cat:
        raise HTTPException(status_code=404, detail="الفئة غير موجودة")
    return cat


@router.delete(
    "/license-types/{license_type_id}/categories/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_license_type_category_admin(
    license_type_id: int,
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.SUPER_ADMIN])),
):
    """حذف فئة (A/B)"""
    ok = LicenseTypeService.delete_category(db, license_type_id, category_id)
    if not ok:
        raise HTTPException(status_code=404, detail="الفئة غير موجودة")
    return None

# ========== إدارة الرخص ==========

@router.get("/licenses", response_model=List[LicenseResponse])
def get_all_licenses_admin(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.SUPER_ADMIN]))
):
    """الحصول على جميع الرخص"""
    from app.features.license.model import License
    
    query = db.query(License)
    if status:
        try:
            license_status = LicenseStatus(status)
            query = query.filter(License.status == license_status)
        except ValueError:
            pass
    
    licenses = query.order_by(License.application_date.desc()).all()
    return licenses


@router.get("/licenses/signature/pending", response_model=List[LicenseResponse])
def get_pending_license_signatures(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.SUPER_ADMIN])),
):
    """الرخص المرحّلة من مسؤول الرخص بانتظار اعتماد/توقيع رئيس القسم."""
    from app.features.license.model import License

    rows = (
        db.query(License)
        .filter(
            License.status == LicenseStatus.ISSUED,
            (License.dept_approval_requested == 1),
            ((License.dept_approval_approved == 0) | (License.dept_approval_approved == None)),
        )
        .order_by(License.dept_approval_requested_at.desc().nullslast(), License.issued_date.desc().nullslast())
        .all()
    )
    return rows


@router.post("/licenses/{license_id}/signature/approve", response_model=LicenseResponse)
def approve_license_signature(
    license_id: int,
    signature_image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.SUPER_ADMIN])),
):
    """اعتماد/توقيع رخصة من رئيس القسم (بعد ترحيلها من مسؤول الرخص) مع رفع صورة التوقيع."""
    from datetime import datetime
    from app.features.license.model import License
    import os
    import uuid

    lic = db.query(License).filter(License.id == license_id).first()
    if not lic:
        raise HTTPException(status_code=404, detail="الرخصة غير موجودة")

    if lic.status != LicenseStatus.ISSUED:
        raise HTTPException(status_code=400, detail="لا يمكن اعتماد هذه الرخصة حالياً")

    if (lic.dept_approval_requested or 0) != 1:
        raise HTTPException(status_code=400, detail="هذه الرخصة لم يتم ترحيلها بعد للاعتماد")

    if (lic.dept_approval_approved or 0) == 1:
        raise HTTPException(status_code=400, detail="تم اعتماد هذه الرخصة بالفعل")

    # رفع صورة التوقيع إذا تم إرسالها
    if signature_image:
        # التحقق من نوع الملف
        if not signature_image.content_type or not signature_image.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="يجب رفع صورة للتوقيع")
        
        # إنشاء مجلد لحفظ التوقيعات
        signature_dir = "uploads/signatures"
        os.makedirs(signature_dir, exist_ok=True)
        
        # إنشاء اسم فريد للملف
        file_extension = signature_image.filename.split('.')[-1] if '.' in signature_image.filename else 'png'
        unique_filename = f"signature_{license_id}_{uuid.uuid4().hex[:8]}.{file_extension}"
        file_path = os.path.join(signature_dir, unique_filename)
        
        # حفظ الملف
        try:
            with open(file_path, "wb") as buffer:
                content = signature_image.file.read()
                buffer.write(content)
            
            lic.signature_image_path = file_path
            print(f"✓ Signature image saved: {file_path}")
        except Exception as e:
            print(f"⚠️ Error saving signature image: {e}")
            raise HTTPException(status_code=500, detail="حدث خطأ أثناء حفظ صورة التوقيع")

    lic.dept_approval_approved = 1
    lic.dept_approval_approved_at = datetime.now()
    lic.dept_approval_approved_by_user_id = current_user.id
    db.commit()
    db.refresh(lic)
    return lic

# ========== إدارة الامتحانات ==========

@router.get("/exams", response_model=List[ExamResponse])
def get_all_exams_admin(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.SUPER_ADMIN]))
):
    """الحصول على جميع الامتحانات"""
    from app.features.exam.model import Exam
    
    exams = db.query(Exam).order_by(Exam.exam_date.desc()).all()
    return exams

# ========== إدارة المخالفات ==========

@router.get("/violations", response_model=List[ViolationResponse])
def get_all_violations_admin(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.SUPER_ADMIN]))
):
    """الحصول على جميع المخالفات"""
    from app.features.violation.model import Violation
    
    query = db.query(Violation)
    if status:
        try:
            violation_status = ViolationStatus(status)
            query = query.filter(Violation.status == violation_status)
        except ValueError:
            pass
    
    violations = query.order_by(Violation.violation_date.desc()).all()
    return violations

# ========== التقارير والإحصائيات ==========

@router.get("/statistics")
def get_system_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.SUPER_ADMIN]))
):
    """الحصول على إحصائيات النظام الشاملة"""
    return AdminService.get_system_statistics(db)

