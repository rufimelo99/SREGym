#!/usr/bin/env python3
"""Standalone worker, run via `uv run --isolated --with inspect-ai --with
openai>=3.1.0` in an environment separate from this project's own venv
(which also has litellm, hard-capped to openai<3.0.0 -- incompatible with
inspect_ai's openai provider's openai>=3.1.0 requirement).

Deliberately has ZERO imports from this project (llm_backend/sregym/etc.)
since it runs completely isolated from it. Reads a JSON request from
stdin: {"model": str, "messages": [{"role": "system"|"user"|"assistant",
"content": str}, ...]}. Writes a JSON response to stdout:
{"completion": str} on success, {"error": str} (and exits 1) on failure.
"""

import asyncio
import json
import sys


def _build_messages(raw_messages):
    from inspect_ai.model import ChatMessageAssistant, ChatMessageSystem, ChatMessageUser

    role_to_cls = {
        "system": ChatMessageSystem,
        "user": ChatMessageUser,
        "assistant": ChatMessageAssistant,
    }
    return [role_to_cls[m["role"]](content=m["content"]) for m in raw_messages]


async def _generate(model_name, messages):
    from inspect_ai.model import get_model

    model = get_model(model_name)
    output = await model.generate(messages)
    return output.completion


def main() -> None:
    request = json.loads(sys.stdin.read())
    try:
        messages = _build_messages(request["messages"])
        completion = asyncio.run(_generate(request["model"], messages))
        json.dump({"completion": completion}, sys.stdout)
    except Exception as e:
        json.dump({"error": f"{type(e).__name__}: {e}"}, sys.stdout)
        sys.exit(1)


if __name__ == "__main__":
    main()
