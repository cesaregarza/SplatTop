import logging

import discord
from discord.ext import commands

from discord_bot.constants import EXTENSIONS

logger = logging.getLogger(__name__)


class SplatTopBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(
            command_prefix=commands.when_mentioned_or("!"), intents=intents
        )

    async def setup_hook(self):
        logger.info(f"Logging in as {self.user}...")
        for ext in EXTENSIONS:
            await self.load_extension(ext)

    async def on_ready(self):
        logger.info(f"Logged in as {self.user}")

    async def on_message(self, message: discord.Message):
        if message.author == self.user:
            return

        logger.info("Received message: %s", message.content)

        await self.process_commands(message)

    async def on_command_error(
        self, context: commands.Context, exception: Exception
    ):
        match exception:
            case commands.CommandNotFound():
                logger.error(f"Error: {exception}")
            case commands.CheckFailure():
                logger.error(f"Check failed: {exception}")
            case commands.CommandInvokeError():
                logger.error(f"Error invoking command: {exception}")
            case _:
                logger.error(f"Unexpected error: {exception}")
