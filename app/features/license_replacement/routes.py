from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.features.user.model import User
from app.models.enums import UserRole
from app.features.license_replacement.schema import (
    LicenseReplacementCreate,
    LicenseReplacementApprove,
    LicenseReplacementReject,
    LicenseReplacementResponse,
)
from app.features.license_replacement.service import LicenseReplacementService

router = APIRouter()


def _to_response(r) -> LicenseReplacementResponse:
    lic = getattr(r, "license", None)
    usr = getattr(r, "user", None)
    return LicenseReplacementResponse(
        id=r.id,
        tracking_code=r.tracking_code,
        payment_code=r.payment_code,
        license_id=r.license_id,
        user_id=r.user_id,
        police_report_path=r.police_report_path,
        status=r.status,
        payment_confirmed=r.payment_confirmed,
        citizen_notes=getattr(r, "citizen_notes", None),
        officer_notes=getattr(r, "officer_notes", None),
        requested_at=r.requested_at,
        reviewed_at=r.reviewed_at,
        reviewed_by_user_id=r.reviewed_by_user_id,
        old_barcode=getattr(r, "old_barcode", None),
        new_barcode=getattr(r, "new_barcode", None),
        license_number=getattr(lic, "license_number", None) if lic else None,
        full_name=getattr(lic, "full_name", None) if lic else None,
        user_national_id=getattr(usr, "national_id", None) if usr else None,
        expiry_date=getattr(lic, "expiry_date", None) if lic else None,
    )


# ===== Citizen =====

@router.post("/apply", response_model=LicenseReplacementResponse, status_code=status.HTTP_201_CREATED)
def apply(
    data: LicenseReplacementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.CITIZEN:
        raise HTTPException(status_code=403, detail="هذا المسار للمواطن فقط")
    try:
        r = LicenseReplacementService.create_request(
            db=db,
            user_id=current_user.id,
            license_id=data.license_id,
            police_report_path=data.police_report_path,
            citizen_notes=data.citizen_notes,
        )
        return _to_response(r)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/my", response_model=List[LicenseReplacementResponse])
def my(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.CITIZEN:
        raise HTTPException(status_code=403, detail="هذا المسار للمواطن فقط")
    rows = LicenseReplacementService.list_my(db, current_user.id)
    return [_to_response(r) for r in rows]


# ===== License Officer =====

@router.get("/pending", response_model=List[LicenseReplacementResponse])
def pending(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.LICENSE_OFFICER])),
):
    rows = LicenseReplacementService.list_pending(db)
    return [_to_response(r) for r in rows]


@router.post("/{replacement_id}/approve", response_model=LicenseReplacementResponse)
def approve(
    replacement_id: int,
    data: LicenseReplacementApprove,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.LICENSE_OFFICER])),
):
    try:
        r = LicenseReplacementService.approve(
            db=db,
            replacement_id=replacement_id,
            officer_user_id=current_user.id,
            payment_confirmed=data.payment_confirmed,
            payment_code=data.payment_code,
            officer_notes=data.officer_notes,
        )
        return _to_response(r)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{replacement_id}/reject", response_model=LicenseReplacementResponse)
def reject(
    replacement_id: int,
    data: LicenseReplacementReject,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.LICENSE_OFFICER])),
):
    try:
        r = LicenseReplacementService.reject(
            db=db,
            replacement_id=replacement_id,
            officer_user_id=current_user.id,
            officer_notes=data.officer_notes,
        )
        return _to_response(r)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


