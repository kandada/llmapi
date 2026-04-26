from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    username: str
    display_name: Optional[str] = None


class UserCreate(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    display_name: Optional[str] = None
    role: Optional[int] = 1


class UserUpdate(BaseModel):
    password: Optional[str] = None
    display_name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[int] = None
    status: Optional[int] = None
    quota: Optional[int] = None
    group: Optional[str] = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    display_name: str
    role: int
    status: int
    email: Optional[str] = None
    quota: int
    used_quota: int
    group: str


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    key: str
    status: int
    name: str
    created_time: int
    accessed_time: int
    expired_time: int
    remain_quota: int
    unlimited_quota: bool
    used_quota: int
    models: Optional[str] = None
    subnet: Optional[str] = None
