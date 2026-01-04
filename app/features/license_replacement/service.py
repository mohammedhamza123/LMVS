from sqlalchemy.orm import Session
from datetime import datetime, date
from typing import Optional, List
import random
import string

from app.features.license.model import License
from app.features.license.service import LicenseService
from app.features.license_replacement.model import LicenseReplacement
from app.models.enums import LicenseRenewalStatus, LicenseStatus


class LicenseReplacementService:
    @staticmethod
    def _gen(prefix: str) -> str:
        return prefix + "".join(random.choices(string.digits, k=8))

    @staticmethod
    def _unique_code(db: Session, field: str, prefix: str) -> str:
        for _ in range(20):
            code = LicenseReplacementService._gen(prefix)
            q = db.query(LicenseReplacement)
            if field == "tracking_code":
                exists = q.filter(LicenseReplacement.tracking_code == code).first()
            else:
                exists = q.filter(LicenseReplacement.payment_code == code).first()
            if not exists:
                return code
        raise ValueError("فشل إنشاء كود فريد، حاول مرة أخرى")

    @staticmethod
    def create_request(
        db: Session,
        user_id: int,
        license_id: int,
        police_report_path: str,
        citizen_notes: Optional[str] = None,
    ) -> LicenseReplacement:
        lic = db.query(License).filter(License.id == license_id).first()
        if not lic:
            raise ValueError("الرخصة غير موجودة")
        if lic.user_id != user_id:
            raise ValueError("ليس لديك صلاحية")

        # فقط رخصة سارية (صادرة وغير منتهية)
        if lic.status != LicenseStatus.ISSUED:
            raise ValueError("لا يمكن طلب بدل فاقد إلا للرخص الصادرة والسارية")
        if not lic.expiry_date:
            raise ValueError("لا يمكن طلب بدل فاقد (لا يوجد تاريخ انتهاء)")
        if lic.expiry_date < date.today():
            raise ValueError("لا يمكن طلب بدل فاقد (الرخصة منتهية)")

        if not police_report_path or not police_report_path.strip():
            raise ValueError("بلاغ الفقد إلزامي")

        # لا يسمح بطلب جديد إلا بعد الرفض (نفس قاعدة التجديد)
        last_req = (
            db.query(LicenseReplacement)
            .filter(LicenseReplacement.license_id == license_id)
            .order_by(LicenseReplacement.requested_at.desc())
            .first()
        )
        if last_req and last_req.status != LicenseRenewalStatus.REJECTED:
            if last_req.status == LicenseRenewalStatus.PENDING:
                raise ValueError("لا يمكن إرسال طلب بدل فاقد مرة أخرى إلا بعد رفض الطلب الحالي")
            raise ValueError("تم اعتماد بدل فاقد بالفعل لهذه الرخصة")

        tracking = LicenseReplacementService._unique_code(db, "tracking_code", "LOS")
        payment = LicenseReplacementService._unique_code(db, "payment_code", "PAY")

        r = LicenseReplacement(
            tracking_code=tracking,
            payment_code=payment,
            license_id=license_id,
            user_id=user_id,
            police_report_path=police_report_path.strip(),
            citizen_notes=(citizen_notes.strip() if citizen_notes else None),
        )
        db.add(r)
        db.commit()
        db.refresh(r)
        return r

    @staticmethod
    def list_my(db: Session, user_id: int) -> List[LicenseReplacement]:
        return (
            db.query(LicenseReplacement)
            .filter(LicenseReplacement.user_id == user_id)
            .order_by(LicenseReplacement.requested_at.desc())
            .all()
        )

    @staticmethod
    def list_pending(db: Session) -> List[LicenseReplacement]:
        return (
            db.query(LicenseReplacement)
            .filter(LicenseReplacement.status == LicenseRenewalStatus.PENDING)
            .order_by(LicenseReplacement.requested_at.desc())
            .all()
        )

    @staticmethod
    def approve(
        db: Session,
        replacement_id: int,
        officer_user_id: int,
        payment_confirmed: bool,
        payment_code: str,
        officer_notes: Optional[str] = None,
    ) -> LicenseReplacement:
        r = db.query(LicenseReplacement).filter(LicenseReplacement.id == replacement_id).first()
        if not r:
            raise ValueError("طلب بدل فاقد غير موجود")
        if r.status != LicenseRenewalStatus.PENDING:
            raise ValueError("هذا الطلب ليس معلقاً")
        if not payment_confirmed:
            raise ValueError("يجب تأكيد الدفع")
        if not payment_code or payment_code.strip() != r.payment_code:
            raise ValueError("كود الدفع غير صحيح")

        lic = db.query(License).filter(License.id == r.license_id).first()
        if not lic:
            raise ValueError("الرخصة غير موجودة")

        # إيقاف الرخصة القديمة (البطاقة القديمة) عبر تغيير الباركود/التوكن
        # هذا يجعل أي بطاقة قديمة (باركود قديم) غير صالحة في صفحة التحقق.
        r.old_barcode = lic.barcode
        if lic.license_number:
            lic.barcode = LicenseService.generate_barcode(lic.license_number, lic.user_id)
        r.new_barcode = lic.barcode
        # token جديد أيضاً
        try:
            import uuid
            lic.public_edit_token = uuid.uuid4().hex
        except Exception:
            pass

        # إعادة إجبار مسار توقيع رئيس القسم قبل الطباعة
        lic.dept_approval_requested = 1
        lic.dept_approval_requested_at = datetime.now()
        lic.dept_approval_requested_by_user_id = officer_user_id
        lic.dept_approval_approved = 0
        lic.dept_approval_approved_at = None
        lic.dept_approval_approved_by_user_id = None

        r.payment_confirmed = True
        r.status = LicenseRenewalStatus.APPROVED
        r.reviewed_by_user_id = officer_user_id
        r.reviewed_at = datetime.now()
        r.officer_notes = officer_notes.strip() if officer_notes else None

        db.add(lic)
        db.add(r)
        db.commit()
        db.refresh(r)
        return r

    @staticmethod
    def reject(
        db: Session,
        replacement_id: int,
        officer_user_id: int,
        officer_notes: Optional[str] = None,
    ) -> LicenseReplacement:
        r = db.query(LicenseReplacement).filter(LicenseReplacement.id == replacement_id).first()
        if not r:
            raise ValueError("طلب بدل فاقد غير موجود")
        if r.status != LicenseRenewalStatus.PENDING:
            raise ValueError("هذا الطلب ليس معلقاً")

        r.status = LicenseRenewalStatus.REJECTED
        r.reviewed_by_user_id = officer_user_id
        r.reviewed_at = datetime.now()
        r.officer_notes = officer_notes.strip() if officer_notes else None

        db.add(r)
        db.commit()
        db.refresh(r)
        return r


