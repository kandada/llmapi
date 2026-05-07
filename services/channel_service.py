from typing import Optional, List, Dict
import json
from sqlalchemy.orm import Session

from models import channel, ability
from models.channel import Channel, ChannelStatus
from config import config
from utils.time import get_timestamp


class ChannelService:
    def __init__(self, db: Session):
        self.db = db

    def get_all_channels(self, offset: int = 0, limit: int = 25) -> List[Channel]:
        return self.db.query(Channel).order_by(Channel.id.desc()).limit(limit).offset(offset).all()

    def get_channel_by_id(self, channel_id: int, include_key: bool = False) -> Optional[Channel]:
        if include_key:
            return self.db.query(Channel).filter(Channel.id == channel_id).first()
        return self.db.query(Channel).filter(Channel.id == channel_id).first()

    def search_channels(self, keyword: str) -> List[Channel]:
        try:
            cid = int(keyword)
            return self.db.query(Channel).filter(Channel.id == cid).all()
        except ValueError:
            return self.db.query(Channel).filter(Channel.name.like(f"{keyword}%")).all()

    def create_channel(self, channel_data: dict) -> Channel:
        ch = Channel(
            type=channel_data.get("type", 0),
            key=channel_data.get("key", ""),
            status=ChannelStatus.ENABLED,
            name=channel_data.get("name", ""),
            weight=channel_data.get("weight", 0),
            created_time=get_timestamp(),
            test_time=0,
            response_time=0,
            base_url=channel_data.get("base_url", ""),
            models=channel_data.get("models", ""),
            group=channel_data.get("group", "default"),
            model_mapping=channel_data.get("model_mapping", ""),
            priority=channel_data.get("priority", 0),
            config=channel_data.get("config", ""),
            system_prompt=channel_data.get("system_prompt", ""),
            llm_gateway=channel_data.get("llm_gateway", "openai"),
            balance=0,
            balance_updated_time=get_timestamp(),
            used_quota=0,
        )
        self.db.add(ch)
        self.db.commit()
        self.db.refresh(ch)
        self._update_abilities(ch)
        return ch

    def update_channel(self, channel_id: int, update_data: dict) -> Optional[Channel]:
        ch = self.db.query(Channel).filter(Channel.id == channel_id).first()
        if not ch:
            return None

        for key, value in update_data.items():
            if value is not None and hasattr(ch, key):
                setattr(ch, key, value)

        self.db.commit()
        self._update_abilities(ch)
        return ch

    def delete_channel(self, channel_id: int) -> bool:
        ch = self.db.query(Channel).filter(Channel.id == channel_id).first()
        if not ch:
            return False
        self.db.query(ability.Ability).filter(ability.Ability.channel_id == channel_id).delete()
        self.db.delete(ch)
        self.db.commit()
        return True

    def update_response_time(self, channel_id: int, response_time: int):
        self.db.query(Channel).filter(Channel.id == channel_id).update({
            "response_time": response_time,
            "test_time": get_timestamp(),
        })
        self.db.commit()

    def update_balance(self, channel_id: int, balance: float):
        self.db.query(Channel).filter(Channel.id == channel_id).update({
            "balance": balance,
            "balance_updated_time": get_timestamp(),
        })
        self.db.commit()

    def disable_channel(self, channel_id: int, status: int = ChannelStatus.AUTO_DISABLED):
        self.db.query(Channel).filter(Channel.id == channel_id).update({"status": status})
        self.db.query(ability.Ability).filter(ability.Ability.channel_id == channel_id).update({"enabled": False})
        self.db.commit()

    def enable_channel(self, channel_id: int):
        self.db.query(Channel).filter(Channel.id == channel_id).update({"status": ChannelStatus.ENABLED})
        self.db.query(ability.Ability).filter(ability.Ability.channel_id == channel_id).update({"enabled": True})
        self.db.commit()

    def _update_abilities(self, ch: Channel):
        models = [m.strip() for m in ch.models.split(",") if m.strip()]
        groups = [g.strip() for g in ch.group.split(",") if g.strip()]
        enabled = ch.status == ChannelStatus.ENABLED
        priority = ch.priority or 0

        existing = self.db.query(ability.Ability).filter(
            ability.Ability.channel_id == ch.id
        ).all()
        existing_set = {(a.group, a.model) for a in existing}

        new_set = set()
        for model in models:
            for group in groups:
                new_set.add((group, model))

        to_delete = [a for a in existing if (a.group, a.model) not in new_set]
        for a in to_delete:
            self.db.delete(a)

        to_add = []
        for group, model in new_set - existing_set:
            to_add.append(ability.Ability(
                group=group, model=model, channel_id=ch.id,
                enabled=enabled, priority=priority,
            ))

        for a in existing:
            if (a.group, a.model) in new_set:
                a.enabled = enabled
                a.priority = priority

        if to_add:
            self.db.add_all(to_add)
        self.db.commit()

    def get_enabled_channels_count(self) -> int:
        return self.db.query(Channel).filter(Channel.status == ChannelStatus.ENABLED).count()

    def get_all_enabled_channels(self) -> List[Channel]:
        return self.db.query(Channel).filter(Channel.status == ChannelStatus.ENABLED).all()

    def get_all_groups(self) -> List[str]:
        groups = self.db.query(Channel.group).distinct().all()
        return [g[0] for g in groups if g[0]]

    def get_channels_by_group(self, group: str) -> List[Channel]:
        return self.db.query(Channel).filter(Channel.group == group).all()

    def get_group_stats(self) -> List[Dict]:
        groups = self.get_all_groups()
        stats = []
        for g in groups:
            channels = self.db.query(Channel).filter(Channel.group == g).all()
            enabled = sum(1 for c in channels if c.status == ChannelStatus.ENABLED)
            stats.append({
                "name": g,
                "total": len(channels),
                "enabled": enabled,
                "disabled": len(channels) - enabled,
            })
        return stats

    def rename_group(self, old_group: str, new_group: str) -> int:
        if old_group == new_group:
            return 0
        result = self.db.query(Channel).filter(Channel.group == old_group).update({"group": new_group})
        self.db.commit()
        self.db.query(ability.Ability).filter(ability.Ability.group == old_group).update({"group": new_group})
        self.db.commit()
        return result

    def delete_group(self, group: str, move_to: str = "default") -> Dict[str, int]:
        if group == "default":
            return {"error": "Cannot delete default group", "moved": 0, "deleted": 0}
        channels = self.db.query(Channel).filter(Channel.group == group).all()
        moved = 0
        deleted = 0
        for ch in channels:
            if move_to:
                ch.group = move_to
                moved += 1
            else:
                self.db.delete(ch)
                deleted += 1
        self.db.commit()
        self.db.query(ability.Ability).filter(ability.Ability.group == group).delete()
        self.db.commit()
        return {"moved": moved, "deleted": deleted}

    def create_group(self, group: str) -> Dict[str, any]:
        if not group or len(group) > 32:
            return {"error": "Invalid group name", "created": False}
        existing = self.db.query(Channel.group).filter(Channel.group == group).distinct().first()
        if existing:
            return {"error": "Group already exists", "created": False}
        return {"group": group, "created": True}
