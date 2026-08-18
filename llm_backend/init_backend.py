import os

from llm_backend.get_llm_backend import LiteLLMBackend


def get_llm_backend(
    model_name: str,
    api_base: str | None = None,
    api_key: str | None = None,
) -> LiteLLMBackend:
    """Initialize an LLM backend for the given litellm model string."""
    endpoint_status = "set" if api_base else "unset"
    print(f"🔧 Initializing LLM backend — model: {model_name}, api_base: {endpoint_status}")
    return LiteLLMBackend(model_name=model_name, api_base=api_base, api_key=api_key)


def get_llm_backend_for_agent() -> LiteLLMBackend:
    """Get LLM backend for agent tasks"""
    model_id = os.environ.get("AGENT_MODEL_ID")
    if not model_id:
        raise ValueError("AGENT_MODEL_ID environment variable is not set.")
    return get_llm_backend(
        model_id,
        api_base=os.environ.get("AGENT_API_BASE"),
        api_key=os.environ.get("AGENT_API_KEY"),
    )


def get_llm_backend_for_judge():
    """Get LLM backend for the LLM-as-a-judge evaluator.

    Set JUDGE_BACKEND=inspect_ai to resolve the judge model through
    inspect_ai.model.get_model() instead of LiteLLM -- lets the judge use
    the same model-string convention and credentials as an inspect_ai-based
    agent. Default (unset) is unchanged LiteLLM behavior.
    """
    model_id = os.environ.get("JUDGE_MODEL_ID")
    if not model_id:
        raise ValueError("JUDGE_MODEL_ID environment variable is not set.")

    if os.environ.get("JUDGE_BACKEND") == "inspect_ai":
        from llm_backend.inspect_ai_backend import InspectAIBackend

        print(f"🔧 Initializing inspect_ai LLM backend for judge — model: {model_id}")
        return InspectAIBackend(model_name=model_id)

    return get_llm_backend(
        model_id,
        api_base=os.environ.get("JUDGE_API_BASE"),
        api_key=os.environ.get("JUDGE_API_KEY"),
    )
