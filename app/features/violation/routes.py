from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.features.user.model import User
from app.models.enums import UserRole, ViolationStatus
from app.features.violation.schema import (
    ViolationResponse,
    ViolationCreate,
    ViolationUpdate,
    ViolationCreateByLicenseNumber,
    ViolationCreateByNationalId,
    ViolationsByLicenseResponse,
    ViolationsByNationalIdResponse,
    ViolationCancelRequest,
    ViolationModifyRequest,
    PaymentReceiptResponse,
    ViolationStatisticsResponse,
)
from datetime import datetime, timedelta
from app.features.violation.service import ViolationService
from app.features.license.service import LicenseService
from app.features.violation_type.service import ViolationTypeService
from app.features.violation_type.schema import (
    ViolationTypeResponse,
    ViolationTypeCreate,
    ViolationTypeUpdate,
)

router = APIRouter()

@router.post("/create", response_model=ViolationResponse, status_code=status.HTTP_201_CREATED)
def create_violation(
    violation_data: ViolationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.VIOLATION_OFFICER, UserRole.TRAFFIC_POLICE]))
):
    """إنشاء مخالفة جديدة"""
    try:
        violation = ViolationService.create_violation(db, violation_data, current_user.id)
        return violation
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/types", response_model=List[ViolationTypeResponse])
def get_violation_types_for_officer(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.VIOLATION_OFFICER, UserRole.TRAFFIC_POLICE])),
):
    """الحصول على قائمة أنواع المخالفات لمسؤول المخالفات"""
    return ViolationTypeService.get_all_violation_types(db, include_inactive=include_inactive)


@router.post("/types", response_model=ViolationTypeResponse, status_code=status.HTTP_201_CREATED)
def create_violation_type_for_officer(
    data: ViolationTypeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.VIOLATION_OFFICER])),  # فقط مسؤول المخالفات يمكنه إنشاء أنواع
):
    """إنشاء نوع مخالفة جديد (مسؤول المخالفات)"""
    try:
        return ViolationTypeService.create_violation_type(db, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/types/{violation_type_id}", response_model=ViolationTypeResponse)
def update_violation_type_for_officer(
    violation_type_id: int,
    data: ViolationTypeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.VIOLATION_OFFICER])),  # فقط مسؤول المخالفات يمكنه التعديل
):
    """تحديث نوع مخالفة (مسؤول المخالفات)"""
    try:
        vt = ViolationTypeService.update_violation_type(db, violation_type_id, data)
        if not vt:
            raise HTTPException(status_code=404, detail="نوع المخالفة غير موجود")
        return vt
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/types/{violation_type_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_violation_type_for_officer(
    violation_type_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.VIOLATION_OFFICER])),  # فقط مسؤول المخالفات يمكنه الحذف
):
    """حذف نوع مخالفة (مسؤول المخالفات)"""
    success = ViolationTypeService.delete_violation_type(db, violation_type_id)
    if not success:
        raise HTTPException(status_code=404, detail="نوع المخالفة غير موجود")
    return None


@router.get("/by-license/{license_number}", response_model=ViolationsByLicenseResponse)
def get_violations_by_license_number(
    license_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.VIOLATION_OFFICER, UserRole.TRAFFIC_POLICE])),
):
    """الاستعلام عن المخالفات حسب رقم الرخصة"""
    license = LicenseService.get_license_by_number(db, license_number)
    if not license:
        raise HTTPException(status_code=404, detail="الرخصة غير موجودة")

    from app.features.violation.model import Violation
    violations = (
        db.query(Violation)
        .filter(Violation.license_id == license.id)
        .order_by(Violation.violation_date.desc())
        .all()
    )

    return {
        "license": {
            "id": license.id,
            "license_number": license.license_number,
            "full_name": license.full_name,
            "status": license.status.value if hasattr(license.status, "value") else str(license.status),
        },
        "violations": violations,
        "has_violations": len(violations) > 0,
        "violations_count": len(violations),
    }


@router.post("/by-license", response_model=ViolationResponse, status_code=status.HTTP_201_CREATED)
def create_violation_by_license_number(
    data: ViolationCreateByLicenseNumber,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.VIOLATION_OFFICER, UserRole.TRAFFIC_POLICE])),
):
    """إضافة مخالفة عبر رقم الرخصة واختيار نوع المخالفة"""
    license = LicenseService.get_license_by_number(db, data.license_number)
    if not license:
        raise HTTPException(status_code=404, detail="الرخصة غير موجودة")

    vt = ViolationTypeService.get_violation_type_by_id(db, data.violation_type_id)
    if not vt or not vt.is_active:
        raise HTTPException(status_code=400, detail="نوع المخالفة غير صالح")

    violation_data = ViolationCreate(
        user_id=license.user_id,
        license_id=license.id,
        violation_type_id=vt.id,
        violation_type=vt.name,
        description=data.description,
        location=data.location,
        violation_date=data.violation_date,
        fine_amount=vt.fine_amount,
    )
    violation = ViolationService.create_violation(db, violation_data, current_user.id)
    return violation


