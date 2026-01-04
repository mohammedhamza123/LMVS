from sqlalchemy.orm import Session
from sqlalchemy import func
from app.features.violation.model import Violation
from app.features.violation.schema import ViolationCreate, ViolationUpdate
from app.models.enums import ViolationStatus
from typing import Optional, List, Dict
from datetime import datetime
from decimal import Decimal
import random
import string

from app.features.violation_type.model import ViolationType

class ViolationService:
    @staticmethod
    def generate_violation_number() -> str:
        """إنشاء رقم مخالفة فريد"""
        prefix = "VIO"
        random_part = ''.join(random.choices(string.digits, k=8))
        return f"{prefix}{random_part}"
    
    @staticmethod
    def create_violation(db: Session, violation_data: ViolationCreate, officer_id: int) -> Violation:
        """إنشاء مخالفة جديدة"""

        # Resolve violation type relationship:
        vt: Optional[ViolationType] = None
        if getattr(violation_data, "violation_type_id", None) is not None:
            vt = db.query(ViolationType).filter(ViolationType.id == violation_data.violation_type_id).first()
            if not vt:
                raise ValueError("نوع المخالفة غير موجود")
            if hasattr(vt, "is_active") and not vt.is_active:
                raise ValueError("نوع المخالفة غير نشط")
        else:
            # Backward compatible path: lookup (or create) by name
            vt_name = (violation_data.violation_type or "").strip()
            vt = db.query(ViolationType).filter(ViolationType.name == vt_name).first()
            if not vt:
                if violation_data.fine_amount is None:
                    raise ValueError("يجب إرسال fine_amount عند إنشاء نوع مخالفة جديد بالاسم")
                vt = ViolationType(
                    name=vt_name,
                    description=None,
                    fine_amount=violation_data.fine_amount,
                    is_active=True,
                )
                db.add(vt)
                db.commit()
                db.refresh(vt)
            elif hasattr(vt, "is_active") and not vt.is_active:
                raise ValueError("نوع المخالفة غير نشط")

        # Always store both FK and display name (for older clients / readability)
        violation_type_id = vt.id if vt else None
        violation_type_name = vt.name if vt else (violation_data.violation_type or "")
        fine_amount = vt.fine_amount if vt and hasattr(vt, "fine_amount") else (violation_data.fine_amount or 0)

        db_violation = Violation(
            user_id=violation_data.user_id,
            license_id=violation_data.license_id,
            violation_number=ViolationService.generate_violation_number(),
            violation_type_id=violation_type_id,
            violation_type=violation_type_name,
            description=violation_data.description,
            location=violation_data.location,
            violation_date=violation_data.violation_date,
            fine_amount=fine_amount,
            created_by=officer_id,
            created_at=datetime.now()
        )
        db.add(db_violation)
        db.commit()
        db.refresh(db_violation)
        
        # إرسال إشعار للمواطن عند إضافة المخالفة
        print(f"🔔 Attempting to send violation notification for violation {db_violation.id} to user {violation_data.user_id}")
        try:
            from app.services.fcm_service import FCMService
            from app.features.user.model import User
            
            # التحقق من وجود المستخدم أولاً
            user = db.query(User).filter(User.id == violation_data.user_id).first()
            if not user:
                print(f"⚠️ User {violation_data.user_id} not found - cannot send notification")
            elif not user.fcm_token:
                print(f"⚠️ User {violation_data.user_id} (national_id: {user.national_id}) has no FCM token registered. User must login to the mobile app first to receive notifications.")
            else:
                print(f"📱 User {violation_data.user_id} has FCM token - proceeding with notification")
                notification_sent = FCMService.send_notification_to_user(
                    user_id=violation_data.user_id,
                    title="تم إضافة مخالفة جديدة",
                    body=f"تم إضافة مخالفة جديدة برقم {db_violation.violation_number}. نوع المخالفة: {violation_type_name}. المبلغ: {fine_amount} دينار",
                    data={
                        "type": "violation_created",
                        "violation_id": str(db_violation.id),
                        "violation_number": db_violation.violation_number,
                        "violation_type": violation_type_name,
                        "fine_amount": str(fine_amount),
                        "location": violation_data.location,
                        "violation_date": violation_data.violation_date.isoformat() if isinstance(violation_data.violation_date, datetime) else str(violation_data.violation_date)
                    },
                    db=db
                )
                if notification_sent:
                    print(f"✓ Violation notification sent successfully to User ID: {violation_data.user_id} for violation {db_violation.id} ({db_violation.violation_number})")
                else:
                    print(f"✗ Failed to send violation notification to User ID: {violation_data.user_id} for violation {db_violation.id}")
        except ImportError as e:
            print(f"⚠️ Failed to import FCMService: {e}")
            print(f"⚠️ Make sure FCM service is properly configured. Check if service-account.json exists.")
        except Exception as e:
            import traceback
            print(f"⚠️ Failed to send violation notification: {e}")
            print(f"⚠️ Traceback: {traceback.format_exc()}")
        
        return db_violation
    
    @staticmethod
    def get_violation_by_id(db: Session, violation_id: int) -> Optional[Violation]:
        """الحصول على مخالفة بالمعرف"""
        return db.query(Violation).filter(Violation.id == violation_id).first()
    
    @staticmethod
    def get_user_violations(db: Session, user_id: int) -> List[Violation]:
        """الحصول على جميع مخالفات المستخدم"""
        return db.query(Violation).filter(Violation.user_id == user_id).all()
    
    @staticmethod
    def get_all_violations(db: Session, status: Optional[ViolationStatus] = None) -> List[Violation]:
        """الحصول على جميع المخالفات"""
        query = db.query(Violation)
        if status:
            query = query.filter(Violation.status == status)
        return query.all()
    
    @staticmethod
    def update_violation(db: Session, violation_id: int, violation_data: ViolationUpdate) -> Optional[Violation]:
        """تحديث مخالفة"""
        db_violation = db.query(Violation).filter(Violation.id == violation_id).first()
        if not db_violation:
            return None
        
        update_data = violation_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_violation, field, value)
        
        if violation_data.status == ViolationStatus.PAID and not db_violation.paid_at:
            db_violation.paid_at = datetime.now()
        
        db.commit()
        db.refresh(db_violation)
        return db_violation

    @staticmethod
    def mark_paid(db: Session, violation_id: int, paid_by_user_id: int) -> Optional[Violation]:
        db_violation = db.query(Violation).filter(Violation.id == violation_id).first()
        if not db_violation:
            return None

        if db_violation.status != ViolationStatus.PAID:
            db_violation.status = ViolationStatus.PAID
        if not db_violation.paid_at:
            db_violation.paid_at = datetime.now()
        db_violation.paid_by_user_id = paid_by_user_id

        db.commit()
        db.refresh(db_violation)
        
        # إرسال إشعار للمواطن الذي دفع المخالفة
        try:
            from app.services.fcm_service import FCMService
            from app.features.user.model import User
            
            # التحقق من وجود المستخدم وFCM token
            user = db.query(User).filter(User.id == db_violation.user_id).first()
            if not user:
                print(f"⚠️ User {db_violation.user_id} not found for violation {db_violation.id}")
            elif not user.fcm_token:
                print(f"⚠️ User {db_violation.user_id} (national_id: {user.national_id}) has no FCM token. User must login to the app first.")
            else:
                print(f"📤 Attempting to send payment notification to User ID: {db_violation.user_id}, FCM Token: {user.fcm_token[:20]}...")
                notification_sent = FCMService.send_notification_to_user(
                    user_id=db_violation.user_id,
                    title="تم دفع المخالفة بنجاح",
                    body=f"تم دفع المخالفة رقم {db_violation.violation_number} بنجاح. المبلغ: {db_violation.fine_amount} دينار",
                    data={
                        "type": "violation_paid",
                        "violation_id": str(db_violation.id),
                        "violation_number": db_violation.violation_number,
                        "fine_amount": str(db_violation.fine_amount),
                        "payment_date": db_violation.paid_at.isoformat() if db_violation.paid_at else None
                    },
                    db=db
                )
                if notification_sent:
                    print(f"✓ Payment notification sent successfully to User ID: {db_violation.user_id} for violation {db_violation.id}")
                else:
                    print(f"✗ Failed to send payment notification to User ID: {db_violation.user_id} for violation {db_violation.id}")
        except ImportError as e:
            print(f"⚠️ Failed to import FCMService: {e}")
        except Exception as e:
            import traceback
            print(f"⚠️ Failed to send payment notification: {e}")
            print(f"⚠️ Traceback: {traceback.format_exc()}")
        
        return db_violation

    @staticmethod
    def cancel_violation(db: Session, violation_id: int, officer_id: int, cancellation_reason: str) -> Optional[Violation]:
        """إلغاء مخالفة مع تسجيل السبب ومن قام بالإلغاء"""
        db_violation = db.query(Violation).filter(Violation.id == violation_id).first()
        if not db_violation:
            return None
        
        if db_violation.status == ViolationStatus.PAID:
            raise ValueError("لا يمكن إلغاء مخالفة مدفوعة")
        
        db_violation.status = ViolationStatus.CANCELLED
        db_violation.cancelled_at = datetime.now()
        db_violation.cancelled_by_user_id = officer_id
        db_violation.cancellation_reason = cancellation_reason
        
        db.commit()
        db.refresh(db_violation)
        return db_violation

    @staticmethod
    def modify_violation(
        db: Session, 
        violation_id: int, 
        officer_id: int, 
        modification_data: dict,
        modification_reason: str
    ) -> Optional[Violation]:
        """تعديل مخالفة (فقط قبل الدفع) مع تسجيل السبب ومن قام بالتعديل"""
        db_violation = db.query(Violation).filter(Violation.id == violation_id).first()
        if not db_violation:
            return None
        
        if db_violation.status == ViolationStatus.PAID:
            raise ValueError("لا يمكن تعديل مخالفة مدفوعة")
        
        # تحديث الحقول
        if 'description' in modification_data and modification_data['description']:
            db_violation.description = modification_data['description']
        if 'location' in modification_data and modification_data['location']:
            db_violation.location = modification_data['location']
        if 'violation_type_id' in modification_data and modification_data['violation_type_id']:
            vt = db.query(ViolationType).filter(ViolationType.id == modification_data['violation_type_id']).first()
            if vt:
                db_violation.violation_type_id = vt.id
                db_violation.violation_type = vt.name
                db_violation.fine_amount = vt.fine_amount
        if 'fine_amount' in modification_data and modification_data['fine_amount']:
            db_violation.fine_amount = modification_data['fine_amount']
        
        db_violation.modified_at = datetime.now()
        db_violation.modified_by_user_id = officer_id
        db_violation.modification_reason = modification_reason
        
        db.commit()
        db.refresh(db_violation)
        return db_violation

    @staticmethod
    def get_violation_statistics(
        db: Session,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        officer_id: Optional[int] = None
    ) -> Dict:
        """الحصول على إحصائيات المخالفات"""
        query = db.query(Violation)
        
        # فلترة حسب التاريخ
        if start_date:
            query = query.filter(Violation.created_at >= start_date)
        if end_date:
            query = query.filter(Violation.created_at <= end_date)
        if officer_id:
            query = query.filter(Violation.created_by == officer_id)
        
        all_violations = query.all()
        
        total = len(all_violations)
        pending = len([v for v in all_violations if v.status == ViolationStatus.PENDING])
        paid = len([v for v in all_violations if v.status == ViolationStatus.PAID])
        cancelled = len([v for v in all_violations if v.status == ViolationStatus.CANCELLED])
        
        total_amount = sum(Decimal(str(v.fine_amount)) for v in all_violations)
        paid_amount = sum(Decimal(str(v.fine_amount)) for v in all_violations if v.status == ViolationStatus.PAID)
        pending_amount = sum(Decimal(str(v.fine_amount)) for v in all_violations if v.status == ViolationStatus.PENDING)
        
        return {
            "total_violations": total,
            "pending_violations": pending,
            "paid_violations": paid,
            "cancelled_violations": cancelled,
            "total_amount": Decimal(str(total_amount)),
            "paid_amount": Decimal(str(paid_amount)),
            "pending_amount": Decimal(str(pending_amount)),
            "period_start": start_date,
            "period_end": end_date,
        }














