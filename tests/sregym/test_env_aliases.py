import os

from sregym.env_aliases import mirror_azure_openai_env_aliases


def _clear_azure_env(monkeypatch):
    for name in (
        "AZURE_API_KEY",
        "AZURE_API_BASE",
        "AZUREAI_OPENAI_API_KEY",
        "AZUREAI_OPENAI_BASE_URL",
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_BASE_URL",
        "AZURE_OPENAI_ENDPOINT",
    ):
        monkeypatch.delenv(name, raising=False)


def test_mirrors_inspect_ai_vars_into_litellm_vars_when_litellm_vars_unset(monkeypatch):
    _clear_azure_env(monkeypatch)
    monkeypatch.setenv("AZUREAI_OPENAI_API_KEY", "inspect-key")
    monkeypatch.setenv("AZUREAI_OPENAI_BASE_URL", "https://example.openai.azure.com")

    mirror_azure_openai_env_aliases()

    assert os.environ["AZURE_API_KEY"] == "inspect-key"
    assert os.environ["AZURE_API_BASE"] == "https://example.openai.azure.com"


def test_does_not_override_an_explicitly_set_litellm_var(monkeypatch):
    _clear_azure_env(monkeypatch)
    monkeypatch.setenv("AZURE_API_KEY", "explicit-key")
    monkeypatch.setenv("AZUREAI_OPENAI_API_KEY", "inspect-key")

    mirror_azure_openai_env_aliases()

    assert os.environ["AZURE_API_KEY"] == "explicit-key"


def test_no_op_when_neither_var_style_is_set(monkeypatch):
    _clear_azure_env(monkeypatch)

    mirror_azure_openai_env_aliases()

    assert "AZURE_API_KEY" not in os.environ
    assert "AZURE_API_BASE" not in os.environ