@router.get("/by-national-id/{national_id}", response_model=ViolationsByNationalIdResponse)
def get_violations_by_national_id(
    national_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.VIOLATION_OFFICER, UserRole.TRAFFIC_POLICE, UserRole.LICENSE_OFFICER])),
):
    """الاستعلام عن المخالفات حسب الرقم الوطني (مربوطة بالمواطن)"""
    citizen = db.query(User).filter(User.national_id == national_id).first()
    if not citizen:
        raise HTTPException(status_code=404, detail="المواطن غير موجود")

    from app.features.violation.model import Violation

    violations = (
        db.query(Violation)
        .filter(Violation.user_id == citizen.id)
        .order_by(Violation.violation_date.desc())
        .all()
    )
    return {
        "citizen": {"id": citizen.id, "national_id": citizen.national_id, "phone": citizen.phone},
        "violations": violations,
        "has_violations": len(violations) > 0,
        "violations_count": len(violations),
    }


@router.post("/by-national-id", response_model=ViolationResponse, status_code=status.HTTP_201_CREATED)
def create_violation_by_national_id(
    data: ViolationCreateByNationalId,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.VIOLATION_OFFICER, UserRole.TRAFFIC_POLICE])),
):
    """إضافة مخالفة عبر الرقم الوطني (بدون الحاجة لرقم الرخصة)"""
    citizen = db.query(User).filter(User.national_id == data.national_id).first()
    if not citizen:
        raise HTTPException(status_code=404, detail="المواطن غير موجود")

    vt = ViolationTypeService.get_violation_type_by_id(db, data.violation_type_id)
    if not vt or not vt.is_active:
        raise HTTPException(status_code=400, detail="نوع المخالفة غير صالح")

    # حاول ربطها بأحدث رخصة صادرة (اختياري)
    license_id = None
    try:
        from app.features.license.model import License
        from app.models.enums import LicenseStatus

        lic = (
            db.query(License)
            .filter(License.user_id == citizen.id)
            .filter(License.status.in_([LicenseStatus.ISSUED, LicenseStatus.EXPIRED]))
            .order_by(License.id.desc())
            .first()
        )
        if lic:
            license_id = lic.id
    except Exception:
        license_id = None

    violation_data = ViolationCreate(
        user_id=citizen.id,
        license_id=license_id,
        violation_type_id=vt.id,
        violation_type=vt.name,
        description=data.description,
        location=data.location,
        violation_date=data.violation_date,
        fine_amount=vt.fine_amount,
    )
    violation = ViolationService.create_violation(db, violation_data, current_user.id)
    return violation

@router.get("/my-violations", response_model=List[ViolationResponse])
def get_my_violations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """الحصول على جميع مخالفات المستخدم الحالي"""
    violations = ViolationService.get_user_violations(db, current_user.id)
    return violations

@router.get("/", response_model=List[ViolationResponse])
def get_all_violations(
    status: Optional[ViolationStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.VIOLATION_OFFICER, UserRole.TRAFFIC_POLICE]))
):
    """الحصول على جميع المخالفات"""
    violations = ViolationService.get_all_violations(db, status)
    return violations

@router.post("/{violation_id}/pay", response_model=ViolationResponse)
def pay_violation(
    violation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.VIOLATION_OFFICER, UserRole.TRAFFIC_POLICE, UserRole.LICENSE_OFFICER])),
):
    """دفع مخالفة (مسؤول المخالفات أو مسؤول الرخص) - تتحول الحالة إلى PAID وتبقى في سجل المواطن"""
    vio = ViolationService.mark_paid(db, violation_id, current_user.id)
    if not vio:
        raise HTTPException(status_code=404, detail="المخالفة غير موجودة")
    return vio


