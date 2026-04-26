from typing import Optional, List
from sqlalchemy.orm import Session
from datetime import datetime

from models import token as token_model
from models.token import Token, TokenStatus
from utils.time import get_timestamp
from utils.random import generate_key


class TokenService:
    def __init__(self, db: Session):
        self.db = db

    def get_user_tokens(self, user_id: int, offset: int = 0, limit: int = 25) -> List[Token]:
        return self.db.query(Token).filter(Token.user_id == user_id).order_by(Token.id.desc()).limit(limit).offset(offset).all()

    def get_token_by_key(self, key: str) -> Optional[Token]:
        return self.db.query(Token).filter(Token.key == key).first()

    def get_token_by_id(self, token_id: int) -> Optional[Token]:
        return self.db.query(Token).filter(Token.id == token_id).first()

    def search_user_tokens(self, user_id: int, keyword: str) -> List[Token]:
        return self.db.query(Token).filter(
            Token.user_id == user_id,
            Token.name.like(f"{keyword}%")
        ).all()

    def create_token(self, user_id: int, token_data: dict) -> Token:
        tk = Token(
            user_id=user_id,
            key=generate_key(),
            status=TokenStatus.ENABLED,
            name=token_data.get("name", ""),
            created_time=get_timestamp(),
            accessed_time=get_timestamp(),
            expired_time=token_data.get("expired_time", -1),
            remain_quota=token_data.get("remain_quota", 0),
            unlimited_quota=token_data.get("unlimited_quota", False),
            models=token_data.get("models"),
            subnet=token_data.get("subnet", ""),
            channel_group=token_data.get("channel_group", ""),
        )
        self.db.add(tk)
        self.db.commit()
        self.db.refresh(tk)
        return tk

    def update_token(self, token_id: int, user_id: int, update_data: dict) -> Optional[Token]:
        tk = self.db.query(Token).filter(Token.id == token_id, Token.user_id == user_id).first()
        if not tk:
            return None

        for key, value in update_data.items():
            if value is not None and hasattr(tk, key):
                setattr(tk, key, value)

        self.db.commit()
        self.db.refresh(tk)
        return tk

    def delete_token(self, token_id: int, user_id: int) -> bool:
        tk = self.db.query(Token).filter(Token.id == token_id, Token.user_id == user_id).first()
        if not tk:
            return False
        self.db.delete(tk)
        self.db.commit()
        return True

    def validate_token(self, key: str) -> tuple[Optional[Token], Optional[str]]:
        tk = self.get_token_by_key(key)
        if not tk:
            return None, "Invalid token"

        if tk.status == TokenStatus.EXHAUSTED:
            return None, f"Token {tk.name} quota exhausted"
        if tk.status == TokenStatus.EXPIRED:
            return None, "Token expired"
        if tk.status != TokenStatus.ENABLED:
            return None, "Token not available"

        now = get_timestamp()
        if tk.expired_time != -1 and tk.expired_time < now:
            tk.status = TokenStatus.EXPIRED
            self.db.commit()
            return None, "Token expired"

        if not tk.unlimited_quota and tk.remain_quota <= 0:
            tk.status = TokenStatus.EXHAUSTED
            self.db.commit()
            return None, "Token quota exhausted"

        return tk, None

    def update_access_time(self, token_id: int):
        self.db.query(Token).filter(Token.id == token_id).update({
            "accessed_time": get_timestamp()
        })
        self.db.commit()

    def decrease_quota(self, token_id: int, quota: int):
        result = self.db.query(Token).filter(
            Token.id == token_id,
            Token.remain_quota >= quota
        ).update({
            "remain_quota": Token.remain_quota - quota,
            "used_quota": Token.used_quota + quota,
            "accessed_time": get_timestamp(),
        })
        self.db.commit()
        return result > 0

    def increase_quota(self, token_id: int, quota: int):
        self.db.query(Token).filter(Token.id == token_id).update({
            "remain_quota": Token.remain_quota + quota,
            "accessed_time": get_timestamp(),
        })
        self.db.commit()
