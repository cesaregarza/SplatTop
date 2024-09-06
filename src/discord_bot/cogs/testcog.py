import logging

import discord
from discord.ext import commands

from discord_bot.clients import anthropic_client
from discord_bot.utils import locked_check

logger = logging.getLogger(__name__)


class TestCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="test")
    @locked_check("anthropic")
    async def testfxn(self, ctx: commands.Context, *, message: str):
        logger.info("Running test function")
        async with ctx.typing():
            out_message = anthropic_client.messages.create(
                system=(
                    "You are an AI powered by Claude designed to answer queries"
                    " using a website called SplatTop. You can answer questions"
                    "related to Splatoon 3 according to what's on the website."
                ),
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": message},
                ],
                model="claude-3-5-sonnet-20240620",
            )
            logger.debug(out_message)
        await ctx.send(out_message.content[0].text)


async def setup(bot: commands.Bot):
    await bot.add_cog(TestCog(bot))
