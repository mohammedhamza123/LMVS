from fastapi import APIRouter
from app.features.auth.routes import router as auth_router
from app.features.user.routes import router as users_router
from app.features.license.routes import router as licenses_router
from app.features.license_renewal.routes import router as license_renewals_router
from app.features.license_replacement.routes import router as license_replacements_router
from app.features.exam.routes import router as exams_router
from app.features.violation.routes import router as violations_router
from app.features.admin.routes import router as admin_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users_router, prefix="/users", tags=["Users"])
api_router.include_router(licenses_router, prefix="/licenses", tags=["Licenses"])
api_router.include_router(license_renewals_router, prefix="/renewals", tags=["License Renewals"])
api_router.include_router(license_replacements_router, prefix="/replacements", tags=["License Replacements"])
api_router.include_router(exams_router, prefix="/exams", tags=["Exams"])
api_router.include_router(violations_router, prefix="/violations", tags=["Violations"])
api_router.include_router(admin_router, prefix="/admin", tags=["Admin"])
