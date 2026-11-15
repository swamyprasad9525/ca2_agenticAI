from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, EmailStr


class VendorBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    registration_number: Optional[str] = Field(default=None, max_length=100)
    contact_email: Optional[str] = Field(default=None)
    country: Optional[str] = Field(default=None, max_length=100)


class VendorCreate(VendorBase):
    pass


class VendorRead(VendorBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

