from sqlalchemy import Column, Integer, String, BigInteger, Boolean, Table
from sqlalchemy.orm import mapper
from .base import Base


class Ability(Base):
    __tablename__ = "abilities"

    group = Column(String(32), primary_key=True, autoincrement=False)
    model = Column(String(255), primary_key=True, autoincrement=False)
    channel_id = Column(Integer, primary_key=True, autoincrement=False, index=True)
    enabled = Column(Boolean, default=True)
    priority = Column(BigInteger, default=0)
