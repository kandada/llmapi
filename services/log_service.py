from typing import Optional, List
from sqlalchemy.orm import Session

from models import log as log_model
from models.log import Log, LogType
from utils.time import get_timestamp


class LogService:
    def __init__(self, db: Session):
        self.db = db

    def get_all_logs(
        self,
        log_type: int = 0,
        start_timestamp: int = 0,
        end_timestamp: int = 0,
        model_name: str = "",
        username: str = "",
        token_name: str = "",
        channel_id: int = 0,
        offset: int = 0,
        limit: int = 25,
    ) -> List[Log]:
        query = self.db.query(Log)

        if log_type != LogType.UNKNOWN:
            query = query.filter(Log.type == log_type)
        if model_name:
            query = query.filter(Log.model_name == model_name)
        if username:
            query = query.filter(Log.username == username)
        if token_name:
            query = query.filter(Log.token_name == token_name)
        if start_timestamp:
            query = query.filter(Log.created_at >= start_timestamp)
        if end_timestamp:
            query = query.filter(Log.created_at <= end_timestamp)
        if channel_id:
            query = query.filter(Log.channel_id == channel_id)

        return query.order_by(Log.id.desc()).limit(limit).offset(offset).all()

    def get_user_logs(
        self,
        user_id: int,
        log_type: int = 0,
        start_timestamp: int = 0,
        end_timestamp: int = 0,
        model_name: str = "",
        token_name: str = "",
        offset: int = 0,
        limit: int = 25,
    ) -> List[Log]:
        query = self.db.query(Log).filter(Log.user_id == user_id)

        if log_type != LogType.UNKNOWN:
            query = query.filter(Log.type == log_type)
        if model_name:
            query = query.filter(Log.model_name == model_name)
        if token_name:
            query = query.filter(Log.token_name == token_name)
        if start_timestamp:
            query = query.filter(Log.created_at >= start_timestamp)
        if end_timestamp:
            query = query.filter(Log.created_at <= end_timestamp)

        return query.order_by(Log.id.desc()).limit(limit).offset(offset).all()

    def record_log(self, log_data: dict):
        log = Log(**log_data)
        self.db.add(log)
        self.db.commit()

    def record_topup(self, user_id: int, username: str, content: str, quota: int):
        log = Log(
            user_id=user_id,
            username=username,
            created_at=get_timestamp(),
            type=LogType.TOPUP,
            content=content,
            quota=0,
        )
        self.db.add(log)
        self.db.commit()

    def record_consume(
        self,
        user_id: int,
        username: str,
        token_name: str,
        model_name: str,
        quota: int,
        prompt_tokens: int,
        completion_tokens: int,
        channel_id: int,
        request_id: str,
        elapsed_time: int,
        is_stream: bool = False,
    ):
        log = Log(
            user_id=user_id,
            username=username,
            created_at=get_timestamp(),
            type=LogType.CONSUME,
            token_name=token_name,
            model_name=model_name,
            quota=quota,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            channel_id=channel_id,
            request_id=request_id,
            elapsed_time=elapsed_time,
            is_stream=is_stream,
        )
        self.db.add(log)
        self.db.commit()

    def record_system(self, user_id: int, username: str, content: str):
        log = Log(
            user_id=user_id,
            username=username,
            created_at=get_timestamp(),
            type=LogType.SYSTEM,
            content=content,
        )
        self.db.add(log)
        self.db.commit()

    def sum_used_quota(
        self,
        log_type: int = LogType.CONSUME,
        start_timestamp: int = 0,
        end_timestamp: int = 0,
        model_name: str = "",
        username: str = "",
        token_name: str = "",
        channel_id: int = 0,
    ) -> int:
        query = self.db.query(Log).filter(Log.type == log_type)

        if username:
            query = query.filter(Log.username == username)
        if token_name:
            query = query.filter(Log.token_name == token_name)
        if start_timestamp:
            query = query.filter(Log.created_at >= start_timestamp)
        if end_timestamp:
            query = query.filter(Log.created_at <= end_timestamp)
        if model_name:
            query = query.filter(Log.model_name == model_name)
        if channel_id:
            query = query.filter(Log.channel_id == channel_id)

        result = query.all()
        return sum(log.quota for log in result)

    def delete_old_logs(self, target_timestamp: int) -> int:
        count = self.db.query(Log).filter(Log.created_at < target_timestamp).delete()
        self.db.commit()
        return count
