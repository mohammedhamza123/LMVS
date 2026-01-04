"""
سكريبت لإنشاء حساب admin مباشرة
"""
import sys
import io
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, Base, engine
from app.models.user import User
from app.models.license import License
from app.models.exam import Exam
from app.models.violation import Violation
from app.models.exam_type import ExamType
from app.models.enums import UserRole
from app.core.security import get_password_hash

# استيراد جميع النماذج لضمان تهيئة العلاقات
from app.models import user, license, exam, violation, exam_type

# إصلاح مشكلة encoding في Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def create_admin():
    db: Session = SessionLocal()
    
    try:
        # بيانات admin الافتراضية
        admin_data = {
            'national_id': 'admin',
            'phone': '1234567890',
            'password': 'admin123',
            'role': UserRole.SUPER_ADMIN
        }
        
        print("=" * 50)
        print("إنشاء حساب Admin")
        print("=" * 50)
        
        # التحقق من وجود admin
        existing_admin = db.query(User).filter(User.national_id == admin_data['national_id']).first()
        if existing_admin:
            print("حساب Admin موجود بالفعل!")
            print(f"   الرقم الوطني: {existing_admin.national_id}")
            print(f"   الدور: {existing_admin.role.value}")
            choice = input("\nهل تريد تحديث كلمة المرور؟ (y/n): ").strip().lower()
            if choice == 'y':
                new_password = input("أدخل كلمة المرور الجديدة: ").strip()
                if new_password:
                    existing_admin.password_hash = get_password_hash(new_password)
                    db.commit()
                    print("تم تحديث كلمة المرور بنجاح!")
                else:
                    print("كلمة المرور فارغة!")
            return
        
        # إنشاء admin
        hashed_password = get_password_hash(admin_data['password'])
        admin = User(
            national_id=admin_data['national_id'],
            phone=admin_data['phone'],
            password_hash=hashed_password,
            role=admin_data['role'],
            is_active=True
        )
        
        db.add(admin)
        db.commit()
        db.refresh(admin)
        
        print("\nتم إنشاء حساب Admin بنجاح!")
        print("=" * 50)
        print("بيانات تسجيل الدخول:")
        print(f"   الرقم الوطني: {admin.national_id}")
        print(f"   كلمة المرور: {admin_data['password']}")
        print(f"   الدور: {admin.role.value}")
        print("=" * 50)
        print("\nيرجى تغيير كلمة المرور بعد تسجيل الدخول الأول!")
        
    except Exception as e:
        print(f"حدث خطأ: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_admin()
