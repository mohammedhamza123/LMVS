from sqlalchemy.orm import Session
from app.features.exam.model import Exam
from app.features.license.model import License
from app.features.exam.schema import ExamCreate, ExamResult, ExamSchedule
from app.features.exam_type.model import ExamType
from app.models.enums import LicenseStatus
from datetime import datetime
from typing import Optional, List

class ExamService:
    @staticmethod
    def create_exam(db: Session, exam_data: ExamCreate, examiner_id: int) -> Exam:
        """إنشاء امتحان جديد"""
        db_exam = Exam(
            user_id=exam_data.user_id,
            license_id=exam_data.license_id,
            exam_type_id=exam_data.exam_type_id,
            created_by_user_id=examiner_id
        )
        db.add(db_exam)
        db.commit()
        db.refresh(db_exam)
        return db_exam
    
    @staticmethod
    def schedule_exam(
        db: Session,
        exam_id: int,
        schedule_data: ExamSchedule,
        scheduler_id: int,
        user_role: Optional[str] = None,
    ) -> Optional[Exam]:
        """تحديد موعد الامتحان - فقط لمسؤولي الرخص والامتحانات"""
        # حماية إضافية: التأكد من أن المستخدم ليس مواطن
        if user_role and user_role == "citizen":
            raise ValueError("ليس لديك صلاحية لتحديد موعد امتحان. فقط مسؤولي الرخص والامتحانات يمكنهم تحديد المواعيد.")
        
        db_exam = db.query(Exam).filter(Exam.id == exam_id).first()
        if not db_exam:
            return None
        
        db_exam.scheduled_date = schedule_data.scheduled_date
        db_exam.scheduled_by_user_id = scheduler_id
        db.commit()
        db.refresh(db_exam)
        
        # إرسال إشعار عند تحديد موعد الامتحان
        try:
            from app.services.fcm_service import FCMService
            
            # الحصول على نوع الامتحان
            exam_type = None
            if db_exam.exam_type_id:
                exam_type = db.query(ExamType).filter(ExamType.id == db_exam.exam_type_id).first()
            
            exam_type_name = exam_type.name if exam_type else "الامتحان"
            scheduled_date_str = schedule_data.scheduled_date.strftime("%Y-%m-%d %H:%M")
            
            # المبلغ الثابت للامتحان: 10.5 دينار
            exam_fee = 10.5
            
            FCMService.send_notification_to_user(
                user_id=db_exam.user_id,
                title="تم تحديد موعد الامتحان",
                body=f"تم تحديد موعد {exam_type_name} في {scheduled_date_str}. يرجى الحضور في الموعد المحدد ودفع مبلغ {exam_fee} دينار عند الحضور.",
                data={
                    "type": "exam_scheduled",
                    "exam_id": str(db_exam.id),
                    "scheduled_date": schedule_data.scheduled_date.isoformat(),
                    "exam_fee": str(exam_fee)
                },
                db=db
            )
        except Exception as e:
            print(f"⚠️ Failed to send notification: {e}")
        
        return db_exam
    
    @staticmethod
    def get_license_exams(db: Session, license_id: int) -> List[Exam]:
        """الحصول على جميع امتحانات الرخصة"""
        return db.query(Exam).filter(Exam.license_id == license_id).order_by(Exam.created_at.asc()).all()
    
    @staticmethod
    def get_exam_by_id(db: Session, exam_id: int) -> Optional[Exam]:
        """الحصول على امتحان بالمعرف"""
        return db.query(Exam).filter(Exam.id == exam_id).first()
    
    @staticmethod
    def get_user_exams(db: Session, user_id: int) -> List[Exam]:
        """الحصول على جميع امتحانات المستخدم"""
        return db.query(Exam).filter(Exam.user_id == user_id).all()
    
    @staticmethod
    def submit_exam_result(db: Session, exam_id: int, result_data: ExamResult, examiner_id: int) -> Optional[Exam]:
        """تسجيل نتيجة الامتحان"""
        db_exam = db.query(Exam).filter(Exam.id == exam_id).first()
        if not db_exam:
            return None
        
        db_exam.score = result_data.score
        db_exam.result = result_data.result
        db_exam.notes = result_data.notes
        db_exam.exam_date = datetime.now()
        db_exam.conducted_by = examiner_id
        
        # تسجيل الدفع تلقائياً عند رصد النتيجة (10.5 دينار)
        if not db_exam.paid_at:
            from decimal import Decimal
            db_exam.paid_at = datetime.now()
            db_exam.paid_by_user_id = examiner_id
            db_exam.paid_amount = Decimal("10.5")
            print(f"✓ Payment recorded for Exam ID: {exam_id}, Amount: 10.5 JOD, Paid by User ID: {examiner_id}")
        
        if db_exam.license_id:
            db_license = db.query(License).filter(License.id == db_exam.license_id).first()
            if db_license:
                # التحقق من جميع الامتحانات المطلوبة
                all_exams = ExamService.get_license_exams(db, db_exam.license_id)
                passed_exams = [e for e in all_exams if e.result == "passed"]
                failed_exams = [e for e in all_exams if e.result == "failed"]
                
                # إذا رسب في أي امتحان، نرفض الطلب
                if db_exam.result == "failed":
                    db_license.status = LicenseStatus.REJECTED
                    from datetime import timedelta
                    # منع إعادة الطلب لمدة أسبوع (نحفظ تاريخ الرفض في review_date)
                    db_license.review_date = datetime.now()
                    db_license.rejection_reason = f"رسب في امتحان {db_exam.exam_type_id}. لا يمكن إعادة الطلب إلا بعد أسبوع من تاريخ الرفض."
                
                # إذا نجح في جميع الامتحانات الثلاثة (3 امتحانات)
                exam_types = db.query(ExamType).filter(ExamType.is_active == True).all()
                if exam_types and len(exam_types) >= 3:
                    # التحقق من أن كل نوع امتحان قد نجح (3 امتحانات)
                    exam_type_ids = {et.id for et in exam_types[:3]}  # أول 3 أنواع
                    passed_exam_type_ids = {e.exam_type_id for e in passed_exams if e.exam_type_id}
                    
                    # إذا نجح في جميع الامتحانات الثلاثة
                    if exam_type_ids.issubset(passed_exam_type_ids) and len(passed_exams) >= 3:
                        # إنشاء الرخصة تلقائياً
                        from app.features.license.service import LicenseService
                        if not db_license.license_number:
                            db_license.license_number = LicenseService.generate_license_number()
                        if not db_license.barcode:
                            db_license.barcode = LicenseService.generate_barcode(db_license.license_number, db_license.user_id)
                        db_license.issued_date = datetime.now()
                        db_license.issued_by_user_id = examiner_id
                        # صلاحية حسب جدول license_types إن كانت موجودة
                        try:
                            from app.features.license_type.model import LicenseType as LicenseTypeModel

                            if getattr(db_license, "license_type_id", None):
                                lt = db.query(LicenseTypeModel).filter(LicenseTypeModel.id == db_license.license_type_id).first()
                                years = int(lt.validity_years) if lt else LicenseService.get_validity_years(db_license.license_type)
                                db_license.expiry_date = LicenseService._add_years(db_license.issued_date.date(), years)
                            else:
                                db_license.expiry_date = LicenseService.calculate_expiry_date(db_license.license_type, db_license.issued_date)
                        except Exception:
                            db_license.expiry_date = LicenseService.calculate_expiry_date(db_license.license_type, db_license.issued_date)
                        db_license.status = LicenseStatus.ISSUED
        
        db.commit()
        db.refresh(db_exam)
        
        # إرسال إشعار للمواطن عند رصد نتيجة الامتحان
        print(f"🔔 Attempting to send exam result notification for exam {db_exam.id} to user {db_exam.user_id}")
        try:
            from app.services.fcm_service import FCMService
            from app.features.user.model import User
            
            # التحقق من وجود المستخدم أولاً
            user = db.query(User).filter(User.id == db_exam.user_id).first()
            if not user:
                print(f"⚠️ User {db_exam.user_id} not found - cannot send notification")
            elif not user.fcm_token:
                print(f"⚠️ User {db_exam.user_id} (national_id: {user.national_id}) has no FCM token registered. User must login to the mobile app first to receive notifications.")
            else:
                # الحصول على نوع الامتحان
                exam_type = None
                exam_type_name = "الامتحان"
                if db_exam.exam_type_id:
                    exam_type = db.query(ExamType).filter(ExamType.id == db_exam.exam_type_id).first()
                    if exam_type:
                        exam_type_name = exam_type.name
                
                # إرسال إشعار مختلف حسب النتيجة
                if db_exam.result == "passed":
                    title = "تهانينا! نجحت في الامتحان"
                    body = f"تهانينا! لقد نجحت في {exam_type_name}. الدرجة: {db_exam.score if db_exam.score else 'ممتاز'}"
                    notification_type = "exam_passed"
                elif db_exam.result == "failed":
                    title = "نتيجة الامتحان"
                    body = f"للأسف، لم تنجح في {exam_type_name}. الدرجة: {db_exam.score if db_exam.score else 'غير متوفرة'}. يمكنك إعادة المحاولة لاحقاً."
                    notification_type = "exam_failed"
                else:
                    # حالة pending (غير محتمل لكن للاحتياط)
                    title = "تم تحديث حالة الامتحان"
                    body = f"تم تحديث حالة {exam_type_name}"
                    notification_type = "exam_updated"
                
                print(f"📱 User {db_exam.user_id} has FCM token - sending {db_exam.result} notification")
                notification_sent = FCMService.send_notification_to_user(
                    user_id=db_exam.user_id,
                    title=title,
                    body=body,
                    data={
                        "type": notification_type,
                        "exam_id": str(db_exam.id),
                        "exam_type": exam_type_name,
                        "result": db_exam.result,
                        "score": str(db_exam.score) if db_exam.score else None,
                        "exam_date": db_exam.exam_date.isoformat() if db_exam.exam_date else None,
                        "license_id": str(db_exam.license_id) if db_exam.license_id else None
                    },
                    db=db
                )
                if notification_sent:
                    print(f"✓ Exam result notification sent successfully to User ID: {db_exam.user_id} for exam {db_exam.id} (Result: {db_exam.result})")
                else:
                    print(f"✗ Failed to send exam result notification to User ID: {db_exam.user_id} for exam {db_exam.id}")
        except ImportError as e:
            print(f"⚠️ Failed to import FCMService: {e}")
            print(f"⚠️ Make sure FCM service is properly configured. Check if service-account.json exists.")
        except Exception as e:
            import traceback
            print(f"⚠️ Failed to send exam result notification: {e}")
            print(f"⚠️ Traceback: {traceback.format_exc()}")
        
        return db_exam
    
    @staticmethod
    def get_pending_exams(db: Session) -> List[Exam]:
        """الحصول على الامتحانات المعلقة"""
        return db.query(Exam).filter(Exam.result == None).all()

