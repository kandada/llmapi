from sqlalchemy import Column, Integer, String, Text, BigInteger
from .base import BaseModel


class Package(BaseModel):
    __tablename__ = "packages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)

    quota = Column(BigInteger, nullable=False, default=0)

    prices = Column(Text, default="{}")

    status = Column(Integer, default=1)

    payment_providers = Column(Text, default="stripe")

    sort_order = Column(Integer, default=0)

    created_time = Column(BigInteger, nullable=False)
    updated_time = Column(BigInteger, nullable=False)


class PackageStatus:
    DISABLED = 0
    ENABLED = 1