from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from decimal import Decimal


class ViolationTypeBase(BaseModel):
    name: str
    description: Optional[str] = None
    fine_amount: Decimal = Decimal("0.00")
    is_active: bool = True


class ViolationTypeCreate(ViolationTypeBase):
    pass


class ViolationTypeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    fine_amount: Optional[Decimal] = None
    is_active: Optional[bool] = None


class ViolationTypeResponse(ViolationTypeBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True



































