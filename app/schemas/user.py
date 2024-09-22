from pydantic import BaseModel, EmailStr, Field, validator
from datetime import date
from typing import Optional
import re


class UserBase(BaseModel):
    email: Optional[EmailStr] = None
    phone: str = Field(..., regex=r'^\+?1?\d{9,15}$')
    full_name: str = Field(..., min_length=2, max_length=100)


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    birth_date: date
    id_number: str
    id_issue_date: date

    @validator('birth_date')
    def check_age(cls, v):
        today = date.today()
        age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
        if age < 18:
            raise ValueError('Must be at least 18 years old')
        return v

    @validator('id_number')
    def validate_id_number(cls, v):
        if not re.match(r'^\d{8,10}$', v):
            raise ValueError('Invalid ID number format')
        return v


class UserInDB(UserBase):
    id: str
    is_active: bool
    is_superuser: bool

    class Config:
        orm_mode = True


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    full_name: Optional[str] = None


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class TokenPayload(BaseModel):
    sub: Optional[str] = None
