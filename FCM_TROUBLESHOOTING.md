# دليل استكشاف أخطاء FCM

## المشكلة: الإشعارات لا تعمل بعد رفع API على الاستضافة

### الخطوة 1: فحص حالة FCM

افتح المتصفح أو استخدم curl:
```bash
curl https://your-domain.com/api/v1/test/fcm
```

**ما يجب أن تبحث عنه:**

1. **`initialized: false`**
   - يعني أن FCM لم يتم تهيئته
   - تحقق من `diagnostic_info.checked_paths` لمعرفة المسارات التي تم فحصها
   - تأكد من وجود ملف `service-account.json` في أحد المسارات

2. **`access_token_available: false`**
   - يعني أن FCM مهيأ لكن لا يمكن الحصول على access token
   - تحقق من `access_token_error` لمعرفة الخطأ
   - قد تكون المشكلة في:
     - الملف JSON تالف أو غير صحيح
     - المفتاح الخاص (private_key) غير صحيح
     - مشكلة في الاتصال بـ Google APIs

### الخطوة 2: فحص المسارات

من النتيجة، افحص `diagnostic_info.checked_paths`:
- إذا كان `exists: false` لجميع المسارات، الملف غير موجود
- إذا كان `exists: true` لأحد المسارات، استخدم `absolute_path` للتحقق

### الخطوة 3: الحلول المقترحة

#### الحل 1: استخدام متغير البيئة (الأسهل)

1. افتح ملف `service-account.json` من الاستضافة
2. انسخ محتوى JSON بالكامل
3. أضف متغير بيئة:
   ```bash
   FCM_SERVICE_ACCOUNT_JSON='{محتوى JSON هنا}'
   ```
4. أعد تشغيل السيرفر

#### الحل 2: رفع الملف في المسار الصحيح

من `diagnostic_info.current_working_directory`، حدد المسار الصحيح:
- إذا كان `/home/user/app/`، ضع الملف في `/home/user/app/app/services/service-account.json`
- أو استخدم متغير البيئة:
  ```bash
  FCM_SERVICE_ACCOUNT_PATH=/path/to/your/service-account.json
  ```

#### الحل 3: التحقق من الصلاحيات

على Linux/Unix، تأكد من صلاحيات الملف:
```bash
chmod 600 service-account.json
chown your-user:your-group service-account.json
```

### الخطوة 4: اختبار إرسال إشعار

بعد التأكد من أن `initialized: true` و `access_token_available: true`:

```bash
curl -X POST "https://your-domain.com/api/v1/test/fcm/send?fcm_token=YOUR_FCM_TOKEN&title=Test&body=Test message"
```

**إذا فشل الإرسال:**
- تحقق من أن `fcm_token` صحيح
- تحقق من سجلات السيرفر (logs) لمعرفة الخطأ التفصيلي
- قد تكون المشكلة في:
  - اتصال الإنترنت من الاستضافة
  - جدار ناري يمنع الاتصال بـ `fcm.googleapis.com`
  - Token غير صحيح أو منتهي الصلاحية

### الخطوة 5: فحص السجلات

على الاستضافة، افحص سجلات التطبيق (application logs):
- ابحث عن رسائل تبدأ بـ `⚠️` أو `✗` للبحث عن الأخطاء
- ابحث عن رسائل تبدأ بـ `✓` للتأكد من أن الإعداد صحيح

### المشاكل الشائعة والحلول

#### 1. "Service Account file not found"
**الحل:** 
- استخدم متغير البيئة `FCM_SERVICE_ACCOUNT_JSON`
- أو تأكد من رفع الملف في المسار الصحيح

#### 2. "Could not read project_id"
**الحل:**
- تأكد من أن ملف JSON صحيح
- افتح الملف وتحقق من وجود حقل `project_id`

#### 3. "Failed to get access token"
**الحل:**
- تحقق من أن `private_key` في JSON صحيح
- تأكد من أن Service Account لديه الصلاحيات المطلوبة في Firebase Console
- تحقق من اتصال الإنترنت من الاستضافة

#### 4. "HTTP error sending notification"
**الحل:**
- تحقق من رسالة الخطأ التفصيلية
- قد تكون المشكلة في:
  - Token FCM غير صحيح
  - المستخدم لم يسجل token بعد
  - مشكلة في Firebase Project

#### 5. "Network error"
**الحل:**
- تحقق من اتصال الإنترنت من الاستضافة
- تأكد من أن جدار النار يسمح بالاتصال بـ `fcm.googleapis.com`
- جرب من سطر الأوامر على الاستضافة:
  ```bash
  curl https://fcm.googleapis.com
  ```

## نصائح إضافية

1. **استخدم متغير البيئة دائماً في الإنتاج** - أكثر أماناً وأسهل في الإدارة
2. **لا ترفع ملف service-account.json إلى Git** - أضفه إلى `.gitignore`
3. **احفظ نسخة احتياطية من Service Account** - في مكان آمن
4. **راقب السجلات بانتظام** - للكشف المبكر عن المشاكل

