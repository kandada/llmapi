from fastapi import Depends
from sqlalchemy.orm import Session
from typing import Optional

from database import get_session
from services.channel_service import ChannelService
from monitor.channel import ChannelMonitor
from middleware.auth import AuthContext, require_admin
from schemas.channel import ChannelCreate, ChannelUpdate, ChannelResponse
from schemas.request import APIResponse
from models.channel import ChannelStatus


class ChannelController:
    def __init__(self, db: Session = Depends(get_session)):
        self.db = db
        self.channel_service = ChannelService(db)
        self.monitor = ChannelMonitor(db)

    async def get_all_channels(self, p: int = 0, ctx: AuthContext = Depends(require_admin)) -> APIResponse:
        channels = self.channel_service.get_all_channels(offset=p * 25, limit=25)
        data = [ChannelResponse.from_orm_with_config(ch) for ch in channels]
        return APIResponse(success=True, data=[d.dict() for d in data])

    async def get_channel(self, channel_id: int, ctx: AuthContext = Depends(require_admin)) -> APIResponse:
        channel = self.channel_service.get_channel_by_id(channel_id)
        if not channel:
            return APIResponse(success=False, message="Channel not found")

        return APIResponse(success=True, data=ChannelResponse.from_orm_with_config(channel).dict())

    async def search_channels(self, keyword: str, ctx: AuthContext = Depends(require_admin)) -> APIResponse:
        channels = self.channel_service.search_channels(keyword)
        data = [ChannelResponse.from_orm_with_config(ch) for ch in channels]
        return APIResponse(success=True, data=[d.dict() for d in data])

    async def add_channel(self, channel_data: ChannelCreate, ctx: AuthContext = Depends(require_admin)) -> APIResponse:
        keys = channel_data.key.split("\n")
        created_ids = []

        for key in keys:
            key = key.strip()
            if not key:
                continue

            data = channel_data.dict()
            data["key"] = key
            data.pop("id", None)

            channel = self.channel_service.create_channel(data)
            created_ids.append(channel.id)

        return APIResponse(success=True, data={"ids": created_ids})

    async def update_channel(self, update_data: ChannelUpdate, ctx: AuthContext = Depends(require_admin)) -> APIResponse:
        channel = self.channel_service.update_channel(update_data.id, update_data.dict(exclude_unset=True))
        if not channel:
            return APIResponse(success=False, message="Channel not found")

        return APIResponse(success=True, data=ChannelResponse.from_orm_with_config(channel).dict())

    async def delete_channel(self, channel_id: int, ctx: AuthContext = Depends(require_admin)) -> APIResponse:
        success = self.channel_service.delete_channel(channel_id)
        if not success:
            return APIResponse(success=False, message="Channel not found")

        return APIResponse(success=True)

    async def delete_disabled_channels(self, ctx: AuthContext = Depends(require_admin)) -> APIResponse:
        from models.channel import Channel
        channels = self.db.query(Channel).filter(
            Channel.status.in_([ChannelStatus.MANUALLY_DISABLED, ChannelStatus.AUTO_DISABLED])
        ).all()

        count = 0
        for ch in channels:
            self.channel_service.delete_channel(ch.id)
            count += 1

        return APIResponse(success=True, data={"count": count})

    async def test_channel(self, channel_id: int, ctx: AuthContext = Depends(require_admin)) -> APIResponse:
        channel = self.channel_service.get_channel_by_id(channel_id, include_key=True)
        if not channel:
            return APIResponse(success=False, message="Channel not found")

        success, elapsed = await self.monitor.test_channel(channel)

        if success:
            return APIResponse(success=True, data={"response_time": elapsed})
        else:
            return APIResponse(success=False, message="Channel test failed")

    async def test_all_channels(self, ctx: AuthContext = Depends(require_admin)) -> APIResponse:
        channels = self.channel_service.get_all_enabled_channels()
        results = []

        for channel in channels:
            success, elapsed = await self.monitor.test_channel(channel)
            results.append({
                "id": channel.id,
                "name": channel.name,
                "success": success,
                "response_time": elapsed,
            })

            if not success and self.monitor.should_disable(channel.id):
                self.monitor.disable_channel(channel.id, "Test failed")

        return APIResponse(success=True, data=results)

    async def update_channel_balance(self, channel_id: int = 0, ctx: AuthContext = Depends(require_admin)) -> APIResponse:
        if channel_id:
            channel = self.channel_service.get_channel_by_id(channel_id, include_key=True)
            if channel:
                await self._update_balance(channel)
            return APIResponse(success=True)
        else:
            channels = self.channel_service.get_all_enabled_channels()
            for ch in channels:
                await self._update_balance(ch)
            return APIResponse(success=True, data={"count": len(channels)})

    async def _update_balance(self, channel):
        pass

    async def get_all_groups(self, ctx: AuthContext = Depends(require_admin)) -> APIResponse:
        stats = self.channel_service.get_group_stats()
        return APIResponse(success=True, data=stats)

    async def get_channels_by_group(self, group: str, ctx: AuthContext = Depends(require_admin)) -> APIResponse:
        channels = self.channel_service.get_channels_by_group(group)
        data = [ChannelResponse.from_orm_with_config(ch) for ch in channels]
        return APIResponse(success=True, data=[d.dict() for d in data])

    async def rename_group(self, old_group: str, new_group: str, ctx: AuthContext = Depends(require_admin)) -> APIResponse:
        if not new_group or len(new_group) > 32:
            return APIResponse(success=False, message="Invalid group name")
        count = self.channel_service.rename_group(old_group, new_group)
        return APIResponse(success=True, data={"renamed": count})

    async def delete_group(self, group: str, move_to: str = "default", ctx: AuthContext = Depends(require_admin)) -> APIResponse:
        result = self.channel_service.delete_group(group, move_to)
        if "error" in result:
            return APIResponse(success=False, message=result["error"])
        return APIResponse(success=True, data=result)
