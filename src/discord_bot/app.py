import logging
import os

import discord
from discord.ext import commands

from discord_bot.bot import SplatTopBot

logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.DEBUG)

handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
handler.setFormatter(formatter)
logger.addHandler(handler)

bot = SplatTopBot()

logger.info("Starting discord bot")


def run():
    bot.run(os.getenv("DISCORD_BOT_TOKEN"))
