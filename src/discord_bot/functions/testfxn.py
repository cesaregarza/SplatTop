import logging

import discord

from discord_bot.clients import anthropic_client
from discord_bot.utils import locked_function

logger = logging.getLogger(__name__)


@locked_function("anthropic")
async def testfxn(client: discord.Client, message: discord.Message):
    logger.info("Running test function")
    out_message = anthropic_client.messages.create(
        system=(
            "You are an AI powered by Claude designed to answer queries"
            " using a website called SplatTop. You can answer questions"
            "related to Splatoon 3 according to what's on the website."
        ),
        max_tokens=1024,
        messages=[
            {"role": "user", "content": message.content},
        ],
        model="claude-3-5-sonnet-20240620",
    )
    logger.debug(out_message)
    await message.channel.send(out_message.content[0].text)
