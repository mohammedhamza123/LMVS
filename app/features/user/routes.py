from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.features.user.model import User
from app.models.enums import UserRole
from app.features.user.schema import UserResponse, UserUpdate, ChangePassword
from app.features.user.service import UserService
from pydantic import BaseModel

class FCMTokenUpdate(BaseModel):
    fcm_token: str

router = APIRouter()

@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """الحصول على معلومات المستخدم الحالي"""
    return current_user

@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """الحصول على معلومات مستخدم"""
    if current_user.role == UserRole.CITIZEN and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="ليس لديك صلاحية للوصول")
    
    user = UserService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")
    return user

@router.put("/me", response_model=UserResponse)
def update_current_user(
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """تحديث بيانات المستخدم الحالي"""
    updated_user = UserService.update_user(db, current_user.id, user_data)
    if not updated_user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")
    return updated_user

@router.post("/change-password")
def change_password(
    password_data: ChangePassword,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """تغيير كلمة المرور"""
    try:
        print(f"Change password request for user ID: {current_user.id}")
        print(f"Current password length: {len(password_data.current_password) if password_data.current_password else 0}")
        print(f"New password length: {len(password_data.new_password) if password_data.new_password else 0}")
        
        # التحقق من أن كلمة المرور الحالية موجودة
        if not password_data.current_password or len(password_data.current_password.strip()) == 0:
            print("Error: Current password is empty")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="كلمة المرور الحالية مطلوبة"
            )
        
        # التحقق من أن كلمة المرور الجديدة موجودة
        if not password_data.new_password or len(password_data.new_password.strip()) == 0:
            print("Error: New password is empty")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="كلمة المرور الجديدة مطلوبة"
            )
        
        # التحقق من طول كلمة المرور الجديدة
        if len(password_data.new_password) < 6:
            print(f"Error: New password too short: {len(password_data.new_password)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="كلمة المرور الجديدة يجب أن تكون على الأقل 6 أحرف"
            )
        
        # التحقق من أن كلمة المرور الجديدة مختلفة عن الحالية
        if password_data.current_password == password_data.new_password:
            print("Error: New password same as current")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="كلمة المرور الجديدة يجب أن تكون مختلفة عن الحالية"
            )
        
        success = UserService.change_password(
            db, 
            current_user.id, 
            password_data.current_password, 
            password_data.new_password
        )
        if not success:
            print("Error: Current password verification failed")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="كلمة المرور الحالية غير صحيحة"
            )
        print("Password changed successfully")
        return {"message": "تم تغيير كلمة المرور بنجاح"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in change_password: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"حدث خطأ أثناء تغيير كلمة المرور: {str(e)}"
        )

@router.post("/update-fcm-token")
def update_fcm_token(
    fcm_token_data: FCMTokenUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """تحديث رمز FCM للمستخدم"""
    if not fcm_token_data.fcm_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="رمز FCM مطلوب"
        )
    
    old_token = current_user.fcm_token
    current_user.fcm_token = fcm_token_data.fcm_token
    db.commit()
    db.refresh(current_user)
    
    print(f"✓ FCM Token updated for User ID: {current_user.id}, National ID: {current_user.national_id}")
    print(f"  Old Token: {old_token[:20] if old_token else 'None'}...")
    print(f"  New Token: {fcm_token_data.fcm_token[:20]}...")
    
    return {"message": "تم تحديث رمز FCM بنجاح", "fcm_token": fcm_token_data.fcm_token}

