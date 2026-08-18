"""Drop-in replacement for LiteLLMBackend's public interface, resolving
models via inspect_ai.model.get_model() -- but in a separate, ISOLATED
environment (via `uv run --isolated --with`), not this process's own venv.

Why isolation: inspect_ai's "openai" provider requires openai>=3.1.0, but
this project also depends on litellm, which hard-caps openai<3.0.0 in every
released version -- the two genuinely cannot share one Python environment.
Running the actual model call in an ephemeral, isolated environment
sidesteps the conflict entirely: openai/azure/<deployment> model strings
work exactly as inspect_ai documents them, with no need for a different
provider convention (e.g. azureai/<deployment>) just to dodge this clash.
"""

import json
import os
import subprocess
from pathlib import Path

_WORKER_SCRIPT = Path(__file__).parent / "_inspect_ai_judge_worker.py"
_INSPECT_AI_SOURCE = "inspect-ai @ git+https://github.com/rufimelo99/inspect_ai.git"
_WORKER_TIMEOUT_SECONDS = 120


class _Response:
    def __init__(self, content: str):
        self.content = content


def _message_role(message) -> str:
    cls_name = type(message).__name__
    if cls_name == "SystemMessage":
        return "system"
    if cls_name == "HumanMessage":
        return "user"
    if cls_name == "AIMessage":
        return "assistant"
    raise TypeError(f"Unsupported message type: {type(message)}")


def _to_plain_messages(messages, system_prompt):
    if isinstance(messages, str):
        result = []
        if system_prompt:
            result.append({"role": "system", "content": system_prompt})
        result.append({"role": "user", "content": messages})
        return result

    return [{"role": _message_role(m), "content": m.content} for m in messages]


def _call_isolated_worker(model_name: str, plain_messages: list[dict]) -> str:
    payload = json.dumps({"model": model_name, "messages": plain_messages})

    result = subprocess.run(
        [
            "uv",
            "run",
            "--isolated",
            "--with",
            _INSPECT_AI_SOURCE,
            "--with",
            "openai>=3.1.0",
            "python",
            str(_WORKER_SCRIPT),
        ],
        input=payload,
        capture_output=True,
        text=True,
        env=os.environ.copy(),
        timeout=_WORKER_TIMEOUT_SECONDS,
    )

    if not result.stdout.strip():
        raise RuntimeError(f"Isolated inspect_ai worker produced no output (stderr: {result.stderr.strip()})")

    response = json.loads(result.stdout)
    if "error" in response:
        raise RuntimeError(response["error"])
    return response["completion"]


class InspectAIBackend:
    def __init__(
        self,
        model_name: str,
        api_key: str | None = None,
        api_base: str | None = None,
        top_p: float = 0.95,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ):
        # api_key/api_base/top_p/max_tokens accepted for interface parity
        # with LiteLLMBackend; inspect_ai resolves its own provider-specific
        # credentials from env vars instead of taking them here.
        self.model_name = model_name
        self.temperature = temperature

    def inference(self, messages, system_prompt: str | None = None, tools=None):
        if tools:
            raise NotImplementedError("InspectAIBackend does not support tool-calling (unused by the judge).")

        plain_messages = _to_plain_messages(messages, system_prompt)
        completion = _call_isolated_worker(self.model_name, plain_messages)
        return _Response(completion)
