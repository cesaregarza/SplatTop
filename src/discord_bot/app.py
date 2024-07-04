import logging
import os

import discord

logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.DEBUG)

# Add a handler to stdout
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
    if message.author == client.user:
        return

    if message.content.startswith("!hello"):
        await message.channel.send("Hello! I'm alive!!")


logger.info("Starting discord bot")
logger.debug(
    f"Token: {os.getenv('DISCORD_BOT_TOKEN')}"
)  # Not accessible to anyone anyway

client.run(os.getenv("DISCORD_BOT_TOKEN"))
