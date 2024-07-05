import logging

import discord

from discord_bot.function_router import function_router

logger = logging.getLogger(__name__)


async def on_message(client: discord.Client, message: discord.Message):
    if message.author == client.user:
        return

    logger.info(f"Received message: %s", message.content)

    await route_message(client, message)


async def route_message(client: discord.Client, message: discord.Message):
    message_str = message.content.lower()
    if not message_str.startswith("!"):
        logger.info("Message does not start with !, not a command")
        return

    command = message_str.split(" ")[0][1:]
    if command not in function_router:
        logger.info("Command %s not found in function_router keys", command)
        return

    logger.info("Routing command %s", command)
    await function_router[command](client, message)
