"""
Firebase Cloud Messaging Service - HTTP v1 API
يستخدم Service Account لإرسال الإشعارات
"""
import os
import json
from typing import Optional
import requests
from pathlib import Path

class FCMService:
    """خدمة إرسال الإشعارات عبر Firebase Cloud Messaging HTTP v1 API"""
    
    # مسار ملف Service Account
    SERVICE_ACCOUNT_PATH: Optional[str] = None
    PROJECT_ID: Optional[str] = None
    ACCESS_TOKEN: Optional[str] = None
    
    @staticmethod
    def initialize():
        """تهيئة خدمة FCM - يجب استدعاؤها عند بدء التطبيق"""
        # الحصول على مسار Service Account من متغير البيئة
        FCMService.SERVICE_ACCOUNT_PATH = os.getenv("FCM_SERVICE_ACCOUNT_PATH", "app/services/service-account.json")
        
        # التحقق من وجود ملف Service Account
        service_account_file = Path(FCMService.SERVICE_ACCOUNT_PATH)
        if not service_account_file.exists():
            print(f"⚠️ Warning: Service Account file not found at {FCMService.SERVICE_ACCOUNT_PATH}")
            print("💡 Please create Service Account and save it to the specified path.")
            return
        
        try:
            # قراءة Project ID من ملف Service Account
            with open(service_account_file, 'r') as f:
                service_account_data = json.load(f)
                FCMService.PROJECT_ID = service_account_data.get('project_id')
            
            if FCMService.PROJECT_ID:
                print(f"✓ FCM Service initialized with project: {FCMService.PROJECT_ID}")
            else:
                print("⚠️ Warning: Could not read project_id from Service Account file")
        except Exception as e:
            print(f"⚠️ Error reading Service Account file: {e}")
    
    @staticmethod
    def get_access_token() -> Optional[str]:
        """
        الحصول على Access Token من Service Account
        """
        if not FCMService.SERVICE_ACCOUNT_PATH:
            return None
        
        service_account_file = Path(FCMService.SERVICE_ACCOUNT_PATH)
        if not service_account_file.exists():
            return None
        
        try:
            from google.auth.transport.requests import Request
            from google.oauth2 import service_account
            
            # قراءة Service Account credentials
            credentials = service_account.Credentials.from_service_account_file(
                str(service_account_file),
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
            return False
        except Exception as e:
            print(f"✗ Error sending notification: {str(e)}")
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
