import os
from psycopg import AsyncConnection
from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class GuildData:
    guild_id: int
    message_id: int


@dataclass(slots=True)
class Ticket:
    id: int
    creator_id: int
    channel_id: int | None
    is_open: bool
    is_deleted: bool
    is_dm: bool
    close_message_id: int | None
    open_message_id: int | None


@dataclass(slots=True)
class TicketMessage:
    id: int
    sender_id: int
    sender_name: str
    message: str
    sent_at: datetime
    attachment_urls: list[str]


class Database:
    CONNINFO = os.getenv("PGURL")

    async def connect(self):
        return await AsyncConnection.connect(self.CONNINFO, autocommit=True)

    async def get_guild_data(self, guild_id: int) -> GuildData | None:
        async with await self.connect() as conn:
            cursor = conn.cursor()
            await cursor.execute(
                """
                SELECT guild_id, message_id FROM guild_data
                WHERE guild_id = %s
                LIMIT 1
                """,
                (guild_id,),
            )
            guild_data = await cursor.fetchone()
            return GuildData(*guild_data) if guild_data else None

    async def set_guild_data(self, guild_id: int, message_id: int) -> GuildData:
        async with await self.connect() as conn:
            cursor = conn.cursor()
            await cursor.execute(
                """
                INSERT INTO guild_data (guild_id, message_id)
                VALUES (%s, %s)
                """,
                (guild_id, message_id),
            )
            return GuildData(guild_id, message_id)

    async def get_all_tickest(self, is_deleted: bool) -> list[Ticket]:
        async with await self.connect() as conn:
            cursor = conn.cursor()
            await cursor.execute(
                """
                SELECT 
                    id,
                    creator_id,
                    channel_id,
                    is_open,
                    is_deleted,
                    is_dm,
                    close_message_id,
                    open_message_id
                FROM ticket
                WHERE is_deleted = %s
                """,
                (is_deleted,),
            )
            tickets = await cursor.fetchall()
            return [Ticket(*ticket) for ticket in tickets]

    async def get_ticket(self, id: int) -> Ticket | None:
        async with await self.connect() as conn:
            cursor = conn.cursor()
            await cursor.execute(
                """
                SELECT 
                    id,
                    creator_id,
                    channel_id,
                    is_open,
                    is_deleted,
                    is_dm,
                    close_message_id,
                    open_message_id
                FROM ticket
                WHERE id = %s
                """,
                (id,),
            )
            ticket = await cursor.fetchone()
            return Ticket(*ticket) if ticket else None

    async def get_ticket_by_channel(self, channel_id: int) -> Ticket | None:
        async with await self.connect() as conn:
            cursor = conn.cursor()
            await cursor.execute(
                """
                SELECT 
                    id,
                    creator_id,
                    channel_id,
                    is_open,
                    is_deleted,
                    is_dm,
                    close_message_id,
                    open_message_id
                FROM ticket
                WHERE channel_id = %s
                LIMIT 1
                """,
                (channel_id,),
            )
            ticket = await cursor.fetchone()
            return Ticket(*ticket) if ticket else None

    async def get_creator_tickets(self, creator_id: int, is_open: bool) -> list[Ticket]:
        async with await self.connect() as conn:
            cursor = conn.cursor()
            await cursor.execute(
                """
                SELECT
                    id,
                    creator_id,
                    channel_id,
                    is_open,
                    is_deleted,
                    is_dm,
                    close_message_id,
                    open_message_id
                FROM ticket
                WHERE creator_id = %s AND is_open = %s
                """,
                (creator_id, is_open),
            )
            return [Ticket(*ticket) for ticket in await cursor.fetchall()]

    async def create_ticket(self, creator_id: int, is_dm: bool) -> Ticket:
        async with await self.connect() as conn:
            cursor = conn.cursor()
            await cursor.execute(
                """
                INSERT INTO ticket (
                    creator_id,
                    channel_id,
                    is_open,
                    is_deleted,
                    is_dm,
                    close_message_id,
                    open_message_id
                ) VALUES (%s, null, true, false, %s, null, null)
                RETURNING id
                """,
                (creator_id, is_dm),
            )
            return Ticket(
                (await cursor.fetchone())[0],
                creator_id,
                None,
                True,
                False,
                is_dm,
                None,
                None,
            )

    async def update_open_ticket_data(
        self, ticket_id: int, channel_id: int, close_message_id: int
    ) -> None:
        async with await self.connect() as conn:
            cursor = conn.cursor()
            await cursor.execute(
                """
                UPDATE ticket SET channel_id = %s, close_message_id = %s
                WHERE id = %s
                """,
                (channel_id, close_message_id, ticket_id),
            )

    async def update_closed_ticket_data(self, ticket_id: int, open_message_id: int):
        async with await self.connect() as conn:
            cursor = conn.cursor()
            await cursor.execute(
                """
                UPDATE ticket SET open_message_id = %s
                WHERE id = %s
                """,
                (open_message_id, ticket_id),
            )

    async def update_ticket_type(self, ticket_id: int, is_dm: bool) -> None:
        async with await self.connect() as conn:
            cursor = conn.cursor()
            await cursor.execute(
                """
                UPDATE ticket SET is_dm = %s
                WHERE id = %s
                """,
                (is_dm, ticket_id),
            )

    async def close_ticket(self, ticket_id: int, open_message_id: int) -> None:
        async with await self.connect() as conn:
            cursor = conn.cursor()
            await cursor.execute(
                """
                UPDATE ticket SET is_open = false, open_message_id = %s
                WHERE id = %s
                """,
                (
                    open_message_id,
                    ticket_id,
                ),
            )

    async def delete_ticket(self, ticket_id: int) -> None:
        async with await self.connect() as conn:
            cursor = conn.cursor()
            await cursor.execute(
                """
                UPDATE ticket SET is_deleted = true
                WHERE id = %s
                """,
                (ticket_id,),
            )

    async def open_ticket(self, ticket_id: int) -> None:
        async with await self.connect() as conn:
            cursor = conn.cursor()
            await cursor.execute(
                """
                UPDATE ticket SET is_open = true
                WHERE id = %s
                """,
                (ticket_id,),
            )

    async def save_ticket_message(
        self,
        ticket_id: int,
        sender_id: int,
        sender_name: str,
        message: str,
        sent_at: datetime,
        attachment_urls,
    ) -> TicketMessage:
        async with await self.connect() as conn:
            cursor = conn.cursor()
            await cursor.execute(
                """
                INSERT INTO ticket_message (
                    ticket_id,
                    sender_id,
                    sender_name,
                    message,
                    sent_at
                ) VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (ticket_id, sender_id, sender_name, message, sent_at.isoformat()),
            )
            message_id = (await cursor.fetchone())[0]
            await cursor.executemany(
                """
                INSERT INTO ticket_message_attachment (ticket_message_id, attachment_url) VALUES (%s, %s)
                """,
                [(message_id, attachment_url) for attachment_url in attachment_urls],
            )
            return TicketMessage(
                message_id, sender_id, sender_name, message, sent_at, attachment_urls
            )