@router.get("/{violation_id}/receipt", response_model=PaymentReceiptResponse)
def get_payment_receipt(
    violation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.VIOLATION_OFFICER, UserRole.LICENSE_OFFICER])),
):
    """الحصول على إيصال دفع مخالفة"""
    violation = ViolationService.get_violation_by_id(db, violation_id)
    if not violation:
        raise HTTPException(status_code=404, detail="المخالفة غير موجودة")
    
    if violation.status != ViolationStatus.PAID:
        raise HTTPException(status_code=400, detail="المخالفة غير مدفوعة")
    
    if not violation.paid_by_user_id:
        raise HTTPException(status_code=400, detail="لا يوجد معلومات عن الدفع")
    
    # الحصول على معلومات المواطن
    citizen = db.query(User).filter(User.id == violation.user_id).first()
    if not citizen:
        raise HTTPException(status_code=404, detail="المواطن غير موجود")
    
    # الحصول على معلومات الموظف
    officer = db.query(User).filter(User.id == violation.paid_by_user_id).first()
    if not officer:
        raise HTTPException(status_code=404, detail="الموظف غير موجود")
    
    # إنشاء رقم إيصال
    receipt_number = f"REC-{violation.violation_number}-{violation.paid_at.strftime('%Y%m%d')}"
    
    return {
        "receipt_number": receipt_number,
        "violation_number": violation.violation_number,
        "national_id": citizen.national_id or "",
        "citizen_name": None,  # يمكن إضافته من الرخصة إذا لزم الأمر
        "fine_amount": violation.fine_amount,
        "payment_date": violation.paid_at,
        "officer_name": officer.username or officer.national_id or "غير محدد",
        "officer_username": officer.username,
    }


@router.post("/{violation_id}/cancel", response_model=ViolationResponse)
def cancel_violation(
    violation_id: int,
    cancel_data: ViolationCancelRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.VIOLATION_OFFICER])),
):
    """إلغاء مخالفة"""
    try:
        vio = ViolationService.cancel_violation(
            db, violation_id, current_user.id, cancel_data.cancellation_reason
        )
        if not vio:
            raise HTTPException(status_code=404, detail="المخالفة غير موجودة")
        return vio
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{violation_id}/modify", response_model=ViolationResponse)
def modify_violation(
    violation_id: int,
    modify_data: ViolationModifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.VIOLATION_OFFICER])),
):
    """تعديل مخالفة (فقط قبل الدفع)"""
    try:
        modification_dict = modify_data.dict(exclude_unset=True, exclude={'modification_reason'})
        vio = ViolationService.modify_violation(
            db, violation_id, current_user.id, modification_dict, modify_data.modification_reason
        )
        if not vio:
            raise HTTPException(status_code=404, detail="المخالفة غير موجودة")
        return vio
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/statistics", response_model=ViolationStatisticsResponse)
def get_violation_statistics(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    officer_id: Optional[int] = None,
    period: Optional[str] = None,  # 'today', 'week', 'month', 'year'
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.VIOLATION_OFFICER])),
):
    """الحصول على إحصائيات المخالفات"""
    # حساب التواريخ حسب الفترة المحددة
    if period:
        now = datetime.now()
        if period == 'today':
            start_date = datetime(now.year, now.month, now.day)
            end_date = now
        elif period == 'week':
            start_date = now - timedelta(days=7)
            end_date = now
        elif period == 'month':
            start_date = datetime(now.year, now.month, 1)
            end_date = now
        elif period == 'year':
            start_date = datetime(now.year, 1, 1)
            end_date = now
    
    # إذا كان المستخدم ليس super_admin، استخدم ID الخاص به فقط
    if current_user.role != UserRole.SUPER_ADMIN:
        officer_id = current_user.id
    
    stats = ViolationService.get_violation_statistics(db, start_date, end_date, officer_id)
    return stats


@router.get("/{violation_id}", response_model=ViolationResponse)
def get_violation(
    violation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """الحصول على مخالفة"""
    violation = ViolationService.get_violation_by_id(db, violation_id)
    if not violation:
        raise HTTPException(status_code=404, detail="المخالفة غير موجودة")
    
    if current_user.role == UserRole.CITIZEN and violation.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="ليس لديك صلاحية للوصول")
    
    return violation

@router.put("/{violation_id}", response_model=ViolationResponse)
def update_violation(
    violation_id: int,
    violation_data: ViolationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """تحديث مخالفة"""
    violation = ViolationService.get_violation_by_id(db, violation_id)
    if not violation:
        raise HTTPException(status_code=404, detail="المخالفة غير موجودة")
    
    if current_user.role == UserRole.CITIZEN:
        raise HTTPException(status_code=403, detail="ليس لديك صلاحية لتحديث المخالفة")
    else:
        if current_user.role not in [UserRole.VIOLATION_OFFICER, UserRole.LICENSE_OFFICER, UserRole.SUPER_ADMIN]:
            raise HTTPException(status_code=403, detail="ليس لديك صلاحية")
    
    updated_violation = ViolationService.update_violation(db, violation_id, violation_data)
    return updated_violation














