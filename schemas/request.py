from pydantic import BaseModel, ConfigDict
from typing import Optional, Any, Dict


class APIResponse(BaseModel):
    success: bool
    message: str = ""
    data: Optional[Any] = None


class OptionItem(BaseModel):
    key: str
    value: str


class OptionUpdate(BaseModel):
    key: str
    value: str


class LogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    created_at: int
    type: int
    content: Optional[str] = None
    username: Optional[str] = None
    token_name: Optional[str] = None
    model_name: Optional[str] = None
    quota: int
    prompt_tokens: int
    completion_tokens: int
    channel_id: Optional[int] = None
    request_id: str
    elapsed_time: int
    is_stream: bool


class StatusResponse(BaseModel):
    version: str
    status: str
    mode: str


class ResetPasswordRequest(BaseModel):
    new_password: str
