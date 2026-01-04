from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine, Base, SessionLocal
from app.api.v1 import api_router
from app.features.user.model import User
from app.features.license.model import License
from app.features.exam.model import Exam
from app.features.violation.model import Violation
from app.features.violation_type.model import ViolationType
from app.features.exam_type.model import ExamType
from app.features.license_renewal.model import LicenseRenewal
from app.features.license_replacement.model import LicenseReplacement
from app.models.enums import UserRole
from app.core.security import get_password_hash

# ترحيل تلقائي (SQLite): ربط violations بجدول violation_types كمفتاح أجنبي حقيقي
def run_sqlite_migrations_if_needed():
    try:
        if "sqlite" not in settings.DATABASE_URL.lower():
            return

        import sqlite3
        from pathlib import Path

        # استخراج مسار ملف sqlite من DATABASE_URL
        db_url = settings.DATABASE_URL
        db_file = "license_system.db"
        if db_url.startswith("sqlite:///"):
            db_file = db_url.replace("sqlite:///", "", 1)
        db_path = Path(db_file)

        if not db_path.exists():
            return

        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        try:
            # ========== Migration: licenses public profile fields ==========
            cur.execute("PRAGMA table_info(licenses)")
            license_cols = [r[1] for r in cur.fetchall()]
            needs_public_profile_cols = any(
                c not in license_cols
                for c in [
                    "chronic_disease",
                    "emergency_contact_name",
                    "emergency_contact_phone",
                ]
            )
            if needs_public_profile_cols:
                from migrate_license_public_profile import migrate

                print("Running DB migration: licenses public profile columns ...")
                migrate(db_path)

            # ========== Migration: license types tables + columns ==========
            try:
                from migrate_license_types import migrate as migrate_license_types

                # نتحقق بطريقة بسيطة: هل جدول license_types موجود؟
                row = cur.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='license_types'"
                ).fetchone()
                if not row:
                    print("Running DB migration: license_types tables ...")
                    migrate_license_types(db_path)
            except Exception as e:
                print(f"Migration warning (license_types): {e}")

            # ========== Migration: users suspension fields ==========
            try:
                cur.execute("PRAGMA table_info(users)")
                user_cols = [r[1] for r in cur.fetchall()]
                if "suspended_until" not in user_cols or "suspension_reason" not in user_cols:
                    from migrate_user_suspension import migrate as migrate_user_suspension

                    print("Running DB migration: users suspension columns ...")
                    migrate_user_suspension(db_path)
            except Exception as e:
                print(f"Migration warning (users suspension): {e}")

            # ========== Migration: licenses audit fields ==========
            try:
                cur.execute("PRAGMA table_info(licenses)")
                license_cols2 = [r[1] for r in cur.fetchall()]
                if "issued_by_user_id" not in license_cols2:
                    from migrate_license_audit import migrate as migrate_license_audit

                    print("Running DB migration: licenses audit columns ...")
                    migrate_license_audit(db_path)
            except Exception as e:
                print(f"Migration warning (licenses audit): {e}")

            # ========== Migration: licenses department approval/signature fields ==========
            try:
                cur.execute("PRAGMA table_info(licenses)")
                license_cols3 = [r[1] for r in cur.fetchall()]
                if "dept_approval_requested" not in license_cols3 or "dept_approval_approved" not in license_cols3:
                    from migrate_license_dept_approval import migrate as migrate_license_dept_approval

                    print("Running DB migration: licenses dept approval fields ...")
                    migrate_license_dept_approval(db_path)
            except Exception as e:
                print(f"Migration warning (licenses dept approval): {e}")

            # ========== Migration: licenses signature_image_path ==========
            try:
                cur.execute("PRAGMA table_info(licenses)")
                license_cols4 = [r[1] for r in cur.fetchall()]
                if "signature_image_path" not in license_cols4:
                    from migrate_license_signature import migrate as migrate_license_signature

                    print("Running DB migration: licenses signature_image_path ...")
                    migrate_license_signature(db_path)
            except Exception as e:
                print(f"Migration warning (licenses signature_image_path): {e}")

            # ========== Migration: license_replacements barcode snapshot fields ==========
            try:
                row = cur.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='license_replacements'"
                ).fetchone()
                if row:
                    cur.execute("PRAGMA table_info(license_replacements)")
                    rep_cols = [r[1] for r in cur.fetchall()]
                    if "old_barcode" not in rep_cols or "new_barcode" not in rep_cols:
                        from migrate_license_replacements_barcode_snapshot import (
                            migrate as migrate_license_replacements_barcode_snapshot,
                        )

                        print("Running DB migration: license_replacements barcode snapshot fields ...")
                        migrate_license_replacements_barcode_snapshot(db_path)
            except Exception as e:
                print(f"Migration warning (license_replacements snapshot): {e}")

            # ========== Migration: exams audit fields ==========
            try:
                cur.execute("PRAGMA table_info(exams)")
                exam_cols = [r[1] for r in cur.fetchall()]
                if "created_by_user_id" not in exam_cols or "scheduled_by_user_id" not in exam_cols:
                    from migrate_exam_audit import migrate as migrate_exam_audit

                    print("Running DB migration: exams audit columns ...")
                    migrate_exam_audit(db_path)
            except Exception as e:
                print(f"Migration warning (exams audit): {e}")

            # ========== Migration: exam_types price field ==========
            try:
                row = cur.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='exam_types'"
                ).fetchone()
                if row:
                    cur.execute("PRAGMA table_info(exam_types)")
                    exam_type_cols = [r[1] for r in cur.fetchall()]
                    if "price" not in exam_type_cols:
                        from migrate_exam_type_price import migrate_exam_type_price

                        print("Running DB migration: exam_types price column ...")
                        migrate_exam_type_price(db_path)
            except Exception as e:
                print(f"Migration warning (exam_types price): {e}")

            # ========== Migration: exams payment fields ==========
            try:
                cur.execute("PRAGMA table_info(exams)")
                exam_cols = [r[1] for r in cur.fetchall()]
                if "paid_at" not in exam_cols or "paid_by_user_id" not in exam_cols or "paid_amount" not in exam_cols:
                    from migrate_exam_payment import migrate as migrate_exam_payment

                    print("Running DB migration: exams payment columns ...")
                    migrate_exam_payment(db_path)
            except Exception as e:
                print(f"Migration warning (exams payment): {e}")

            # ========== Migration: license_renewals vision exam and fee fields ==========
            try:
                row = cur.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='license_renewals'"
                ).fetchone()
                if row:
                    cur.execute("PRAGMA table_info(license_renewals)")
                    renewal_cols = [r[1] for r in cur.fetchall()]
                    if ("vision_exam_date" not in renewal_cols or 
                        "vision_exam_result" not in renewal_cols or 
                        "renewal_fee" not in renewal_cols):
                        from migrate_renewal_vision_exam import migrate as migrate_renewal_vision_exam

                        print("Running DB migration: license_renewals vision exam and fee columns ...")
                        migrate_renewal_vision_exam(db_path)
            except Exception as e:
                print(f"Migration warning (license_renewals vision exam): {e}")

            # ========== Migration: violations paid_by_user_id ==========
            try:
                cur.execute("PRAGMA table_info(violations)")
                vio_cols = [r[1] for r in cur.fetchall()]
                if "paid_by_user_id" not in vio_cols:
                    from migrate_violation_paid_by import migrate as migrate_violation_paid_by

                    print("Running DB migration: violations paid_by_user_id ...")
                    migrate_violation_paid_by(db_path)
            except Exception as e:
                print(f"Migration warning (violations paid_by): {e}")

            # هل العمود موجود؟
            cur.execute("PRAGMA table_info(violations)")
            cols = [r[1] for r in cur.fetchall()]
            needs_col = "violation_type_id" not in cols

            # هل هناك FK حقيقي في تعريف الجدول؟
            row = cur.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='violations'"
            ).fetchone()
            create_sql = (row[0] or "") if row else ""
            needs_fk = "violation_type_id" in create_sql and "REFERENCES violation_types" not in create_sql

            if needs_col or needs_fk:
                from migrate_violation_type_fk import migrate

                print("Running DB migration: violations.violation_type_id FK ...")
                migrate(db_path)

            # ========== Migration: users username field ==========
            try:
                cur.execute("PRAGMA table_info(users)")
                user_cols = [r[1] for r in cur.fetchall()]
                if "username" not in user_cols:
                    from migrate_user_username import migrate as migrate_user_username

                    print("Running DB migration: users username column ...")
                    migrate_user_username(db_path)
            except Exception as e:
                print(f"Migration warning (users username): {e}")

            # ========== Migration: make national_id nullable ==========
            try:
                cur.execute("PRAGMA table_info(users)")
                user_cols_info = cur.fetchall()
                national_id_col = next((c for c in user_cols_info if c[1] == 'national_id'), None)
                if national_id_col and national_id_col[3] == 1:  # NOT NULL
                    from migrate_user_national_id_nullable import migrate as migrate_national_id_nullable

                    print("Running DB migration: make national_id nullable ...")
                    migrate_national_id_nullable(db_path)
            except Exception as e:
                print(f"Migration warning (users national_id nullable): {e}")

            # ========== Migration: users fcm_token field ==========
            try:
                cur.execute("PRAGMA table_info(users)")
                user_cols = [r[1] for r in cur.fetchall()]
                if "fcm_token" not in user_cols:
                    cur.execute("ALTER TABLE users ADD COLUMN fcm_token TEXT")
                    conn.commit()
                    print("Running DB migration: users fcm_token column ...")
            except Exception as e:
                print(f"Migration warning (users fcm_token): {e}")

            # ========== Migration: violations audit fields (cancel/modify) ==========
            try:
                cur.execute("PRAGMA table_info(violations)")
                violation_cols = [r[1] for r in cur.fetchall()]
                needs_audit_fields = any(
                    c not in violation_cols
                    for c in [
                        "cancelled_at",
                        "cancelled_by_user_id",
                        "cancellation_reason",
                        "modified_at",
                        "modified_by_user_id",
                        "modification_reason",
                    ]
                )
                if needs_audit_fields:
                    from migrate_violation_audit_fields import migrate as migrate_violation_audit

                    print("Running DB migration: violations audit fields (cancel/modify) ...")
                    migrate_violation_audit(db_path)
            except Exception as e:
                print(f"Migration warning (violations audit fields): {e}")
        finally:
            conn.close()
    except Exception as e:
        # لا نوقف تشغيل السيرفر بسبب الترحيل، لكن نطبع الخطأ للمراجعة
        print(f"Migration warning: {e}")


