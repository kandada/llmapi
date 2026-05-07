from pydantic import BaseModel, ConfigDict
from typing import Optional


class TokenCreate(BaseModel):
    name: str
    expired_time: int = -1
    remain_quota: int = 0
    unlimited_quota: bool = False
    models: Optional[str] = None
    subnet: Optional[str] = None
    channel_group: Optional[str] = None


class TokenUpdate(BaseModel):
    id: int
    name: Optional[str] = None
    status: Optional[int] = None
    expired_time: Optional[int] = None
    remain_quota: Optional[int] = None
    unlimited_quota: Optional[bool] = None
    models: Optional[str] = None
    subnet: Optional[str] = None
    channel_group: Optional[str] = None


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
    channel_group: Optional[str] = None
