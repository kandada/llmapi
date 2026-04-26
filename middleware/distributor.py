from fastapi import Request, HTTPException, Depends
from typing import Optional, List
import random
import json
from sqlalchemy.orm import Session

from database import get_session
from services.channel_service import ChannelService
from services.user_service import UserService
from models.channel import Channel, ChannelStatus
from models.ability import Ability


def weighted_choice(channels: List[Channel]) -> Channel:
    if not channels:
        return None
    if len(channels) == 1:
        return channels[0]

    total_weight = sum(c.weight if c.weight > 0 else 1 for c in channels)
    r = random.uniform(0, total_weight)
    cumsum = 0
    for c in channels:
        weight = c.weight if c.weight > 0 else 1
        cumsum += weight
        if cumsum >= r:
            return c
    return channels[-1]


class Distributor:
    def __init__(self, db: Session):
        self.db = db
        self.channel_service = ChannelService(db)

    def select_channel(self, group: str, model: str, token_channel_group: str = "", ignore_priority: bool = False) -> Optional[Channel]:
        effective_group = token_channel_group or group

        abilities = self.db.query(Ability).filter(
            Ability.group == effective_group,
            Ability.model == model,
            Ability.enabled == True,
        ).all()

        if not abilities:
            return None

        priority_channels = {}
        for ability in abilities:
            channel = self.db.query(Channel).filter(Channel.id == ability.channel_id).first()
            if channel and channel.status == ChannelStatus.ENABLED:
                priority = ability.priority or 0
                if priority not in priority_channels:
                    priority_channels[priority] = []
                priority_channels[priority].append(channel)

        if not priority_channels:
            return None

        max_priority = max(priority_channels.keys())

        if ignore_priority:
            all_channels = []
            for p, chs in priority_channels.items():
                all_channels.extend(chs)
            if not all_channels:
                all_channels = priority_channels[max_priority]
        else:
            all_channels = priority_channels[max_priority]

        return weighted_choice(all_channels)

    def get_model_mapping(self, channel: Channel) -> dict:
        if not channel.model_mapping:
            return {}
        try:
            return json.loads(channel.model_mapping)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            channel_id = getattr(channel, 'id', 'unknown')
            raw_value = getattr(channel, 'model_mapping', '')[:100] if channel.model_mapping else ''
            logger.warning(f"Failed to parse model_mapping for channel {channel_id}: {e}, raw value: {raw_value}")
            return {}

    def map_model(self, channel: Channel, model: str) -> str:
        mapping = self.get_model_mapping(channel)
        return mapping.get(model, model)

    def get_base_url(self, channel: Channel) -> str:
        return channel.base_url or ""


async def distribute_request(
    request: Request,
    group: str,
    model: str,
    db: Session = Depends(get_session),
) -> dict:
    distributor = Distributor(db)
    channel = distributor.select_channel(group, model)

    if not channel:
        raise HTTPException(status_code=503, detail=f"No available channel for model {model} in group {group}")

    mapped_model = distributor.map_model(channel, model)
    base_url = distributor.get_base_url(channel)

    return {
        "channel": channel,
        "model": mapped_model,
        "base_url": base_url,
    }
