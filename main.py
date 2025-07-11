import discord
from logging import getLogger
from discord.ext import commands


intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


log = getLogger(__name__)


@bot.event
async def on_message(message):
    if message.channel.id == 1388913510569873418:
        try:
            await message.publish()
        except discord.Forbidden:
            log.exception("Missing permissions to publish message")
        except discord.HTTPException as e:
            log.exception("Failed to publish", exc_info=e)


if __name__ == "__main__":
    from dotenv import load_dotenv
    import os

    load_dotenv()

    bot.run(os.getenv("TOKEN"))
