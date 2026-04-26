from typing import Optional, List
from sqlalchemy.orm import Session

from models import redemption as redemption_model
from models.redemption import Redemption, RedemptionStatus
from utils.time import get_timestamp
from utils.random import generate_uuid


class RedemptionService:
    def __init__(self, db: Session):
        self.db = db

    def get_all_redemptions(self, offset: int = 0, limit: int = 25) -> List[Redemption]:
        return self.db.query(Redemption).order_by(Redemption.id.desc()).limit(limit).offset(offset).all()

    def get_redemption_by_id(self, redemption_id: int) -> Optional[Redemption]:
        return self.db.query(Redemption).filter(Redemption.id == redemption_id).first()

    def search_redemptions(self, keyword: str) -> List[Redemption]:
        try:
            rid = int(keyword)
            return self.db.query(Redemption).filter(Redemption.id == rid).all()
        except ValueError:
            return self.db.query(Redemption).filter(Redemption.name.like(f"{keyword}%")).all()

    def create_redemption(self, user_id: int, name: str, quota: int, count: int = 1) -> List[str]:
        keys = []
        for _ in range(count):
            key = generate_uuid()
            redemption = Redemption(
                user_id=user_id,
                key=key,
                status=RedemptionStatus.ENABLED,
                name=name,
                quota=quota,
                created_time=get_timestamp(),
            )
            self.db.add(redemption)
            keys.append(key)
        self.db.commit()
        return keys

    def update_redemption(self, redemption_id: int, update_data: dict) -> Optional[Redemption]:
        redemption = self.db.query(Redemption).filter(Redemption.id == redemption_id).first()
        if not redemption:
            return None

        for key, value in update_data.items():
            if value is not None and hasattr(redemption, key):
                setattr(redemption, key, value)

        self.db.commit()
        self.db.refresh(redemption)
        return redemption

    def delete_redemption(self, redemption_id: int) -> bool:
        redemption = self.db.query(Redemption).filter(Redemption.id == redemption_id).first()
        if not redemption:
            return False
        self.db.delete(redemption)
        self.db.commit()
        return True

    def redeem(self, key: str, user_id: int) -> tuple[Optional[int], Optional[str]]:
        redemption = self.db.query(Redemption).filter(Redemption.key == key).first()
        if not redemption:
            return None, "Invalid redemption code"

        if redemption.status != RedemptionStatus.ENABLED:
            return None, "Redemption code already used"

        quota = redemption.quota
        redemption.status = RedemptionStatus.USED
        redemption.redeemed_time = get_timestamp()
        self.db.commit()

        return quota, None
