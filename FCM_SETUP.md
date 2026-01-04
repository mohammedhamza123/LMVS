# دليل إعداد Firebase Cloud Messaging (FCM) على الاستضافة

## المشكلة
عند رفع API على الاستضافة، قد لا تعمل الإشعارات بسبب مشاكل في إعدادات Service Account.

## الحلول المتاحة

### الطريقة 1: استخدام متغير البيئة (مُوصى به للاستضافة)

هذه الطريقة الأفضل للاستضافة حيث لا تحتاج لرفع ملف JSON:

1. افتح ملف `service-account.json` من `app/services/service-account.json`
2. انسخ محتوى الملف بالكامل (JSON)
3. على الاستضافة، أضف متغير بيئة باسم `FCM_SERVICE_ACCOUNT_JSON` وقم بلصق محتوى JSON بالكامل

**مثال على الاستضافة:**
```bash
# في cPanel أو لوحة التحكم
FCM_SERVICE_ACCOUNT_JSON='{"type":"service_account","project_id":"...","private_key":"..."}'
```

**ملاحظة:** تأكد من إضافة علامات الاقتباس المناسبة وتجنب كسر السطور.

### الطريقة 2: رفع ملف service-account.json

1. ارفع ملف `app/services/service-account.json` إلى الاستضافة في نفس المسار
2. أو حدد مسار مخصص عبر متغير البيئة:
   ```bash
   FCM_SERVICE_ACCOUNT_PATH=/path/to/your/service-account.json
   ```

### الطريقة 3: استخدام المسار الافتراضي

إذا رفعت الملف في `app/services/service-account.json`، سيعمل تلقائياً.

## التحقق من الإعداد

بعد رفع API، قم بزيارة:
```
GET /api/v1/test/fcm
```

ستحصل على معلومات تفصيلية عن حالة خدمة FCM:
- `initialized`: هل تم تهيئة الخدمة بنجاح
- `project_id`: معرف المشروع
- `access_token_available`: هل يمكن الحصول على access token
- `diagnostic_info`: معلومات تشخيصية تشمل:
  - المسار الحالي للعمل
  - المسارات التي تم فحصها
  - ما إذا كان الملف موجوداً في كل مسار

## اختبار إرسال إشعار فعلي

لاختبار إرسال إشعار فعلي:
```
POST /api/v1/test/fcm/send
Content-Type: application/json

{
  "fcm_token": "رمز_FCM_الخاص_بك",
  "title": "عنوان الإشعار",
  "body": "نص الإشعار"
}
```

أو باستخدام query parameters:
```
POST /api/v1/test/fcm/send?fcm_token=YOUR_TOKEN&title=Test&body=Test message
```

## استكشاف الأخطاء

### المشكلة: "Service Account file not found"
**الحل:** 
- تأكد من رفع ملف `service-account.json` أو إضافة متغير البيئة `FCM_SERVICE_ACCOUNT_JSON`
- تحقق من الصلاحيات على الملف

### المشكلة: "Could not read project_id"
**الحل:**

- تأكد من أن ملف JSON صحيح وغير تالف
- تحقق من أن الملف يحتوي على حقل `project_id`

### المشكلة: "google-auth libraries not installed"
**الحل:**
- تأكد من تثبيت المكتبات المطلوبة:
  ```bash
  pip install google-auth google-auth-oauthlib google-auth-httplib2
  ```

### المشكلة: "Failed to get access token"
**الحل:**
- تحقق من أن Service Account لديه الصلاحيات المطلوبة في Firebase Console
- تأكد من أن المفتاح الخاص (private_key) صحيح
- تحقق من اتصال الإنترنت من الاستضافة إلى Google APIs

## الأمان

⚠️ **مهم جداً:**
- لا ترفع ملف `service-account.json` إلى Git
- استخدم متغيرات البيئة في الإنتاج
- تأكد من أن الملف محمي بصلاحيات مناسبة (600 أو 640)

## اختبار الإشعارات

بعد التأكد من أن FCM يعمل عبر `/api/v1/test/fcm`، جرب إرسال إشعار فعلي من التطبيق.

