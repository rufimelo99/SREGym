#!/usr/bin/env bash
set -euo pipefail
echo "[$(date -Iseconds)] Installing inspect_ai..."
python3 -m pip install --break-system-packages "git+https://github.com/rufimelo99/inspect_ai.git"
python3 -c "import inspect_ai" && echo "[$(date -Iseconds)] inspect_ai installed: $(python3 -c 'import inspect_ai; print(inspect_ai.__version__)')"

# Needed for the "azureai" model provider (inspect_ai.model), used for
# Azure-hosted models -- inspect_ai's "openai" provider requires
# openai>=3.1.0, which conflicts with litellm's openai<3.0.0 cap (litellm
# is also installed in this image), so Azure models must go through
# azureai/<deployment> instead of openai/azure/<deployment>.
echo "[$(date -Iseconds)] Installing azure-ai-inference..."
python3 -m pip install --break-system-packages "azure-ai-inference"
