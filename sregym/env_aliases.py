import os

# LiteLLM, inspect_ai's "openai" provider (Azure-via-OpenAI), and inspect_ai's
# "azureai" provider each read DIFFERENT env var names for the same Azure
# deployment. Users who only set one style would otherwise see the others
# silently fail to find credentials.
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
    """Mirror inspect_ai-style Azure OpenAI env vars into LiteLLM's and
    inspect_ai's "azureai" provider's names.

    Only fills in a target var when it isn't already set; never overrides an
    explicitly configured one.
    """
    _mirror("AZURE_API_KEY", _AZURE_API_KEY_ALIASES)
    _mirror("AZURE_API_BASE", _AZURE_API_BASE_ALIASES)
    _mirror("AZUREAI_API_KEY", _AZURE_API_KEY_ALIASES)
    _mirror("AZUREAI_BASE_URL", _AZURE_API_BASE_ALIASES)
