from pydantic_settings import BaseSettings
from typing import Optional, List

class Settings(BaseSettings):
    # قاعدة البيانات
    # SQLite للتطوير (افتراضي)
    DATABASE_URL: str = "sqlite:///./license_system.db"
    # أو PostgreSQL للإنتاج
    # DATABASE_URL: str = "postgresql://user:password@localhost/dbname"
    
    # JWT
    SECRET_KEY: str = "your-secret-key-change-this-in-production"  # ⚠️ يجب تغييره في الإنتاج!
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # إعدادات التطبيق
    PROJECT_NAME: str = "نظام إدارة رخص السيارات"
    
    # CORS Origins (للإنتاج: حدد النطاقات المسموحة)
    CORS_ORIGINS: List[str] = ["*"]  # ⚠️ في الإنتاج: ["https://yourdomain.com"]
    
    class Config:
        env_file = ".env"

settings = Settings()

