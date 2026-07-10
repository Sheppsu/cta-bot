import discord
import os
import asyncio
from discord.ext import commands
from logging import getLogger

from dotenv import load_dotenv

load_dotenv(override=True)

from database import Database, GuildData


ANNOUNCEMENT_CHANNEL_ID = int(os.getenv("ANNOUNCEMENT_CHANNEL_ID"))
SERVER_ID = int(os.getenv("SERVER_ID"))
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
STAFF_ROLE_ID = int(os.getenv("STAFF_ROLE_ID"))
CONTACT_ID = int(os.getenv("CONTACT_ID"))
CATEGORY = int(os.getenv("CATEGORY"))

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

log = getLogger(__name__)
db = Database()
guild_data: GuildData


def ticket_creation_view_embed():
    return discord.Embed(
        title="Create a ticket",
        description="Use tickets to ask question directly with staff "
        "or verify solution steps for certain achievements.\n\n"
        "Use DM tickets for solution verification to avoid "
        "the possibility that someone else snipes your completion through certain Discord plugins.",
        color=discord.Color.yellow(),
    )


def ticket_embed(ticket_id, creator_id):
    return discord.Embed(
        title=f"Ticket #{ticket_id}",
        color=discord.Color.blue(),
        description=f"Created by <@{creator_id}>",
    )


def dm_ticket_embed():
    return discord.Embed(
        title="You have opened a ticket",
        description="Messages sent to me will be sent to staff and vice-versa.",
        color=discord.Color.blue(),
    )


def closed_ticket_embed():
    return discord.Embed(
        title="This ticket has been closed",
        color=discord.Color.red(),
    )


def forwarded_message_embed(message: discord.Message):
    embed = discord.Embed(
        description=message.content or None,
        color=discord.Color.blue(),
    )
    embed.set_author(
        name=message.author.display_name, icon_url=message.author.display_avatar.url
    )
    return embed


async def delayed_delete(channel: discord.TextChannel, delay: int):
    await asyncio.sleep(delay)
    await channel.delete()