run_sqlite_migrations_if_needed()

# إنشاء جداول قاعدة البيانات (إذا لم تكن موجودة) - بعد migrations
Base.metadata.create_all(bind=engine)

# إنشاء حساب admin تلقائياً إذا لم يكن موجوداً
def create_default_admin():
    db = SessionLocal()
    try:
        # البحث أولاً باسم المستخدم
        admin = db.query(User).filter(User.username == 'admin').first()
        # إذا لم يوجد، البحث بالرقم الوطني (للتوافق مع الإصدارات القديمة)
        if not admin:
            admin = db.query(User).filter(User.national_id == 'admin').first()
        
        if not admin:
            hashed_password = get_password_hash('admin123')
            admin = User(
                username='admin',
                national_id=None,  # الإداريون لا يحتاجون رقم وطني
                phone='1234567890',
                password_hash=hashed_password,
                role=UserRole.SUPER_ADMIN,
                is_active=True
            )
            db.add(admin)
            db.commit()
            print("Created default admin account")
            print("  national_id: admin")
            print("  password: admin123")
        else:
            # إذا كان الحساب موجوداً لكن ليس super_admin (مثلاً تم إنشاءه كمواطن عبر التسجيل)،
            # نرفعه تلقائياً لتفادي مشكلة "لا يدخل لوحة الأدمن" عند تسجيل الدخول.
            changed = False
            if admin.role != UserRole.SUPER_ADMIN:
                admin.role = UserRole.SUPER_ADMIN
                changed = True
            if not admin.is_active:
                admin.is_active = True
                changed = True

            if changed:
                db.add(admin)
                db.commit()
                print("Updated existing 'admin' account to SUPER_ADMIN and ensured it is active")
                print("  national_id: admin")
            else:
                print("Default admin account already exists")
    except Exception as e:
        print(f"Error creating default admin account: {e}")
        db.rollback()
    finally:
        db.close()

