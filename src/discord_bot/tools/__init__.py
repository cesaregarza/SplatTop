from discord_bot.tools.splattop_api import WEAPON_XREF_DEFINITION

DEFINITIONS = [
    WEAPON_XREF_DEFINITION,
]

TOOLS = [
    {k: v for k, v in entry.items() if k != "function"} for entry in DEFINITIONS
]

TOOL_FUNCTIONS = {entry["name"]: entry["function"] for entry in DEFINITIONS}
