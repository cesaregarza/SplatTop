from discord_bot.functions.agent import discord_agent
from discord_bot.functions.testfxn import testfxn

function_router = {"test": testfxn, "ask": discord_agent}