create_default_admin()

# تهيئة خدمة FCM
print("=" * 60)
print("Initializing FCM Service...")
print("=" * 60)
try:
    from app.services.fcm_service import FCMService
    FCMService.initialize()
    if FCMService.is_initialized():
        print("=" * 60)
        print("✅ FCM Service is ready!")
        print("=" * 60)
    else:
        print("=" * 60)
        print("❌ FCM Service initialization failed. Check logs above for details.")
        print("=" * 60)
except Exception as e:
    print(f"⚠️ CRITICAL: Failed to import or initialize FCM service: {e}")
    import traceback
    print(traceback.format_exc())
    print("=" * 60)

app = FastAPI(
    title="نظام إدارة رخص السيارات والمخالفات",
    description="نظام شامل لإدارة رخص السيارات والمخالفات المرورية",
    version="1.0.0"
)

# إعدادات CORS
# ⚠️ في الإنتاج: حدد origins بدقة بدلاً من ["*"]
CORS_ORIGINS = settings.CORS_ORIGINS if hasattr(settings, 'CORS_ORIGINS') else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# تضمين API routes
app.include_router(api_router, prefix="/api/v1")

# خدمة الملفات الثابتة (Frontend)
# app.mount("/static", StaticFiles(directory="static"), name="static")

# خدمة رفع الملفات
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# @app.get("/")
# async def read_root():
#     return FileResponse("static/index.html")

@app.get("/verify/{barcode}")
async def verify_license_page(barcode: str):
    """صفحة فحص الرخصة بالباركود"""
    return FileResponse("static/verify.html")

