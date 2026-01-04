from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.features.user.model import User
from app.models.enums import UserRole, LicenseRenewalStatus
from app.features.license_renewal.schema import (
    LicenseRenewalCreate,
    LicenseRenewalApprove,
    LicenseRenewalReject,
    LicenseRenewalResponse,
    LicenseRenewalVisionExamSchedule,
    LicenseRenewalVisionExamResult,
)
from app.features.license_renewal.service import LicenseRenewalService

router = APIRouter()


def _to_response(r) -> LicenseRenewalResponse:
    lic = getattr(r, "license", None)
    usr = getattr(r, "user", None)
    renewal_fee = getattr(r, "renewal_fee", None)
    if renewal_fee is not None:
        renewal_fee = float(renewal_fee)
    
    return LicenseRenewalResponse(
        id=r.id,
        tracking_code=r.tracking_code,
        license_id=r.license_id,
        user_id=r.user_id,
        new_photo_path=r.new_photo_path,
        status=r.status,
        payment_confirmed=r.payment_confirmed,
        citizen_notes=getattr(r, "citizen_notes", None),
        officer_notes=getattr(r, "officer_notes", None),
        requested_at=r.requested_at,
        reviewed_at=r.reviewed_at,
        reviewed_by_user_id=r.reviewed_by_user_id,
        license_number=getattr(lic, "license_number", None) if lic else None,
        full_name=getattr(lic, "full_name", None) if lic else None,
        user_national_id=getattr(usr, "national_id", None) if usr else None,
        expiry_date=getattr(lic, "expiry_date", None) if lic else None,
        vision_exam_date=getattr(r, "vision_exam_date", None),
        vision_exam_result=getattr(r, "vision_exam_result", None),
        vision_exam_conducted_by_user_id=getattr(r, "vision_exam_conducted_by_user_id", None),
        renewal_fee=renewal_fee,
    )


# ===== Citizen =====

@router.post("/apply", response_model=LicenseRenewalResponse, status_code=status.HTTP_201_CREATED)
def apply_for_renewal(
    data: LicenseRenewalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.CITIZEN:
        raise HTTPException(status_code=403, detail="هذا المسار للمواطن فقط")
    try:
        r = LicenseRenewalService.create_renewal_request(
            db=db,
            user_id=current_user.id,
            license_id=data.license_id,
            new_photo_path=data.new_photo_path,
            citizen_notes=data.citizen_notes,
        )
        return _to_response(r)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/my", response_model=List[LicenseRenewalResponse])
def my_renewals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.CITIZEN:
        raise HTTPException(status_code=403, detail="هذا المسار للمواطن فقط")
    rows = LicenseRenewalService.list_my_renewals(db, current_user.id)
    return [_to_response(r) for r in rows]


# ===== License Officer =====

@router.get("/pending", response_model=List[LicenseRenewalResponse])
def list_pending(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.LICENSE_OFFICER])),
):
    rows = LicenseRenewalService.list_renewals_for_officer(db, status=LicenseRenewalStatus.PENDING)
    return [_to_response(r) for r in rows]


@router.get("/approved", response_model=List[LicenseRenewalResponse])
def list_approved(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.LICENSE_OFFICER])),
):
    rows = LicenseRenewalService.list_renewals_for_officer(db, status=LicenseRenewalStatus.APPROVED)
    return [_to_response(r) for r in rows]


@router.post("/{renewal_id}/vision-exam/schedule", response_model=LicenseRenewalResponse)
def schedule_vision_exam(
    renewal_id: int,
    data: LicenseRenewalVisionExamSchedule,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.LICENSE_OFFICER])),
):
    """تحديد موعد امتحان النظر لطلب تجديد الرخصة"""
    try:
        r = LicenseRenewalService.schedule_vision_exam(
            db=db,
            renewal_id=renewal_id,
            vision_exam_date=data.vision_exam_date,
            officer_user_id=current_user.id,
        )
        return _to_response(r)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{renewal_id}/vision-exam/result", response_model=LicenseRenewalResponse)
def submit_vision_exam_result(
    renewal_id: int,
    data: LicenseRenewalVisionExamResult,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.LICENSE_OFFICER])),
):
    """تسجيل نتيجة امتحان النظر"""
    try:
        r = LicenseRenewalService.submit_vision_exam_result(
            db=db,
            renewal_id=renewal_id,
            vision_exam_result=data.vision_exam_result,
            officer_user_id=current_user.id,
            officer_notes=data.officer_notes,
        )
        return _to_response(r)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{renewal_id}/approve", response_model=LicenseRenewalResponse)
def approve(
    renewal_id: int,
    data: LicenseRenewalApprove,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.LICENSE_OFFICER])),
):
    """اعتماد تجديد الرخصة (يجب أن يكون امتحان النظر ناجحاً)"""
    try:
        r = LicenseRenewalService.approve_renewal(
            db=db,
            renewal_id=renewal_id,
            officer_user_id=current_user.id,
            payment_confirmed=data.payment_confirmed,
            officer_notes=data.officer_notes,
        )
        return _to_response(r)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{renewal_id}/reject", response_model=LicenseRenewalResponse)
def reject(
    renewal_id: int,
    data: LicenseRenewalReject,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.LICENSE_OFFICER])),
):
    try:
        r = LicenseRenewalService.reject_renewal(
            db=db,
            renewal_id=renewal_id,
            officer_user_id=current_user.id,
            officer_notes=data.officer_notes,
        )
        return _to_response(r)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

















