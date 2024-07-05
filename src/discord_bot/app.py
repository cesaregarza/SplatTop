import logging
import os

import discord

from discord_bot.events.on_message import on_message as on_message_fn

logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.DEBUG)

handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
handler.setFormatter(formatter)
logger.addHandler(handler)

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)


@client.event
async def on_ready():
    logger.info(f"Logged in as {client.user}")


@client.event
async def on_message(message: discord.Message):
    await on_message_fn(client, message)


logger.info("Starting discord bot")


def run():
    client.run(os.getenv("DISCORD_BOT_TOKEN"))
