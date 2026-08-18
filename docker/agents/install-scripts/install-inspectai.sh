#!/usr/bin/env bash
set -euo pipefail
echo "[$(date -Iseconds)] Installing inspect_ai..."
python3 -m pip install --break-system-packages "git+https://github.com/rufimelo99/inspect_ai.git"
python3 -c "import inspect_ai" && echo "[$(date -Iseconds)] inspect_ai installed: $(python3 -c 'import inspect_ai; print(inspect_ai.__version__)')"
