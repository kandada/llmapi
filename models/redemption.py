from sqlalchemy import Column, Integer, String, BigInteger, Text
from .base import BaseModel


class Redemption(BaseModel):
    __tablename__ = "redemptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    key = Column(String(32), unique=True, nullable=False, index=True)
    status = Column(Integer, default=1)  # 1=enabled, 2=disabled, 3=used
    name = Column(String(255), index=True)
    quota = Column(BigInteger, default=100)
    created_time = Column(BigInteger, nullable=False)
    redeemed_time = Column(BigInteger, default=0)


class RedemptionStatus:
    ENABLED = 1
    DISABLED = 2
    USED = 3
