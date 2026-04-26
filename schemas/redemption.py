from pydantic import BaseModel, ConfigDict
from typing import Optional


class RedemptionCreate(BaseModel):
    name: str
    quota: int = 100
    count: int = 1


class RedemptionUpdate(BaseModel):
    id: int
    name: Optional[str] = None
    status: Optional[int] = None
    quota: Optional[int] = None


class RedemptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    key: str
    status: int
    name: str
    quota: int
    created_time: int
    redeemed_time: int
