from sqlalchemy.orm import Session
from sqlalchemy import func
from app.features.user.model import User
from app.features.license.model import License
from app.features.exam.model import Exam
from app.features.violation.model import Violation
from app.models.enums import LicenseStatus, ViolationStatus, UserRole
from typing import Dict, Tuple
import os

class AdminService:
    @staticmethod
    def get_system_statistics(db: Session) -> Dict:
        """الحصول على إحصائيات النظام الشاملة"""
        
        # إحصائيات المستخدمين
        total_users = db.query(func.count(User.id)).scalar()
        active_users = db.query(func.count(User.id)).filter(User.is_active == True).scalar()
        citizens = db.query(func.count(User.id)).filter(User.role == UserRole.CITIZEN).scalar()
        license_officers = db.query(func.count(User.id)).filter(User.role == UserRole.LICENSE_OFFICER).scalar()
        violation_officers = db.query(func.count(User.id)).filter(User.role == UserRole.VIOLATION_OFFICER).scalar()
        
        # إحصائيات الرخص
        total_licenses = db.query(func.count(License.id)).scalar()
        pending_licenses = db.query(func.count(License.id)).filter(License.status == LicenseStatus.PENDING).scalar()
        approved_licenses = db.query(func.count(License.id)).filter(License.status == LicenseStatus.APPROVED).scalar()
        issued_licenses = db.query(func.count(License.id)).filter(License.status == LicenseStatus.ISSUED).scalar()
        rejected_licenses = db.query(func.count(License.id)).filter(License.status == LicenseStatus.REJECTED).scalar()
        exam_passed = db.query(func.count(License.id)).filter(License.status == LicenseStatus.EXAM_PASSED).scalar()
        exam_failed = db.query(func.count(License.id)).filter(License.status == LicenseStatus.EXAM_FAILED).scalar()
        
        # إحصائيات الامتحانات
        total_exams = db.query(func.count(Exam.id)).scalar()
        pending_exams = db.query(func.count(Exam.id)).filter(Exam.result == None).scalar()
        passed_exams = db.query(func.count(Exam.id)).filter(Exam.result == "passed").scalar()
        failed_exams = db.query(func.count(Exam.id)).filter(Exam.result == "failed").scalar()
        
        # إحصائيات المخالفات
        total_violations = db.query(func.count(Violation.id)).scalar()
        pending_violations = db.query(func.count(Violation.id)).filter(Violation.status == ViolationStatus.PENDING).scalar()
        paid_violations = db.query(func.count(Violation.id)).filter(Violation.status == ViolationStatus.PAID).scalar()
        appealed_violations = db.query(func.count(Violation.id)).filter(Violation.status == ViolationStatus.APPEALED).scalar()
        
        # حساب إجمالي المبالغ
        total_fines = db.query(func.sum(Violation.fine_amount)).scalar() or 0
        paid_fines = db.query(func.sum(Violation.fine_amount)).filter(Violation.status == ViolationStatus.PAID).scalar() or 0
        pending_fines = db.query(func.sum(Violation.fine_amount)).filter(Violation.status == ViolationStatus.PENDING).scalar() or 0
        
        # إحصائيات المسؤولين الذين أصدروا الرخص
        licenses_by_officer = (
            db.query(
                License.issued_by_user_id,
                User.username,
                User.national_id,
                func.count(License.id).label('count')
            )
            .join(User, License.issued_by_user_id == User.id, isouter=True)
            .filter(License.status == LicenseStatus.ISSUED)
            .filter(License.issued_by_user_id.isnot(None))
            .group_by(License.issued_by_user_id, User.username, User.national_id)
            .order_by(func.count(License.id).desc())
            .all()
        )
        
        officers_stats = []
        for row in licenses_by_officer:
            officers_stats.append({
                "user_id": row.issued_by_user_id,
                "username": row.username,
                "national_id": row.national_id,
                "issued_count": row.count
            })
        
        return {
            "users": {
                "total": total_users,
                "active": active_users,
                "inactive": total_users - active_users,
                "by_role": {
                    "citizens": citizens,
                    "license_officers": license_officers,
                    "violation_officers": violation_officers
                }
            },
            "licenses": {
                "total": total_licenses,
                "pending": pending_licenses,
                "approved": approved_licenses,
                "issued": issued_licenses,
                "rejected": rejected_licenses,
                "exam_passed": exam_passed,
                "exam_failed": exam_failed,
                "summary": {
                    "pending": pending_licenses,
                    "approved": approved_licenses + issued_licenses,
                    "rejected": rejected_licenses
                },
                "by_officer": officers_stats
            },
            "exams": {
                "total": total_exams,
                "pending": pending_exams,
                "passed": passed_exams,
                "failed": failed_exams
            },
            "violations": {
                "total": total_violations,
                "pending": pending_violations,
                "paid": paid_violations,
                "appealed": appealed_violations,
                "fines": {
                    "total": float(total_fines),
                    "paid": float(paid_fines),
                    "pending": float(pending_fines)
                }
            }
        }



















