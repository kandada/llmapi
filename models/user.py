from sqlalchemy import Column, Integer, String, BigInteger
from .base import BaseModel


class User(BaseModel):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(12), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)
    display_name = Column(String(20), index=True)
    role = Column(Integer, default=1)  # 0=guest, 1=user, 10=admin, 100=root
    status = Column(Integer, default=1)  # 1=enabled, 2=disabled, 3=deleted
    email = Column(String(50), index=True)
    github_id = Column(String(255), index=True)
    wechat_id = Column(String(255), index=True)
    lark_id = Column(String(255), index=True)
    oidc_id = Column(String(255), index=True)
    access_token = Column(String(32), unique=True, index=True)
    quota = Column(BigInteger, default=0)
    used_quota = Column(BigInteger, default=0)
    request_count = Column(Integer, default=0)
    group = Column(String(32), default="default")
    aff_code = Column(String(32), unique=True, index=True)
    inviter_id = Column(Integer, default=0)


class UserRole:
    GUEST = 0
    COMMON = 1
    ADMIN = 10
    ROOT = 100


class UserStatus:
    ENABLED = 1
    DISABLED = 2
    DELETED = 3
