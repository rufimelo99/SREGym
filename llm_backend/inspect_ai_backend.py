"""Drop-in replacement for LiteLLMBackend's public interface, resolving
models via inspect_ai.model.get_model() instead of LiteLLM.

Lets the judge use the exact same model-string convention and credential
env vars as an inspect_ai-based agent (e.g. azureai/<deployment> for Azure),
instead of LiteLLM's separate conventions and env vars.
"""

import asyncio
import concurrent.futures
from collections.abc import Awaitable, Callable

from inspect_ai.model import ChatMessageAssistant, ChatMessageSystem, ChatMessageUser, get_model


class _Response:
    def __init__(self, content: str):
        self.content = content


def _to_inspect_messages(messages, system_prompt):
    if isinstance(messages, str):
        result = []
        if system_prompt:
            result.append(ChatMessageSystem(content=system_prompt))
        result.append(ChatMessageUser(content=messages))
        return result

    result = []
    for message in messages:
        role = type(message).__name__
        if role == "SystemMessage":
            result.append(ChatMessageSystem(content=message.content))
        elif role == "HumanMessage":
            result.append(ChatMessageUser(content=message.content))
        elif role == "AIMessage":
            result.append(ChatMessageAssistant(content=message.content))
        else:
            raise TypeError(f"Unsupported message type: {type(message)}")
    return result


def _run_sync[T](coro_factory: Callable[[], Awaitable[T]]) -> T:
    """Run an async 0-arg callable to completion, whether called from a
    plain sync context or from within an already-running event loop.

    inference() is called from two very different places: SREGym's real
    judge grading happens inside a ThreadPoolExecutor thread (Conductor
    runs evaluation off its main event loop), where there's no running
    loop and asyncio.run() works directly. But this same method is also
    called from our own async preflight check, which runs *inside*
    inspect_ai's event loop -- asyncio.run() there raises "cannot be
    called from a running event loop". Detect which case we're in and,
    for the latter, run the coroutine on a fresh loop in a separate
    thread instead of trying to nest event loops.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro_factory())

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(lambda: asyncio.run(coro_factory())).result()


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

        chat_messages = _to_inspect_messages(messages, system_prompt)

        async def _generate():
            model = get_model(self.model_name)
            return await model.generate(chat_messages)

        output = _run_sync(_generate)
        return _Response(output.completion)