@app.get("/test")
async def test_connection():
    """اختبار الاتصال - للتحقق من أن السيرفر يعمل"""
    return {
        "status": "success",
        "message": "السيرفر يعمل بشكل صحيح",
        "server": "running",
        "host": "0.0.0.0",
        "port": 8000
    }

@app.get("/api/v1/test")
async def test_api():
    """اختبار API - للتحقق من أن API يعمل"""
    return {
        "status": "success",
        "message": "API يعمل بشكل صحيح",
        "endpoint": "/api/v1/test"
    }

@app.get("/api/v1/test/fcm")
async def test_fcm():
    """اختبار حالة خدمة FCM"""
    try:
        from app.services.fcm_service import FCMService
        status = FCMService.get_status()
        
        # معلومات إضافية للتشخيص
        import os
        from pathlib import Path
        
        diagnostic_info = {
            "current_working_directory": str(Path.cwd()),
            "fcm_service_account_path_env": os.getenv("FCM_SERVICE_ACCOUNT_PATH"),
            "fcm_service_account_json_env_set": bool(os.getenv("FCM_SERVICE_ACCOUNT_JSON")),
            "checked_paths": []
        }
        
        # فحص المسارات المحتملة
        possible_paths = [
            "app/services/service-account.json",
            "./app/services/service-account.json",
            "/app/services/service-account.json",
            os.path.join(os.path.dirname(__file__), "app", "services", "service-account.json"),
        ]
        
        for path_str in possible_paths:
            path_obj = Path(path_str)
            exists = path_obj.exists()
            abs_path = str(path_obj.absolute()) if exists else None
            diagnostic_info["checked_paths"].append({
                "path": path_str,
                "exists": exists,
                "absolute_path": abs_path
            })
        
        return {
            "status": "success" if status["initialized"] else "error",
            "fcm_status": status,
            "diagnostic_info": diagnostic_info,
            "message": "خدمة FCM مهيأة بشكل صحيح" if status["initialized"] else "خدمة FCM غير مهيأة - يرجى التحقق من إعدادات Service Account",
            "recommendations": [] if status["initialized"] else [
                "تأكد من وجود ملف service-account.json في app/services/",
                "أو أضف متغير بيئة FCM_SERVICE_ACCOUNT_JSON بمحتوى JSON",
                "أو أضف متغير بيئة FCM_SERVICE_ACCOUNT_PATH بمسار الملف"
            ]
        }
    except Exception as e:
        import traceback
        return {
            "status": "error",
            "message": f"خطأ في فحص خدمة FCM: {str(e)}",
            "traceback": traceback.format_exc()
        }

@app.post("/api/v1/test/fcm/reinitialize")
async def reinitialize_fcm():
    """إعادة تهيئة خدمة FCM يدوياً"""
    try:
        from app.services.fcm_service import FCMService
        
        # إعادة التهيئة
        FCMService.initialize()
        
        # الحصول على الحالة بعد إعادة التهيئة
        status = FCMService.get_status()
        
        return {
            "status": "success" if status["initialized"] else "error",
            "message": "تم إعادة تهيئة خدمة FCM بنجاح" if status["initialized"] else "فشلت إعادة تهيئة خدمة FCM",
            "fcm_status": status
        }
    except Exception as e:
        import traceback
        return {
            "status": "error",
            "message": f"خطأ في إعادة تهيئة خدمة FCM: {str(e)}",
            "traceback": traceback.format_exc()
        }

@app.post("/api/v1/test/fcm/send")
async def test_fcm_send(fcm_token: str, title: str = "اختبار إشعار", body: str = "هذا إشعار تجريبي"):
    """اختبار إرسال إشعار فعلي عبر FCM"""
    try:
        from app.services.fcm_service import FCMService
        
        if not FCMService.is_initialized():
            return {
                "status": "error",
                "message": "خدمة FCM غير مهيأة - يرجى التحقق من إعدادات Service Account"
            }
        
        if not fcm_token:
            return {
                "status": "error",
                "message": "رمز FCM مطلوب"
            }
        
        result = FCMService.send_notification(
            fcm_token=fcm_token,
            title=title,
            body=body,
            data={"test": "true", "type": "test_notification"}
        )
        
        return {
            "status": "success" if result else "error",
            "message": "تم إرسال الإشعار بنجاح" if result else "فشل إرسال الإشعار - تحقق من السجلات",
            "fcm_token_received": fcm_token[:30] + "..." if len(fcm_token) > 30 else fcm_token
        }
    except Exception as e:
        import traceback
        return {
            "status": "error",
            "message": f"خطأ في إرسال الإشعار: {str(e)}",
            "traceback": traceback.format_exc()
        }

if __name__ == "__main__":
    import uvicorn
    # للتطوير: استخدام reload=True
    # للإنتاج: استخدام gunicorn مع uvicorn workers
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        # reload=True  # تعطيل في الإنتاج
    )
