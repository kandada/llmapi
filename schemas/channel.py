from pydantic import BaseModel, ConfigDict
from typing import Optional
import json


class ChannelBase(BaseModel):
    name: str
    type: int
    models: str
    group: str = "default"


class ChannelCreate(BaseModel):
    name: str
    type: int
    key: str
    models: str
    group: str = "default"
    base_url: Optional[str] = ""
    model_mapping: Optional[str] = ""
    priority: Optional[int] = 0
    config: Optional[str] = ""
    system_prompt: Optional[str] = ""
    llm_gateway: Optional[str] = "openai"


class ChannelUpdate(BaseModel):
    id: int
    name: Optional[str] = None
    type: Optional[int] = None
    key: Optional[str] = None
    models: Optional[str] = None
    group: Optional[str] = None
    status: Optional[int] = None
    base_url: Optional[str] = None
    model_mapping: Optional[str] = None
    priority: Optional[int] = None
    config: Optional[str] = None
    system_prompt: Optional[str] = None
    weight: Optional[int] = None
    llm_gateway: Optional[str] = None


class ChannelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: int
    status: int
    name: str
    weight: int
    base_url: Optional[str] = ""
    models: str
    group: str
    model_mapping: Optional[str] = ""
    priority: int
    balance: float
    response_time: int
    test_time: int
    created_time: int
    used_quota: int
    llm_gateway: str = "openai"

    @classmethod
    def from_orm_with_config(cls, channel):
        config = {}
        if channel.config:
            try:
                config = json.loads(channel.config)
            except:
                pass
        return cls(
            id=channel.id,
            type=channel.type,
            status=channel.status,
            name=channel.name,
            weight=channel.weight or 0,
            base_url=channel.base_url or "",
            models=channel.models,
            group=channel.group,
            model_mapping=channel.model_mapping or "",
            priority=channel.priority or 0,
            balance=channel.balance or 0.0,
            response_time=channel.response_time or 0,
            test_time=channel.test_time or 0,
            created_time=channel.created_time or 0,
            used_quota=channel.used_quota or 0,
            llm_gateway=channel.llm_gateway or "openai",
        )


class ChannelConfig(BaseModel):
    region: Optional[str] = None
    sk: Optional[str] = None
    ak: Optional[str] = None
    user_id: Optional[str] = None
    api_version: Optional[str] = None
    library_id: Optional[str] = None
    plugin: Optional[str] = None
    vertex_ai_project_id: Optional[str] = None
    vertex_ai_adc: Optional[str] = None
