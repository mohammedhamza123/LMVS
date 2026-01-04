from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class LicenseTypeCategoryBase(BaseModel):
    code: str = Field(..., description="رمز الفئة مثل A أو B")
    label: Optional[str] = None
    allowed_vehicles: Optional[str] = None


class LicenseTypeCategoryCreate(LicenseTypeCategoryBase):
    pass


class LicenseTypeCategoryUpdate(BaseModel):
    label: Optional[str] = None
    allowed_vehicles: Optional[str] = None


class LicenseTypeCategoryResponse(LicenseTypeCategoryBase):
    id: int
    license_type_id: int

    class Config:
        from_attributes = True


class LicenseTypeBase(BaseModel):
    name: str
    degree_order: int = 1
    validity_years: int = 10
    top_color: str = "#facc15"
    has_categories: bool = False
    allowed_vehicles: Optional[str] = None
    is_active: bool = True


class LicenseTypeCreate(LicenseTypeBase):
    categories: Optional[List[LicenseTypeCategoryCreate]] = None


class LicenseTypeUpdate(BaseModel):
    name: Optional[str] = None
    degree_order: Optional[int] = None
    validity_years: Optional[int] = None
    top_color: Optional[str] = None
    has_categories: Optional[bool] = None
    allowed_vehicles: Optional[str] = None
    is_active: Optional[bool] = None


class LicenseTypeResponse(LicenseTypeBase):
    id: int
    created_at: datetime
    categories: List[LicenseTypeCategoryResponse] = []

    class Config:
        from_attributes = True
































