import os

import anthropic

anthropic_client = anthropic.Anthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY"),
)
