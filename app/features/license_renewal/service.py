from sqlalchemy.orm import Session
from datetime import datetime, date
from typing import Optional, List
from decimal import Decimal
import random
import string

from app.features.license.model import License
from app.features.license.service import LicenseService
from app.features.license_type.model import LicenseType as LicenseTypeModel
from app.features.license_renewal.model import LicenseRenewal
from app.models.enums import LicenseRenewalStatus, LicenseStatus, UserRole
from app.services.fcm_service import FCMService


class LicenseRenewalService:
    @staticmethod
    def _generate_tracking_code() -> str:
        # REN + 8 digits
        return "REN" + "".join(random.choices(string.digits, k=8))

    @staticmethod
    def _ensure_unique_tracking_code(db: Session) -> str:
        for _ in range(20):
            code = LicenseRenewalService._generate_tracking_code()
            exists = db.query(LicenseRenewal).filter(LicenseRenewal.tracking_code == code).first()
            if not exists:
                return code
        raise ValueError("فشل إنشاء رقم تتبع فريد، حاول مرة أخرى")

    @staticmethod
    def create_renewal_request(
        db: Session,
        user_id: int,
        license_id: int,
        new_photo_path: str,
        citizen_notes: Optional[str] = None,
    ) -> LicenseRenewal:
        lic = db.query(License).filter(License.id == license_id).first()
        if not lic:
            raise ValueError("الرخصة غير موجودة")
        if lic.user_id != user_id:
            raise ValueError("ليس لديك صلاحية لتجديد هذه الرخصة")

        # يجب أن تكون صادرة أو منتهية ولها تاريخ انتهاء
        if lic.status not in [LicenseStatus.ISSUED, LicenseStatus.EXPIRED]:
            raise ValueError("لا يمكن تجديد هذه الرخصة حالياً")
        if not lic.expiry_date:
            raise ValueError("لا يمكن تجديد هذه الرخصة (لا يوجد تاريخ انتهاء)")

        today = date.today()
        if lic.expiry_date >= today:
            raise ValueError("الرخصة ليست منتهية بعد")

        # لا ننشئ طلب جديد لنفس الرخصة إلا إذا كان آخر طلب "مرفوض".
        # (أي: إذا كان هناك طلب معلق أو معتمد، يمنع الإرسال مرة أخرى)
        last_req = (
            db.query(LicenseRenewal)
            .filter(LicenseRenewal.license_id == license_id)
            .order_by(LicenseRenewal.requested_at.desc())
            .first()
        )
        if last_req and last_req.status != LicenseRenewalStatus.REJECTED:
            if last_req.status == LicenseRenewalStatus.PENDING:
                raise ValueError("لا يمكن إرسال طلب تجديد مرة أخرى إلا بعد رفض الطلب الحالي")
            # APPROVED
            raise ValueError("لا يمكن إرسال طلب تجديد مرة أخرى لأن التجديد تم اعتماده بالفعل")

        tracking = LicenseRenewalService._ensure_unique_tracking_code(db)
        r = LicenseRenewal(
            tracking_code=tracking,
            license_id=license_id,
            user_id=user_id,
            new_photo_path=new_photo_path.strip(),
            citizen_notes=(citizen_notes.strip() if citizen_notes else None),
            renewal_fee=Decimal('8.50'),  # سعر التجديد الافتراضي
        )
        db.add(r)
        db.commit()
        db.refresh(r)
        return r

    @staticmethod
    def list_my_renewals(db: Session, user_id: int) -> List[LicenseRenewal]:
        return (
            db.query(LicenseRenewal)
            .filter(LicenseRenewal.user_id == user_id)
            .order_by(LicenseRenewal.requested_at.desc())
            .all()
        )

    @staticmethod
    def list_renewals_for_officer(
        db: Session,
        status: Optional[LicenseRenewalStatus] = None,
    ) -> List[LicenseRenewal]:
        q = db.query(LicenseRenewal).order_by(LicenseRenewal.requested_at.desc())
        if status is not None:
            q = q.filter(LicenseRenewal.status == status)
        return q.all()

    @staticmethod
    def schedule_vision_exam(
        db: Session,
        renewal_id: int,
        vision_exam_date: datetime,
        officer_user_id: int,
    ) -> LicenseRenewal:
        """تحديد موعد امتحان النظر لطلب تجديد الرخصة"""
        r = db.query(LicenseRenewal).filter(LicenseRenewal.id == renewal_id).first()
        if not r:
            raise ValueError("طلب التجديد غير موجود")
        if r.status != LicenseRenewalStatus.PENDING:
            raise ValueError("لا يمكن تحديد موعد لطلب ليس معلقاً")
        
        r.vision_exam_date = vision_exam_date
        db.add(r)
        db.commit()
        db.refresh(r)
        
        # إرسال إشعار للمواطن
        try:
            FCMService.send_notification_to_user(
                user_id=r.user_id,
                title="تم تحديد موعد امتحان النظر",
                body=f"تم تحديد موعد امتحان النظر في {vision_exam_date.strftime('%Y-%m-%d %H:%M')}. يرجى الحضور في الموعد المحدد ودفع مبلغ 8.5 دينار عند الحضور.",
                data={
                    "type": "renewal_vision_exam_scheduled",
                    "renewal_id": str(renewal_id),
                    "exam_date": vision_exam_date.isoformat(),
                    "fee": "8.5"
                },
                db=db
            )
        except Exception as e:
            print(f"⚠️ Failed to send vision exam notification: {e}")
        
        return r
    
    @staticmethod
    def submit_vision_exam_result(
        db: Session,
        renewal_id: int,
        vision_exam_result: str,
        officer_user_id: int,
        officer_notes: Optional[str] = None,
    ) -> LicenseRenewal:
        """تسجيل نتيجة امتحان النظر"""
        r = db.query(LicenseRenewal).filter(LicenseRenewal.id == renewal_id).first()
        if not r:
            raise ValueError("طلب التجديد غير موجود")
        if r.status != LicenseRenewalStatus.PENDING:
            raise ValueError("لا يمكن تسجيل نتيجة لطلب ليس معلقاً")
        if not r.vision_exam_date:
            raise ValueError("يجب تحديد موعد امتحان النظر أولاً")
        if vision_exam_result not in ['passed', 'failed']:
            raise ValueError("نتيجة الامتحان يجب أن تكون 'passed' أو 'failed'")
        
        r.vision_exam_result = vision_exam_result
        r.vision_exam_conducted_by_user_id = officer_user_id
        if officer_notes:
            r.officer_notes = officer_notes.strip()
        
        db.add(r)
        db.commit()
        db.refresh(r)
        
        # إرسال إشعار للمواطن
        try:
            if vision_exam_result == 'passed':
                message = "تهانينا! لقد نجحت في امتحان النظر. يمكنك الآن دفع رسوم التجديد (8.5 دينار) لإكمال عملية التجديد."
            else:
                message = "نأسف، لم تنجح في امتحان النظر. يرجى المحاولة مرة أخرى في موعد لاحق."
            
            FCMService.send_notification_to_user(
                user_id=r.user_id,
                title="نتيجة امتحان النظر",
                body=message,
                data={
                    "type": "renewal_vision_exam_result",
                    "renewal_id": str(renewal_id),
                    "result": vision_exam_result
                },
                db=db
            )
        except Exception as e:
            print(f"⚠️ Failed to send vision exam result notification: {e}")
        
        return r

    @staticmethod
    def approve_renewal(
        db: Session,
        renewal_id: int,
        officer_user_id: int,
        payment_confirmed: bool,
        officer_notes: Optional[str] = None,
    ) -> LicenseRenewal:
        r = db.query(LicenseRenewal).filter(LicenseRenewal.id == renewal_id).first()
        if not r:
            raise ValueError("طلب التجديد غير موجود")
        if r.status != LicenseRenewalStatus.PENDING:
            raise ValueError("لا يمكن اعتماد هذا الطلب لأنه ليس معلقاً")
        if not payment_confirmed:
            raise ValueError("يجب تأكيد الدفع لاعتماد التجديد")
        # التحقق من نجاح امتحان النظر
        if not r.vision_exam_result:
            raise ValueError("يجب تحديد نتيجة امتحان النظر أولاً")
        if r.vision_exam_result != 'passed':
            raise ValueError("يجب أن يكون امتحان النظر ناجحاً لتجديد الرخصة")

        lic = db.query(License).filter(License.id == r.license_id).first()
        if not lic:
            raise ValueError("الرخصة الأصلية غير موجودة")

        # تحديث صورة الرخصة وتواريخها
        lic.photo_path = r.new_photo_path
        lic.issued_date = datetime.utcnow()

        # حساب تاريخ الانتهاء الجديد حسب نوع الرخصة (جدول license_types إن وجد)
        lt = None
        if getattr(lic, "license_type_id", None):
            lt = db.query(LicenseTypeModel).filter(LicenseTypeModel.id == lic.license_type_id).first()
        if lt and getattr(lt, "validity_years", None) is not None:
            years = int(lt.validity_years)
            lic.expiry_date = LicenseService._add_years(lic.issued_date.date(), years)
        else:
            lic.expiry_date = LicenseService.calculate_expiry_date(lic.license_type, lic.issued_date)

        lic.status = LicenseStatus.ISSUED

        # تحديث طلب التجديد
        r.payment_confirmed = True
        r.status = LicenseRenewalStatus.APPROVED
        r.reviewed_by_user_id = officer_user_id
        r.reviewed_at = datetime.utcnow()
        r.officer_notes = officer_notes.strip() if officer_notes else None

        db.add(lic)
        db.add(r)
        db.commit()
        db.refresh(r)
        return r

    @staticmethod
    def reject_renewal(
        db: Session,
        renewal_id: int,
        officer_user_id: int,
        officer_notes: Optional[str] = None,
    ) -> LicenseRenewal:
        r = db.query(LicenseRenewal).filter(LicenseRenewal.id == renewal_id).first()
        if not r:
            raise ValueError("طلب التجديد غير موجود")
        if r.status != LicenseRenewalStatus.PENDING:
            raise ValueError("لا يمكن رفض هذا الطلب لأنه ليس معلقاً")

        r.status = LicenseRenewalStatus.REJECTED
        r.reviewed_by_user_id = officer_user_id
        r.reviewed_at = datetime.utcnow()
        r.officer_notes = officer_notes.strip() if officer_notes else None

        db.add(r)
        db.commit()
        db.refresh(r)
        return r


