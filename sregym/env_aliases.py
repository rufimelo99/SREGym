import os

# LiteLLM (used by SREGym's agent/judge preflight) and inspect_ai (used by
# inspect_ai-based agents) read different env var names for the same Azure
# OpenAI deployment. Users who only set the inspect_ai-style vars would
# otherwise see the judge silently fail to find credentials.
_AZURE_API_KEY_ALIASES = ("AZUREAI_OPENAI_API_KEY", "AZURE_OPENAI_API_KEY")
_AZURE_API_BASE_ALIASES = ("AZUREAI_OPENAI_BASE_URL", "AZURE_OPENAI_BASE_URL", "AZURE_OPENAI_ENDPOINT")


def _mirror(target: str, sources: tuple[str, ...]) -> None:
    if os.environ.get(target):
        return
    for source in sources:
        value = os.environ.get(source)
        if value:
            os.environ[target] = value
            return


def mirror_azure_openai_env_aliases() -> None:
    """Mirror inspect_ai-style Azure OpenAI env vars into LiteLLM's names.

    Only fills in AZURE_API_KEY / AZURE_API_BASE when they aren't already
    set; never overrides an explicitly configured LiteLLM var.
    """
    _mirror("AZURE_API_KEY", _AZURE_API_KEY_ALIASES)
    _mirror("AZURE_API_BASE", _AZURE_API_BASE_ALIASES)
