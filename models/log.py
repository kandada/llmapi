from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean
from .base import BaseModel


class Log(BaseModel):
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    created_at = Column(BigInteger, nullable=False, index=True)
    type = Column(Integer, index=True)  # 1=topup, 2=consume, 3=manage, 4=system, 5=test
    content = Column(Text)
    username = Column(String(255), index=True)
    token_name = Column(String(255))
    model_name = Column(String(255), index=True)
    quota = Column(Integer, default=0)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    channel_id = Column(Integer, index=True)
    request_id = Column(String(255), default="")
    elapsed_time = Column(Integer, default=0)  # ms
    is_stream = Column(Boolean, default=False)
    system_prompt_reset = Column(Boolean, default=False)


class LogType:
    UNKNOWN = 0
    TOPUP = 1
    CONSUME = 2
    MANAGE = 3
    SYSTEM = 4
    TEST = 5
