"""
Firebase Cloud Messaging Service - HTTP v1 API
يستخدم Service Account لإرسال الإشعارات
"""
import os
import json
from typing import Optional, Dict, Any
import requests
from pathlib import Path

class FCMService:
    """خدمة إرسال الإشعارات عبر Firebase Cloud Messaging HTTP v1 API"""
    
    # مسار ملف Service Account
    SERVICE_ACCOUNT_PATH: Optional[str] = None
    SERVICE_ACCOUNT_DATA: Optional[Dict[str, Any]] = None
    PROJECT_ID: Optional[str] = None
    ACCESS_TOKEN: Optional[str] = None
    IS_INITIALIZED: bool = False
    
    @staticmethod
    def initialize():
        """تهيئة خدمة FCM - يجب استدعاؤها عند بدء التطبيق"""
        try:
            # الطريقة 1: قراءة Service Account من متغير البيئة مباشرة (JSON string)
            # مفيد للاستضافة حيث يمكن حفظ JSON كمتغير بيئة
            fcm_json_env = os.getenv("FCM_SERVICE_ACCOUNT_JSON")
            if fcm_json_env:
                try:
                    FCMService.SERVICE_ACCOUNT_DATA = json.loads(fcm_json_env)
                    FCMService.PROJECT_ID = FCMService.SERVICE_ACCOUNT_DATA.get('project_id')
                    FCMService.IS_INITIALIZED = True
                    print(f"✓ FCM Service initialized from environment variable with project: {FCMService.PROJECT_ID}")
                    return
                except json.JSONDecodeError as e:
                    print(f"⚠️ Error: FCM_SERVICE_ACCOUNT_JSON is not valid JSON: {e}")
            
            # الطريقة 2: قراءة من ملف
            # الحصول على مسار Service Account من متغير البيئة
            default_paths = [
                "app/services/service-account.json",
                "./app/services/service-account.json",
                "/app/services/service-account.json",
                os.path.join(os.path.dirname(__file__), "service-account.json"),
            ]
            
            fcm_path_env = os.getenv("FCM_SERVICE_ACCOUNT_PATH")
            if fcm_path_env:
                default_paths.insert(0, fcm_path_env)
            
            service_account_file = None
            for path_str in default_paths:
                path_obj = Path(path_str)
                # محاولة مسار نسبي ومطلق
                if path_obj.exists():
                    service_account_file = path_obj
                    FCMService.SERVICE_ACCOUNT_PATH = str(path_obj.absolute())
                    break
                # محاولة مسار مطلق
                abs_path = Path(path_str).absolute()
                if abs_path.exists():
                    service_account_file = abs_path
                    FCMService.SERVICE_ACCOUNT_PATH = str(abs_path)
                    break
            
            if not service_account_file:
                print(f"⚠️ Warning: Service Account file not found in any of these paths:")
                for p in default_paths:
                    print(f"   - {p}")
                print("💡 Options:")
                print("   1. Set FCM_SERVICE_ACCOUNT_JSON environment variable with the full JSON content")
                print("   2. Set FCM_SERVICE_ACCOUNT_PATH environment variable with the file path")
                print("   3. Place service-account.json in app/services/ directory")
                FCMService.IS_INITIALIZED = False
                return
            
            try:
                # قراءة Project ID من ملف Service Account
                with open(service_account_file, 'r', encoding='utf-8') as f:
                    FCMService.SERVICE_ACCOUNT_DATA = json.load(f)
                    FCMService.PROJECT_ID = FCMService.SERVICE_ACCOUNT_DATA.get('project_id')
                
                if FCMService.PROJECT_ID:
                    FCMService.IS_INITIALIZED = True
                    print(f"✓ FCM Service initialized from file: {FCMService.SERVICE_ACCOUNT_PATH}")
                    print(f"✓ Project ID: {FCMService.PROJECT_ID}")
                else:
                    print("⚠️ Warning: Could not read project_id from Service Account file")
                    FCMService.IS_INITIALIZED = False
            except Exception as e:
                print(f"⚠️ Error reading Service Account file: {e}")
                FCMService.IS_INITIALIZED = False
        except Exception as e:
            print(f"⚠️ Error initializing FCM service: {e}")
            FCMService.IS_INITIALIZED = False
    
    @staticmethod
    def is_initialized() -> bool:
        """التحقق من أن خدمة FCM مهيأة بشكل صحيح"""
        return FCMService.IS_INITIALIZED and FCMService.PROJECT_ID is not None
    
    @staticmethod
    def get_access_token() -> Optional[str]:
        """
        الحصول على Access Token من Service Account
        """
        if not FCMService.is_initialized():
            print("⚠️ FCM Service is not initialized. Cannot get access token.")
            return None
        
        if not FCMService.SERVICE_ACCOUNT_DATA:
            print("⚠️ Service Account data is not available. Cannot get access token.")
            return None
        
        try:
            from google.auth.transport.requests import Request
            from google.oauth2 import service_account
            
            # استخدام Service Account data مباشرة (من ملف أو متغير بيئة)
            credentials = service_account.Credentials.from_service_account_info(
                FCMService.SERVICE_ACCOUNT_DATA,
                scopes=['https://www.googleapis.com/auth/firebase.messaging']
            )
            
            # تحديث credentials للحصول على access token
            credentials.refresh(Request())
            
            return credentials.token
        except ImportError:
            print("⚠️ Error: google-auth libraries not installed. Run: pip install google-auth google-auth-oauthlib google-auth-httplib2")
            return None
        except Exception as e:
            print(f"⚠️ Error getting access token: {e}")
            import traceback
            print(f"⚠️ Traceback: {traceback.format_exc()}")
            return None
    
    @staticmethod
    def send_notification(
        fcm_token: str,
        title: str,
        body: str,
        data: Optional[dict] = None
    ) -> bool:
        """
        إرسال إشعار إلى جهاز واحد باستخدام HTTP v1 API
        
        Args:
            fcm_token: رمز FCM للمستخدم
            title: عنوان الإشعار
            body: نص الإشعار
            data: بيانات إضافية (اختياري)
        
        Returns:
            True إذا تم الإرسال بنجاح، False في حالة الفشل
        """
        if not fcm_token:
            print("⚠️ FCM token is empty. Cannot send notification.")
            return False
        
        if not FCMService.is_initialized():
            print("⚠️ FCM Service is not initialized. Cannot send notification.")
            print("💡 Please check FCM configuration and ensure Service Account is properly set up.")
            return False
        
        if not FCMService.PROJECT_ID:
            print("⚠️ FCM Project ID not configured. Cannot send notification.")
            return False
        
        # الحصول على Access Token
        access_token = FCMService.get_access_token()
        if not access_token:
            print("⚠️ Failed to get access token. Cannot send notification.")
            return False
        
        # بناء رابط API v1
        url = f"https://fcm.googleapis.com/v1/projects/{FCMService.PROJECT_ID}/messages:send"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # بناء payload حسب HTTP v1 API format
        # ⚠️ مهم: استخدام "token" لإرسال إشعار لمستخدم واحد فقط
        # لا تستخدم "topic" لأن ذلك سيرسل الإشعار لجميع المشتركين في الـ topic
        # ⚠️ تأكد من أن كل مستخدم لديه token فريد - إذا كان جميع المستخدمين لديهم نفس token، سيظهر الإشعار لجميعهم
        
        # التحقق من أن token ليس فارغاً أو null
        if not fcm_token or len(fcm_token.strip()) == 0:
            print("⚠️ FCM token is empty or null. Cannot send notification.")
            return False
        
        message = {
            "message": {
                "token": fcm_token.strip(),  # إرسال لجهاز واحد فقط باستخدام token (NOT topic!)
                "notification": {
                    "title": title,
                    "body": body
                }
            }
        }
        
        # إضافة data إذا كان موجوداً
        if data:
            # تحويل data إلى strings (مطلوب في FCM)
            data_strings = {k: str(v) for k, v in data.items()}
            message["message"]["data"] = data_strings
        
        # سجل للتأكد من أننا نرسل للمستخدم الصحيح فقط
        print(f"📤 FCM Payload: Sending to token {fcm_token[:30]}... (first 30 chars)")
        print(f"📤 FCM Message: {title} - {body}")
        print(f"📤 Using 'token' field (NOT 'topic') - this should send to ONE device only")
        
        try:
            response = requests.post(url, headers=headers, json=message, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if "name" in result:
                print(f"✓ Notification sent successfully via HTTP v1 API")
                return True
            else:
                print(f"✗ Failed to send notification: {result}")
                return False
        except requests.exceptions.HTTPError as e:
            error_detail = ""
            try:
                error_detail = e.response.json()
            except:
                error_detail = str(e)
            print(f"✗ HTTP error sending notification: {error_detail}")
            print(f"✗ Response status: {e.response.status_code if hasattr(e, 'response') else 'N/A'}")
            print(f"✗ Response headers: {e.response.headers if hasattr(e, 'response') and hasattr(e.response, 'headers') else 'N/A'}")
            return False
        except requests.exceptions.RequestException as e:
            print(f"✗ Network error sending notification: {str(e)}")
            print(f"✗ This might indicate a network connectivity issue or firewall blocking the request")
            return False
        except Exception as e:
            print(f"✗ Error sending notification: {str(e)}")
            import traceback
            print(f"✗ Traceback: {traceback.format_exc()}")
            return False
    
    @staticmethod
    def send_notification_to_user(
        user_id: int,
        title: str,
        body: str,
        data: Optional[dict] = None,
        db = None
    ) -> bool:
        """
        إرسال إشعار إلى مستخدم محدد
        
        Args:
            user_id: معرف المستخدم
            title: عنوان الإشعار
            body: نص الإشعار
            data: بيانات إضافية (اختياري)
            db: جلسة قاعدة البيانات
        
        Returns:
            True إذا تم الإرسال بنجاح، False في حالة الفشل
        """
        if not db:
            print("⚠️ Database session not provided")
            return False
        
        from app.features.user.model import User
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            print(f"⚠️ User {user_id} not found")
            return False
        
        if not user.fcm_token:
            print(f"⚠️ User {user_id} (national_id: {user.national_id}) has no FCM token. Notification cannot be sent. User must login to the app first to register FCM token.")
            return False
        
        print(f"📤 Sending notification to User ID: {user_id}, National ID: {user.national_id}")
        print(f"📤 FCM Token: {user.fcm_token[:50]}... (first 50 chars)")
        print(f"📤 Title: {title}")
        print(f"📤 Body: {body}")
        result = FCMService.send_notification(
            fcm_token=user.fcm_token,
            title=title,
            body=body,
            data=data
        )
        if result:
            print(f"✓ Notification sent successfully to User ID: {user_id}")
        else:
            print(f"✗ Failed to send notification to User ID: {user_id}")
        return result
    
    @staticmethod
    def get_status() -> dict:
        """
        الحصول على حالة خدمة FCM
        """
        status = {
            "initialized": FCMService.IS_INITIALIZED,
            "project_id": FCMService.PROJECT_ID if FCMService.IS_INITIALIZED else None,
            "service_account_path": FCMService.SERVICE_ACCOUNT_PATH if FCMService.SERVICE_ACCOUNT_PATH else "Using environment variable",
            "has_service_account_data": FCMService.SERVICE_ACCOUNT_DATA is not None
        }
        
        # محاولة الحصول على access token للتحقق من أن كل شيء يعمل
        access_token_test = None
        token_error = None
        if status["initialized"]:
            try:
                access_token_test = FCMService.get_access_token()
                if access_token_test:
                    status["access_token_available"] = True
                    status["access_token_length"] = len(access_token_test)
                else:
                    status["access_token_available"] = False
                    status["access_token_error"] = "Failed to get access token"
            except Exception as e:
                status["access_token_available"] = False
                status["access_token_error"] = str(e)
                import traceback
                status["access_token_traceback"] = traceback.format_exc()
        
        return status
