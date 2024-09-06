import logging

import discord
import orjson
from discord.ext import commands

from discord_bot.clients import anthropic_client
from discord_bot.prompts import agent_prompts
from discord_bot.tools import TOOL_FUNCTIONS, TOOLS
from discord_bot.utils import extract_from_message, locked_check

logger = logging.getLogger(__name__)


class AgentCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ask")
    @locked_check("anthropic")
    async def discord_agent(self, ctx: commands.Context, *, message: str):
        logger.info("Running agent")
        async with ctx.typing():
            running_messages = [
                {"role": "user", "content": message},
            ]
            response = anthropic_client.messages.create(
                system=agent_prompts.SYSTEM_PROMPT,
                max_tokens=1024,
                messages=running_messages,
                model="claude-3-5-sonnet-20240620",
                tools=TOOLS,
            )
            logger.debug(response)
            while response.stop_reason == "tool_use":
                tool_to_use = next(
                    block
                    for block in response.content
                    if block.type == "tool_use"
                )
                logger.info("Using tool %s", tool_to_use.name)
                tool = TOOL_FUNCTIONS[tool_to_use.name]
                tool_inputs = tool_to_use.input
                tool_response = tool(**tool_inputs)
                running_messages.extend(
                    [
                        {
                            "role": "assistant",
                            "content": response.content[0].text,
                        },
                        {
                            "role": "user",
                            "content": (
                                "We got the following response from the tool:\n"
                                "<TOOL_RESPONSE>\n"
                                f"{orjson.dumps(tool_response).decode()}"
                                "\n</TOOL_RESPONSE>"
                            ),
                        },
                    ]
                )
                response = anthropic_client.messages.create(
                    system=agent_prompts.SYSTEM_PROMPT,
                    max_tokens=1024,
                    messages=running_messages,
                    model="claude-3-5-sonnet-20240620",
                    tools=TOOLS,
                )

            return_value = extract_from_message(
                response.content[0].text, "ANSWER"
            )
        await ctx.send(return_value)


async def setup(bot: commands.Bot):
    await bot.add_cog(AgentCog(bot))
