from sqlalchemy import Column, Integer, String, BigInteger, Boolean, Text
from .base import BaseModel


class Token(BaseModel):
    __tablename__ = "tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    key = Column(String(48), unique=True, nullable=False, index=True)
    status = Column(Integer, default=1)  # 1=enabled, 2=disabled, 3=expired, 4=exhausted
    name = Column(String(255), index=True)
    created_time = Column(BigInteger, nullable=False)
    accessed_time = Column(BigInteger, nullable=False)
    expired_time = Column(BigInteger, default=-1)  # -1 means never expired
    remain_quota = Column(BigInteger, default=0)
    unlimited_quota = Column(Boolean, default=False)
    used_quota = Column(BigInteger, default=0)
    models = Column(Text)  # allowed models, empty means all
    subnet = Column(String(100), default="")  # allowed IP subnets
    channel_group = Column(String(32), default="")  # channel group restriction, empty means no restriction


class TokenStatus:
    ENABLED = 1
    DISABLED = 2
    EXPIRED = 3
    EXHAUSTED = 4
