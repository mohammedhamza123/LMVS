from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.models.enums import UserRole

class UserBase(BaseModel):
    national_id: Optional[str] = None
    username: Optional[str] = None
    phone: str

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    phone: Optional[str] = None
    fcm_token: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    national_id: Optional[str] = None
    username: Optional[str] = None
    phone: str
    role: UserRole
    is_active: bool
    suspended_until: Optional[datetime] = None
    suspension_reason: Optional[str] = None
    fcm_token: Optional[str] = None
    
    class Config:
        from_attributes = True


class UserSuspendRequest(BaseModel):
    """إيقاف مؤقت لحساب المستخدم"""
    minutes: int = 60
    reason: Optional[str] = None

class UserLogin(BaseModel):
    national_id: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class ChangePassword(BaseModel):
    current_password: str = Field(..., min_length=1, description="كلمة المرور الحالية")
    new_password: str = Field(..., min_length=6, description="كلمة المرور الجديدة")
    
    class Config:
        json_schema_extra = {
            "example": {
                "current_password": "password123",
                "new_password": "newpassword123"
            }
        }

