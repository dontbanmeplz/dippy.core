from dippy.core.caching.cache import Cache
from dippy.core.enums import Event as E
from dippy.core.events import BaseEventStream
from dippy.core.models.events import (
    EventChannelCreate,
    EventChannelDelete,
    EventChannelUpdate,
    EventGuildCreate,
    EventGuildDelete,
    EventGuildMemberAdd,
    EventGuildMemberRemove,
    EventGuildMemberUpdate,
    EventGuildMembersChunk,
    EventGuildUpdate,
    EventMessageCreate,
    EventMessageDelete,
    EventMessageDeleteBulk,
    EventMessageUpdate,
    GuildModel,
)
from dippy.core.interfaces.channel import Channel
from dippy.core.interfaces.guild import Guild
from dippy.core.interfaces.member import Member
from dippy.core.interfaces.message import Message
from dippy.core.interfaces.user import User
from typing import Union


class CacheManager:
    def __init__(
        self,
        gateway: GatewayConnection,
        max_channels: int = 1000,
        max_guilds: int = 1_000,
        max_members: int = 10_000,
        max_messages: int = 1_000,
        max_users: int = 10_000,
    ):
        self.channels = Cache(max_channels, Channel)
        self.guilds = Cache(max_guilds, Guild)
        self.messages = Cache(max_messages, Message)
        self.members = Cache(max_members, Member)
        self.users = Cache(max_users, User)

        gateway.on(E.CHANNEL_CREATE, self.channel_update)
        gateway.on(E.CHANNEL_UPDATE, self.channel_update)
        gateway.on(E.CHANNEL_DELETE, self.channel_remove)

        gateway.on(E.GUILD_CREATE, self.guild_update)
        gateway.on(E.GUILD_UPDATE, self.guild_update)
        gateway.on(E.GUILD_DELETE, self.guild_remove)

        gateway.on(E.GUILD_MEMBER_ADD, self.member_update)
        gateway.on(E.GUILD_MEMBER_UPDATE, self.member_update)
        gateway.on(E.GUILD_MEMBER_REMOVE, self.member_remove)
        gateway.on(E.GUILD_MEMBERS_CHUNK, self.member_update_chunk)

        gateway.on(E.MESSAGE_CREATE, self.message_update)
        gateway.on(E.MESSAGE_UPDATE, self.message_update)
        gateway.on(E.MESSAGE_DELETE, self.message_delete)
        gateway.on(E.MESSAGE_DELETE_BULK, self.message_delete_bulk)

    async def channel_update(
        self, event: Union[EventChannelCreate, EventChannelUpdate]
    ):
        self.channels.add(event)

    async def channel_remove(self, event: EventChannelDelete):
        self.channels.remove(event.id)

    async def channel_update_bulk(
        self, event: Union[EventGuildCreate, EventGuildUpdate, GuildModel]
    ):
        for channel in event.channels:
            self.channels.add(channel)

    async def guild_update(self, event: Union[EventGuildCreate, EventGuildUpdate]):
        self.guilds.add(event)
        await self.channel_update_bulk(event)
        await self.member_update_chunk(event)

    async def guild_remove(self, event: EventGuildDelete):
        self.guilds.remove(event.id)

    async def message_update(
        self, event: Union[EventMessageCreate, EventMessageUpdate]
    ):
        self.messages.add(event)

    async def message_delete(self, event: EventMessageDelete):
        self.messages.remove(event.id)

    async def message_delete_bulk(self, event: EventMessageDeleteBulk):
        for message_id in event.ids:
            self.messages.remove(message_id)

    async def member_update(
        self, event: Union[EventGuildMemberAdd, EventGuildMemberUpdate]
    ):
        if event.user:
            self.users.add(event.user)
        user = self.users.get(event.user.id)
        self.members.add(event, user)

    async def member_remove(self, event: EventGuildMemberRemove):
        self.members.remove(event.user.id)

    async def member_update_chunk(
        self, event: Union[EventGuildMembersChunk, EventGuildCreate, EventGuildUpdate]
    ):
        for member in event.members:
            if member.user:
                self.users.add(member.user)
            user = self.users.get(member.user.id)
            self.members.add(member, user)