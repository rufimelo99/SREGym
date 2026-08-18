"""Drop-in replacement for LiteLLMBackend's public interface, resolving
models via inspect_ai.model.get_model() instead of LiteLLM.

Lets the judge use the exact same model-string convention and credential
env vars as an inspect_ai-based agent (e.g. openai/azure/<deployment>),
instead of LiteLLM's separate azure/<deployment> convention and
AZURE_API_KEY/AZURE_API_BASE env vars.
"""

import asyncio

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

        output = asyncio.run(_generate())
        return _Response(output.completion)
