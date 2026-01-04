from enum import Enum

class UserRole(str, Enum):
    CITIZEN = "citizen"
    LICENSE_OFFICER = "license_officer"
    VIOLATION_OFFICER = "violation_officer"
    TRAFFIC_POLICE = "traffic_police"  # شرطي المرور
    SUPER_ADMIN = "super_admin"

class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"

class BloodType(str, Enum):
    A_POSITIVE = "A+"
    A_NEGATIVE = "A-"
    B_POSITIVE = "B+"
    B_NEGATIVE = "B-"
    AB_POSITIVE = "AB+"
    AB_NEGATIVE = "AB-"
    O_POSITIVE = "O+"
    O_NEGATIVE = "O-"

class LicenseStatus(str, Enum):
    PENDING = "pending"
    EXAM_PASSED = "exam_passed"
    EXAM_FAILED = "exam_failed"
    APPROVED = "approved"
    REJECTED = "rejected"
    ISSUED = "issued"
    EXPIRED = "expired"
    REVOKED = "revoked"

class LicenseRenewalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class ViolationStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    APPEALED = "appealed"
    CANCELLED = "cancelled"

class LicenseType(str, Enum):
    # ملاحظة: يتم تخزين أسماء الـEnum في قاعدة البيانات (مثل PRIVATE) بينما الـAPI يعرض value (مثل "private").
    # تم إعادة تعريف مسميات الأنواع في الواجهة حسب طلب المستخدم (درجة أولى/الثاني/الثالث/الرابع/ذوي العاهات).
    PRIVATE = "private"        # النوع الأول (درجة أولى)
    PUBLIC = "public"          # النوع الثاني
    MOTORCYCLE = "motorcycle"  # نوع قديم (للتوافق)
    TRUCK = "truck"            # النوع الثالث
    BUS = "bus"                # النوع الرابع
    DISABLED = "disabled"      # ذوي العاهات





