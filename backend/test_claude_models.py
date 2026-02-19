"""Test different Claude model names to find what works with the API key."""
import os
import sys
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()

import anthropic
client = anthropic.Anthropic()

models_to_try = [
    "claude-3-haiku-20240307",
    "claude-3-sonnet-20240229",
    "claude-3-opus-20240229",
    "claude-3-5-haiku-20241022",
    "claude-3-5-sonnet-20241022",
    "claude-3-5-sonnet-latest",
]

for model in models_to_try:
    try:
        msg = client.messages.create(
            model=model,
            max_tokens=10,
            messages=[{"role": "user", "content": "Say OK"}],
        )
        print(f"  OK  {model}: {msg.content[0].text}")
    except Exception as e:
        err = str(e)[:120]
        print(f"  FAIL {model}: {type(e).__name__}: {err}")
