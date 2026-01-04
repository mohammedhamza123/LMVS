from sqlalchemy.orm import Session
from app.features.license.model import License
from app.features.license.schema import LicenseCreate, LicenseReview
from app.models.enums import LicenseStatus, LicenseType
from app.features.license_type.model import LicenseType as LicenseTypeModel
from datetime import datetime, date, timedelta
from typing import Optional, List
import random
import string
import hashlib

class LicenseService:
    @staticmethod
    def refresh_expired_status(db: Session, license: Optional[License]) -> bool:
        """
        تحديث حالة الرخصة إلى EXPIRED إذا انتهت صلاحيتها.
        يرجع True إذا تم تعديل أي شيء.
        """
        if not license:
            return False
        if license.status != LicenseStatus.ISSUED:
            return False
        if not license.expiry_date:
            return False
        today = date.today()
        if license.expiry_date < today:
            license.status = LicenseStatus.EXPIRED
            db.add(license)
            return True
        return False

    @staticmethod
    def refresh_expired_status_for_list(db: Session, licenses: List[License]) -> bool:
        changed = False
        for lic in licenses:
            if LicenseService.refresh_expired_status(db, lic):
                changed = True
        return changed
    @staticmethod
    def _add_years(d: date, years: int) -> date:
        """
        إضافة عدد سنوات لتاريخ مع معالجة 29 فبراير.
        مثال: 2024-02-29 + 1 سنة -> 2025-02-28
        """
        try:
            return d.replace(year=d.year + years)
        except ValueError:
            # happens on Feb 29 for non-leap year
            return d.replace(month=2, day=28, year=d.year + years)

    @staticmethod
    def _infer_license_type_from_license_type_id(
        db: Session, 
        license_type_id: Optional[int]
    ) -> Optional[LicenseType]:
        """
        محاولة استنتاج LicenseType enum من license_type_id بناءً على:
        1. اسم النوع في الجدول (إذا كان يطابق enum values)
        2. degree_order (1->PRIVATE, 2->PUBLIC, 3->TRUCK, 4->BUS)
        
        يُستخدم فقط إذا لم يكن license_type محدداً (للتوافق مع النظام القديم)
        """
        if not license_type_id:
            return None
        
        try:
            lt_model = db.query(LicenseTypeModel).filter(
                LicenseTypeModel.id == license_type_id
            ).first()
            
            if not lt_model:
                return None
            
            # محاولة 1: بناءً على degree_order (الأكثر موثوقية)
            if lt_model.degree_order == 1:
                return LicenseType.PRIVATE
            elif lt_model.degree_order == 2:
                return LicenseType.PUBLIC
            elif lt_model.degree_order == 3:
                return LicenseType.TRUCK
            elif lt_model.degree_order == 4:
                return LicenseType.BUS
            
            # محاولة 2: بناءً على اسم النوع (إذا كان يحتوي كلمات مفتاحية)
            name_lower = (lt_model.name or "").lower()
            if "أولى" in name_lower or "first" in name_lower or "private" in name_lower:
                return LicenseType.PRIVATE
            elif "ثاني" in name_lower or "second" in name_lower or "public" in name_lower:
                return LicenseType.PUBLIC
            elif "ثالث" in name_lower or "third" in name_lower or "truck" in name_lower:
                return LicenseType.TRUCK
            elif "رابع" in name_lower or "fourth" in name_lower or "bus" in name_lower:
                return LicenseType.BUS
            elif "عاهات" in name_lower or "disabled" in name_lower:
                return LicenseType.DISABLED
        except Exception:
            pass
        
        return None

    @staticmethod
    def get_validity_years(license_type: Optional[LicenseType]) -> int:
        """
        مدة صلاحية الرخصة حسب نوعها (حسب متطلبات النظام الحالية):
        - النوع الأول (PRIVATE): 10 سنوات
        - النوع الثاني (PUBLIC): 6 سنوات
        - النوع الثالث (TRUCK): 6 سنوات
        - النوع الرابع (BUS): 10 سنوات
        - ذوي العاهات (DISABLED): 3 سنوات
        - الأنواع القديمة/غير المعروفة: 10 سنوات (افتراضي)
        """
        if license_type == LicenseType.PUBLIC:
            return 6
        if license_type == LicenseType.TRUCK:
            return 6
        if license_type == LicenseType.BUS:
            return 10
        if license_type == LicenseType.DISABLED:
            return 3
        # PRIVATE أو غير معروف
        return 10

    @staticmethod
    def calculate_expiry_date(
        license_type: Optional[LicenseType] = None,
        issued_at: Optional[datetime] = None,
    ) -> date:
        """حساب تاريخ انتهاء صلاحية الرخصة حسب نوعها."""
        issued_date = (issued_at or datetime.now()).date()
        years = LicenseService.get_validity_years(license_type)
        return LicenseService._add_years(issued_date, years)

    @staticmethod
    def generate_license_number() -> str:
        prefix = "LIC"
        random_part = ''.join(random.choices(string.digits, k=8))
        return f"{prefix}{random_part}"
    
    @staticmethod
    def generate_barcode(license_number: str, user_id: int) -> str:
        """إنشاء باركود فريد للرخصة"""
        # استخدام hash لإنشاء باركود فريد
        data = f"{license_number}_{user_id}_{datetime.now().isoformat()}"
        hash_obj = hashlib.sha256(data.encode())
        barcode = hash_obj.hexdigest()[:16].upper()
        return barcode

    @staticmethod
    
    @staticmethod
    def get_license_by_barcode(db: Session, barcode: str) -> Optional[License]:
        """الحصول على الرخصة بالباركود"""
        lic = db.query(License).filter(License.barcode == barcode).first()
        if LicenseService.refresh_expired_status(db, lic):
            db.commit()
            db.refresh(lic)
        return lic

    @staticmethod
    def get_license_by_number(db: Session, license_number: str) -> Optional[License]:
        """الحصول على الرخصة برقم الرخصة"""
        return db.query(License).filter(License.license_number == license_number).first()
    
    @staticmethod
    def calculate_age(birth_date: date) -> int:
        """حساب العمر من تاريخ الميلاد"""
        today = date.today()
        age = today.year - birth_date.year
        # التحقق من أن عيد الميلاد قد مر هذا العام
        if today.month < birth_date.month or (today.month == birth_date.month and today.day < birth_date.day):
            age -= 1
        return age
    
    @staticmethod
    def create_license_application(db: Session, user_id: int, license_data: LicenseCreate) -> License:
        # تحديد نوع الرخصة المطلوبة
        selected_license_type_id: Optional[int] = getattr(license_data, "license_type_id", None)
        legacy_type: Optional[LicenseType] = getattr(license_data, "license_type", None)
        
        # التحقق من وجود رخصة سارية المفعول لنفس النوع
        today = date.today()
        active_license_query = db.query(License).filter(
            License.user_id == user_id,
            License.status == LicenseStatus.ISSUED,
            (License.expiry_date == None) | (License.expiry_date >= today)
        )
        
        # إذا كان هناك نوع محدد، نتحقق من نفس النوع
        if selected_license_type_id:
            active_license = active_license_query.filter(
                License.license_type_id == selected_license_type_id
            ).first()
            if active_license:
                raise ValueError("لديك رخصة سارية المفعول من هذا النوع. إذا فقدت الرخصة، يرجى التوجه إلى قسم بدل الفاقد")
        elif legacy_type:
            active_license = active_license_query.filter(
                License.license_type == legacy_type
            ).first()
            if active_license:
                raise ValueError("لديك رخصة سارية المفعول من هذا النوع. إذا فقدت الرخصة، يرجى التوجه إلى قسم بدل الفاقد")
        else:
            # إذا لم يكن هناك نوع محدد، نتحقق من أي رخصة سارية
            active_license = active_license_query.first()
            if active_license:
                raise ValueError("لديك رخصة سارية المفعول. إذا فقدت الرخصة، يرجى التوجه إلى قسم بدل الفاقد")
        
        # التحقق من وجود طلب قائم لنفس النوع
        existing_license_query = db.query(License).filter(
            License.user_id == user_id,
            License.status.in_([LicenseStatus.PENDING, LicenseStatus.EXAM_PASSED, LicenseStatus.APPROVED])
        )
        
        if selected_license_type_id:
            existing_license = existing_license_query.filter(
                License.license_type_id == selected_license_type_id
            ).first()
            if existing_license:
                raise ValueError("لديك طلب رخصة قائم بالفعل من هذا النوع")
        elif legacy_type:
            existing_license = existing_license_query.filter(
                License.license_type == legacy_type
            ).first()
            if existing_license:
                raise ValueError("لديك طلب رخصة قائم بالفعل من هذا النوع")
        else:
            existing_license = existing_license_query.first()
            if existing_license:
                raise ValueError("لديك طلب رخصة قائم بالفعل")
        
        # التحقق من وجود طلب مرفوض مؤخراً (خلال أسبوع)
        from datetime import timedelta
        week_ago = datetime.now() - timedelta(days=7)
        recent_rejected = db.query(License).filter(
            License.user_id == user_id,
            License.status == LicenseStatus.REJECTED,
            License.review_date >= week_ago
        ).first()
        
        if recent_rejected:
            days_left = 7 - (datetime.now() - recent_rejected.review_date).days
            raise ValueError(f"لا يمكن إعادة الطلب إلا بعد أسبوع من تاريخ الرفض. متبقي {days_left} يوم/أيام")
        
        # حساب العمر من تاريخ الميلاد
        age = LicenseService.calculate_age(license_data.birth_date)
        
        # === النظام الجديد: نوع الرخصة من جدول ===
        selected_license_type_id: Optional[int] = getattr(license_data, "license_type_id", None)
        selected_category: Optional[str] = getattr(license_data, "license_category", None)
        
        degree_order = None  # للتحقق من العمر حسب الدرجة

        if selected_license_type_id:
            lt = (
                db.query(LicenseTypeModel)
                .filter(LicenseTypeModel.id == selected_license_type_id, LicenseTypeModel.is_active == True)
                .first()
            )
            if not lt:
                raise ValueError("نوع الرخصة غير موجود أو غير مفعل")
            
            degree_order = lt.degree_order

            # إن كان النوع يحتوي فئات، يجب اختيار A/B
            if lt.has_categories:
                if not selected_category or not str(selected_category).strip():
                    raise ValueError("يرجى اختيار فئة الرخصة (A أو B)")
                code = str(selected_category).strip().upper()
                if code not in {"A", "B"}:
                    raise ValueError("فئة الرخصة غير صحيحة (A أو B)")
                # تحقق أن الفئة موجودة في الجدول
                if not any((c.code or "").strip().upper() == code for c in (lt.categories or [])):
                    raise ValueError("الفئة المختارة غير متاحة لهذا النوع")
                selected_category = code
            else:
                selected_category = None

        # === النظام القديم (للتوافق) ===
        legacy_type: Optional[LicenseType] = getattr(license_data, "license_type", None)
        
        if not selected_license_type_id and not legacy_type:
            raise ValueError("يرجى اختيار نوع الرخصة")
        
        # التحقق من العمر حسب الدرجة
        if degree_order is not None:
            if degree_order == 2:
                # الدرجة الثانية: 21 عام وما فوق
                if age < 21:
                    raise ValueError("يجب أن يكون عمرك 21 سنة على الأقل للحصول على رخصة الدرجة الثانية")
            elif degree_order == 3:
                # الدرجة الثالثة: 28 عام بالضبط
                if age != 28:
                    raise ValueError("يجب أن يكون عمرك 28 سنة بالضبط للحصول على رخصة الدرجة الثالثة")
            elif degree_order == 4:
                # الدرجة الرابعة: 28 عام وما فوق
                if age < 28:
                    raise ValueError("يجب أن يكون عمرك 28 سنة على الأقل للحصول على رخصة الدرجة الرابعة")
            else:
                # الدرجة الأولى أو غير محدد: 18 عام (الافتراضي)
                if age < 18:
                    raise ValueError("يجب أن يكون عمرك 18 سنة على الأقل للحصول على رخصة قيادة")
        else:
            # إذا لم يكن هناك degree_order (النظام القديم)، نستخدم 18 عام
            if age < 18:
                raise ValueError("يجب أن يكون عمرك 18 سنة على الأقل للحصول على رخصة قيادة")

        # تحديد license_type النهائي للتوافق مع النظام القديم والاستعلامات:
        # 1. إذا كان legacy_type محدداً (النظام القديم)، نستخدمه
        # 2. إذا كان license_type_id محدداً، نحاول استنتاجه من degree_order أو اسم النوع
        # 3. إذا فشل كل شيء، نستخدم PRIVATE كافتراضي
        final_license_type = legacy_type
        if not final_license_type and selected_license_type_id:
            final_license_type = LicenseService._infer_license_type_from_license_type_id(db, selected_license_type_id)
        if not final_license_type:
            final_license_type = LicenseType.PRIVATE  # افتراضي للتوافق
        
        db_license = License(
            user_id=user_id,
            # نحتفظ بـ license_type القديم لأغراض التوافق مع الرخص القديمة والاستعلامات
            license_type=final_license_type,
            license_type_id=selected_license_type_id,
            license_category=selected_category,
            full_name=license_data.full_name,
            birth_date=license_data.birth_date,
            age=age,
            gender=license_data.gender,
            passport_number=license_data.passport_number,
            nationality=license_data.nationality,
            blood_type=license_data.blood_type,
            place_of_birth=(license_data.place_of_birth.strip() if getattr(license_data, "place_of_birth", None) else None),
            residence_address=(license_data.residence_address.strip() if getattr(license_data, "residence_address", None) else None),
            email=license_data.email,
            photo_path=license_data.photo_path,
            residence_certificate_path=license_data.residence_certificate_path,
            birth_certificate_path=license_data.birth_certificate_path,
            passport_image_path=license_data.passport_image_path,
            status=LicenseStatus.PENDING
        )
        db.add(db_license)
        db.commit()
        db.refresh(db_license)
        return db_license
    
    @staticmethod
    def get_license_by_id(db: Session, license_id: int) -> Optional[License]:
        lic = db.query(License).filter(License.id == license_id).first()
        if LicenseService.refresh_expired_status(db, lic):
            db.commit()
            db.refresh(lic)
        return lic
    
    @staticmethod
    def get_user_licenses(db: Session, user_id: int) -> List[License]:
        licenses = db.query(License).filter(License.user_id == user_id).all()
        if LicenseService.refresh_expired_status_for_list(db, licenses):
            db.commit()
            for l in licenses:
                try:
                    db.refresh(l)
                except Exception:
                    pass
        return licenses
    
    @staticmethod
    def get_pending_licenses(db: Session) -> List[License]:
        return db.query(License).filter(License.status == LicenseStatus.PENDING).order_by(License.application_date.asc()).all()
    
    @staticmethod
    def get_all_licenses_for_officer(db: Session, license_type: Optional[str] = None) -> List[License]:
        """الحصول على جميع الرخص لمسؤول الرخص (مصنفة حسب النوع)"""
        query = db.query(License).filter(
            License.status.in_([
                LicenseStatus.PENDING,
                LicenseStatus.EXAM_PASSED,
                LicenseStatus.EXAM_FAILED,
                LicenseStatus.APPROVED
            ])
        )
        
        if license_type:
            from app.models.enums import LicenseType
            try:
                lt = LicenseType(license_type)
                query = query.filter(License.license_type == lt)
            except ValueError:
                pass
        
        return query.order_by(License.application_date.asc()).all()

    @staticmethod
    def get_printable_licenses_for_officer(db: Session) -> List[License]:
        """الرخص القابلة للطباعة لمسؤول الرخص (الرخص الصادرة فقط)"""
        query = db.query(License).filter(
            License.status == LicenseStatus.ISSUED,
            (License.dept_approval_approved == 1) | (License.dept_approval_approved == None),
        )
        licenses = query.order_by(License.issued_date.desc().nullslast(), License.application_date.desc()).all()

        # ضمان وجود barcode للرخص القديمة (قبل إضافة الميزة)
        changed = False
        for l in licenses:
            if not l.license_number:
                continue
            if not l.barcode:
                l.barcode = LicenseService.generate_barcode(l.license_number, l.user_id)
                changed = True
        if changed:
            db.commit()
            for l in licenses:
                db.refresh(l)
        return licenses
    
    @staticmethod
    def review_license(db: Session, license_id: int, review_data: LicenseReview, actor_user_id: Optional[int] = None) -> Optional[License]:
        db_license = db.query(License).filter(License.id == license_id).first()
        if not db_license:
            return None
        
        # التحقق من وجود سبب الرفض عند رفض الرخصة
        if review_data.status == LicenseStatus.REJECTED:
            if not review_data.rejection_reason or not review_data.rejection_reason.strip():
                raise ValueError("يجب إدخال سبب الرفض")
            db_license.rejection_reason = review_data.rejection_reason.strip()
        
        db_license.status = review_data.status
        db_license.review_date = datetime.now()
        if review_data.review_notes:
            db_license.review_notes = review_data.review_notes
        
        # إرسال إشعار عند قبول الطلب
        if review_data.status == LicenseStatus.APPROVED:
            try:
                from app.services.fcm_service import FCMService
                notification_sent = FCMService.send_notification_to_user(
                    user_id=db_license.user_id,
                    title="تمت مراجعة الطلب",
                    body="تمت مراجعة الطلب والبيانات صحيحة. انتظر حتى يتم تحديد موعد الامتحانات",
                    data={
                        "type": "license_approved",
                        "license_id": str(db_license.id)
                    },
                    db=db
                )
                if not notification_sent:
                    print(f"ℹ️ License {license_id} approved, but notification not sent (user may not have FCM token yet)")
            except Exception as e:
                print(f"⚠️ Failed to send notification: {e}")
        
        if review_data.status == LicenseStatus.APPROVED:
            # قبول الطلب - لا يتطلب امتحانات
            # التحقق من الامتحانات يتم عند إصدار الرخصة فقط
            from app.features.exam.service import ExamService
            exams = ExamService.get_license_exams(db, license_id)
            passed_exams = [e for e in exams if e.result == "passed"]
            
            # إذا كان هناك 3 امتحانات ناجحة، يمكن إصدار الرخصة مباشرة
            if len(passed_exams) >= 3:
                if not db_license.license_number:
                    db_license.license_number = LicenseService.generate_license_number()
                if not db_license.barcode:
                    db_license.barcode = LicenseService.generate_barcode(db_license.license_number, db_license.user_id)
                db_license.issued_date = datetime.now()
                if actor_user_id:
                    db_license.issued_by_user_id = actor_user_id
                # صلاحية حسب الجدول إذا متاح
                if db_license.license_type_id:
                    lt = db.query(LicenseTypeModel).filter(LicenseTypeModel.id == db_license.license_type_id).first()
                    years = int(lt.validity_years) if lt else LicenseService.get_validity_years(db_license.license_type)
                    db_license.expiry_date = LicenseService._add_years(db_license.issued_date.date(), years)
                else:
                    db_license.expiry_date = LicenseService.calculate_expiry_date(db_license.license_type, db_license.issued_date)
                db_license.status = LicenseStatus.ISSUED
                
                # إرسال إشعار عند إصدار الرخصة
                try:
                    from app.services.fcm_service import FCMService
                    FCMService.send_notification_to_user(
                        user_id=db_license.user_id,
                        title="تم إصدار الرخصة",
                        body=f"تهانينا! تم إصدار رخصتك برقم {db_license.license_number}",
                        data={
                            "type": "license_issued",
                            "license_id": str(db_license.id),
                            "license_number": db_license.license_number
                        },
                        db=db
                    )
                except Exception as e:
                    print(f"⚠️ Failed to send notification: {e}")
            # إذا لم يكن هناك 3 امتحانات، نقبل الطلب فقط (APPROVED)
            # الرخصة ستُصدر لاحقاً بعد اجتياز 3 امتحانات
        
        db.commit()
        db.refresh(db_license)
        return db_license

