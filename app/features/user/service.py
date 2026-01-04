from sqlalchemy.orm import Session
from app.features.user.model import User
from app.features.user.schema import UserCreate, UserUpdate
from app.core.security import get_password_hash, verify_password
from app.models.enums import UserRole
from typing import Optional

class UserService:
    @staticmethod
    def create_user(db: Session, user_data: UserCreate, role: UserRole = UserRole.CITIZEN) -> User:
        """إنشاء مستخدم جديد"""
        # التحقق من وجود مستخدم بنفس الرقم الوطني (للمواطنين)
        if user_data.national_id:
            existing_user = db.query(User).filter(
                User.national_id == user_data.national_id
            ).first()
            if existing_user:
                raise ValueError("المستخدم موجود بالفعل بهذا الرقم الوطني")
        
        # التحقق من وجود مستخدم بنفس اسم المستخدم (للإداريين)
        if user_data.username:
            existing_user = db.query(User).filter(
                User.username == user_data.username
            ).first()
            if existing_user:
                raise ValueError("اسم المستخدم موجود بالفعل")
        
        # التحقق من وجود national_id أو username
        if not user_data.national_id and not user_data.username:
            raise ValueError("يجب إدخال الرقم الوطني أو اسم المستخدم")
        
        # للإداريين: يجب وجود username
        admin_roles = [UserRole.SUPER_ADMIN, UserRole.LICENSE_OFFICER, UserRole.VIOLATION_OFFICER, UserRole.TRAFFIC_POLICE]
        if role in admin_roles and not user_data.username:
            raise ValueError("يجب إدخال اسم المستخدم للإداريين")
        
        # للمواطنين: يجب وجود national_id
        if role == UserRole.CITIZEN and not user_data.national_id:
            raise ValueError("يجب إدخال الرقم الوطني للمواطنين")
        
        hashed_password = get_password_hash(user_data.password)
        db_user = User(
            national_id=user_data.national_id,
            username=user_data.username,
            phone=user_data.phone,
            password_hash=hashed_password,
            role=role
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    
    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        """الحصول على مستخدم بالمعرف"""
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def get_user_by_national_id(db: Session, national_id: str) -> Optional[User]:
        """الحصول على مستخدم بالرقم الوطني"""
        return db.query(User).filter(User.national_id == national_id).first()
    
    @staticmethod
    def get_user_by_username(db: Session, username: str) -> Optional[User]:
        """الحصول على مستخدم باسم المستخدم"""
        return db.query(User).filter(User.username == username).first()
    
    @staticmethod
    def update_user(db: Session, user_id: int, user_data: UserUpdate) -> Optional[User]:
        """تحديث بيانات المستخدم"""
        db_user = db.query(User).filter(User.id == user_id).first()
        if not db_user:
            return None
        
        update_data = user_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_user, field, value)
        
        db.commit()
        db.refresh(db_user)
        return db_user
    
    @staticmethod
    def authenticate_user(db: Session, username_or_national_id: str, password: str) -> Optional[User]:
        """المصادقة على المستخدم - يدعم اسم المستخدم للإداريين والرقم الوطني للمواطنين"""
        # البحث أولاً باسم المستخدم (للإداريين)
        user = db.query(User).filter(User.username == username_or_national_id).first()
        
        # إذا لم يوجد، البحث بالرقم الوطني (للمواطنين)
        if not user:
            user = db.query(User).filter(User.national_id == username_or_national_id).first()
        
        if not user:
            return None
        
        if not verify_password(password, user.password_hash):
            return None
        
        return user
    
    @staticmethod
    def change_password(db: Session, user_id: int, current_password: str, new_password: str) -> bool:
        """تغيير كلمة المرور"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        if not verify_password(current_password, user.password_hash):
            return False
        
        user.password_hash = get_password_hash(new_password)
        db.commit()
        return True

















