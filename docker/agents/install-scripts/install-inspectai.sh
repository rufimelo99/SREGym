#!/usr/bin/env bash
set -euo pipefail

# inspect_ai's own "openai" provider (openai/azure/<deployment>) requires
# openai>=3.1.0, but this image's global site-packages also has litellm
# (needed by other agents, e.g. stratus), which hard-caps openai<3.0.0 in
# every release -- the two cannot coexist in one environment. Rather than
# routing around this via the "azureai" provider (a different SDK,
# azure-ai-inference, that turned out to have its own request-serialization
# bugs with newer "reasoning" models' max_completion_tokens param), give the
# inspectai agent its own fully isolated venv with openai>=3.1.0, mirroring
# how llm_backend/inspect_ai_backend.py isolates the judge's model call --
# just for this driver's whole process instead of a single completion.
VENV_DIR="/opt/inspectai-venv"

echo "[$(date -Iseconds)] Creating isolated venv for inspectai agent at $VENV_DIR..."
python3 -m venv "$VENV_DIR"

echo "[$(date -Iseconds)] Installing inspect_ai + deps into isolated venv..."
"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet \
    "git+https://github.com/rufimelo99/inspect_ai.git" \
    "openai>=3.1.0" \
    "mcp[cli]==1.27.2" \
    "httpx>=0.28.1" \
    "requests>=2.32.3" \
    "pyyaml==6.0.2" \
    "python-dotenv==1.1.0" \
    "rich==13.9.4" \
    "pydantic>=2.13.0"

"$VENV_DIR/bin/python" -c "import inspect_ai, openai; print(f'inspect_ai={inspect_ai.__version__} openai={openai.__version__}')"