class FinalTicketView(discord.ui.View):
    def __init__(self, ticket_id: int):
        super().__init__(timeout=None)

        self.ticket_id = ticket_id
        self.lock = asyncio.Lock()

    @discord.ui.button(label="Reopen", style=discord.ButtonStyle.primary, emoji="🔓")
    async def reopen(self, interaction: discord.Interaction, button: discord.ui.Button):
        async with self.lock:
            ticket = await db.get_ticket(self.ticket_id)
            if ticket.is_open:
                await interaction.response.send_message(
                    "Ticket already open", ephemeral=True
                )
                return
            if ticket.is_deleted:
                await interaction.response.send_message(
                    "Ticket has been marked for deletion", ephemeral=True
                )
                return

            ticket_channel = bot.get_channel(ticket.channel_id) or (
                await bot.fetch_channel(ticket.channel_id)
            )
            if ticket.open_message_id:
                open_msg = await ticket_channel.fetch_message(ticket.open_message_id)
                await open_msg.delete()
            await ticket_channel.send("Ticket has been reopened")
            await db.open_ticket(self.ticket_id)
            await interaction.response.send_message(
                "Ticket has been reopened", ephemeral=True
            )

        log.info(f"Reopened ticket {ticket.id}")

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.primary, emoji="❌")
    async def delete_ticket(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        async with self.lock:
            ticket = await db.get_ticket(self.ticket_id)
            if ticket.is_deleted:
                await interaction.response.send_message(
                    "Ticket is already marked for deletion", ephemeral=True
                )
                return
            if ticket.is_open:
                await interaction.response.send_message(
                    "Ticket is still open", ephemeral=True
                )
                return

            ticket_channel = bot.get_channel(ticket.channel_id) or (
                await bot.fetch_channel(ticket.channel_id)
            )
            await ticket_channel.send("This channel will be deleted in 5 seconds")
            _ = bot.loop.create_task(delayed_delete(ticket_channel, 5))
            await db.delete_ticket(ticket.id)
            await interaction.response.send_message(
                "Ticket will be deleted", ephemeral=True
            )

        log.info(f"Deleted ticket {ticket.id}")


class CloseTicketView(discord.ui.View):
    def __init__(self, ticket_id: int):
        super().__init__(timeout=None)

        self.ticket_id: int = ticket_id
        self.lock = asyncio.Lock()

    @discord.ui.button(label="Close", style=discord.ButtonStyle.primary, emoji="🔒")
    async def close_ticket(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        async with self.lock:
            ticket = await db.get_ticket(self.ticket_id)
            if not ticket.is_open:
                await interaction.response.send_message(
                    "Ticket is already closed", ephemeral=True
                )
                return
            if ticket.is_deleted:
                await interaction.response.send_message(
                    "Ticket is marked for deletion", ephemeral=True
                )
                return

            ticket_channel = bot.get_channel(ticket.channel_id) or (
                await bot.fetch_channel(ticket.channel_id)
            )
            open_msg = await ticket_channel.send(
                embed=closed_ticket_embed(), view=FinalTicketView(ticket.id)
            )
            await db.close_ticket(ticket.id, open_msg.id)
            await interaction.response.send_message(
                "Ticket has been closed", ephemeral=True
            )

        log.info(f"Closed ticket {ticket.id}")


class CreateTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

        self.lock = asyncio.Lock()

    async def open_ticket(
        self, interaction: discord.Interaction, button: discord.ui.Button, is_dm: bool
    ):
        async with self.lock:
            open_tickets = await db.get_creator_tickets(interaction.user.id, True)
            if len(open_tickets) > 0:
                await interaction.response.send_message(
                    "You cannot open more than one ticket at a time.",
                    ephemeral=True,
                )
                return

            guild = interaction.guild
            staff_role = guild.get_role(STAFF_ROLE_ID)
            category = guild.get_channel(CATEGORY)
            if staff_role is None:
                await interaction.response.send_message(
                    f"Failed to create ticket. Contact <@{CONTACT_ID}>", ephemeral=True
                )
                return

            ticket = await db.create_ticket(interaction.user.id, is_dm)

        see_perms = discord.PermissionOverwrite(
            view_channel=True, send_messages=True, read_message_history=True
        )
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            staff_role: see_perms,
            guild.me: see_perms,
        }
        if not is_dm:
            overwrites[interaction.user] = see_perms
        channel = await guild.create_text_channel(
            name=f"ticket-{ticket.id}",
            overwrites=overwrites,
            category=category,
        )

        channel_msg = await channel.send(
            embed=ticket_embed(ticket.id, interaction.user.id),
            view=CloseTicketView(ticket.id),
        )
        await db.update_open_ticket_data(ticket.id, channel.id, channel_msg.id)
        if is_dm:
            try:
                await interaction.user.send(embed=dm_ticket_embed())
                await interaction.response.send_message(
                    "Ticket was created. Communication will take place in DMs with CTA Bot.",
                    ephemeral=True,
                )
            except discord.Forbidden:
                overwrites[interaction.user] = see_perms
                await channel.edit(overwrites=overwrites)
                await db.update_ticket_type(ticket.id, False)
                await interaction.response.send_message(
                    f"I was unable to DM you, so the ticket was changed into a channel ticket: {channel.mention}. "
                    "Enable DMs from server members to use DM tickets.",
                    ephemeral=True,
                )
        else:
            await interaction.response.send_message(
                f"Ticket was created: {channel.mention}", ephemeral=True
            )

        log.info(f"Created ticket {ticket.id}")

    @discord.ui.button(label="DM ticket", style=discord.ButtonStyle.primary, emoji="🎫")
    async def create_dm_ticket(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        log.info(
            f"Creating DM ticket for {interaction.user.name} (ID: {interaction.user.id})"
        )
        await self.open_ticket(interaction, button, True)

    @discord.ui.button(
        label="Channel ticket", style=discord.ButtonStyle.primary, emoji="🎫"
    )
    async def create_channel_ticket(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        log.info(
            f"Creating channel ticket for {interaction.user.name} (ID: {interaction.user.id})"
        )
        await self.open_ticket(interaction, button, False)


async def get_view_message(message_id: int):
    channel = bot.get_channel(CHANNEL_ID) or (await bot.fetch_channel(CHANNEL_ID))
    msg = await channel.fetch_message(message_id)
    await msg.edit(embed=ticket_creation_view_embed(), view=CreateTicketView())
    return msg


async def create_view_message():
    channel = bot.get_channel(CHANNEL_ID) or (await bot.fetch_channel(CHANNEL_ID))
    msg = await channel.send(
        embed=ticket_creation_view_embed(), view=CreateTicketView()
    )
    return msg


@bot.event
async def on_ready():
    global guild_data

    log.info("Bot is online")

    guild_data = await db.get_guild_data(SERVER_ID)
    if guild_data is None:
        log.info("Creating new view")
        msg = await create_view_message()
        guild_data = await db.set_guild_data(SERVER_ID, msg.id)
    else:
        log.info("Found existing view")
        await get_view_message(guild_data.message_id)

    log.info("Processing existing tickets")
    for ticket in await db.get_all_tickest(False):
        channel = bot.get_channel(ticket.channel_id) or (
            await bot.fetch_channel(ticket.channel_id)
        )
        close_msg = await channel.fetch_message(ticket.close_message_id)
        await close_msg.edit(
            embed=ticket_embed(ticket.id, ticket.creator_id),
            view=CloseTicketView(ticket.id),
        )
        if not ticket.is_open and ticket.open_message_id:
            open_msg = await channel.fetch_message(ticket.open_message_id)
            await open_msg.edit(
                embed=closed_ticket_embed(), view=FinalTicketView(ticket.id)
            )

    log.info("Ready!")


async def forward_message_to(ticket_id: int, sendable, message: discord.Message):
    await sendable.send(embed=forwarded_message_embed(message))
    attachment_urls = [attachment.url for attachment in message.attachments]
    for attachment_url in attachment_urls:
        await sendable.send(attachment_url)

    await db.save_ticket_message(
        ticket_id,
        message.author.id,
        message.author.name,
        message.content,
        message.created_at,
        attachment_urls,
    )


@bot.event
async def on_message(message: discord.Message):
    if message.channel.id == ANNOUNCEMENT_CHANNEL_ID:
        try:
            await message.publish()
            log.info("Published message")
        except discord.Forbidden:
            log.exception("Missing permissions to publish message")
        except discord.HTTPException as e:
            log.exception("Failed to publish", exc_info=e)

    if message.author.bot:
        return

    if isinstance(message.channel, discord.DMChannel):
        tickets = await db.get_creator_tickets(message.author.id, True)
        if len(tickets) == 0:
            return

        ticket = tickets[0]
        ticket_channel = bot.get_channel(ticket.channel_id) or (
            await bot.fetch_channel(ticket.channel_id)
        )
        await forward_message_to(ticket.id, ticket_channel, message)

        return

    if message.channel.name.startswith("ticket"):
        ticket = await db.get_ticket_by_channel(message.channel.id)
        if (
            ticket is None
            or not ticket.is_open
            or ticket.is_deleted
            or not ticket.is_dm
        ):
            return

        user = bot.get_user(ticket.creator_id) or (
            await bot.fetch_user(ticket.creator_id)
        )
        if user:
            try:
                await forward_message_to(ticket.id, user, message)
            except discord.Forbidden:
                await message.channel.send(
                    "Failed to forward message - user's DMs are closed"
                )


if __name__ == "__main__":
    from dotenv import load_dotenv
    import os
    import sys

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    load_dotenv()

    bot.run(os.getenv("TOKEN"))
