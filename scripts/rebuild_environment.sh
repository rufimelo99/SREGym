#!/usr/bin/env bash
# Rebuilds SREGym's local dev environment -- the agent Docker image and the
# kind cluster -- only when necessary. Safe to run repeatedly; a no-op fast
# path when everything's already current.
#
# "Necessary" means:
#   - the sregym-agent-base image is missing, OR any file under a watched
#     source path (clients/, logger/, llm_backend/, docker/agents/, the
#     handful of sregym/ files build.sh actually copies in) is newer than
#     the image itself
#   - no kind cluster named "kind" exists
#
# This script does NOT delete or restart live pods -- reconciling cluster
# state for an in-progress run is SREGym's own Conductor.fix_kubernetes()
# job, not this script's. It only reports pods that aren't Running/Ready so
# you can decide what (if anything) to do about them.
#
# Usage:
#   bash scripts/rebuild_environment.sh            # rebuild only what's stale/missing
#   bash scripts/rebuild_environment.sh --force     # always rebuild the image + recreate the cluster

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
FORCE=false
[[ "${1:-}" == "--force" ]] && FORCE=true

IMAGE_NAME="sregym-agent-base:latest"
CLUSTER_NAME="kind"

# Mirrors exactly what docker/agents/build.sh copies into the build context.
WATCHED_PATHS=(
    "$REPO_ROOT/clients"
    "$REPO_ROOT/logger"
    "$REPO_ROOT/llm_backend"
    "$REPO_ROOT/sregym/paths.py"
    "$REPO_ROOT/sregym/service/kubectl.py"
    "$REPO_ROOT/sregym/service/helm.py"
    "$REPO_ROOT/sregym/service/apps/base.py"
    "$REPO_ROOT/sregym/service/apps/helpers.py"
    "$REPO_ROOT/docker/agents"
)

if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker is not running (or not reachable). Start Docker Desktop and retry."
    exit 1
fi

# ─────────────────────────────────────────────
# 1. Agent Docker image
# ─────────────────────────────────────────────
echo "==> Checking agent Docker image ($IMAGE_NAME)..."

needs_image_rebuild=false
if [[ "$FORCE" == true ]]; then
    needs_image_rebuild=true
elif ! docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; then
    echo "    Image not found."
    needs_image_rebuild=true
elif ! python3 - "$IMAGE_NAME" "${WATCHED_PATHS[@]}" <<'PYEOF'
import datetime
import os
import subprocess
import sys

image, paths = sys.argv[1], sys.argv[2:]

result = subprocess.run(
    ["docker", "image", "inspect", image, "--format", "{{.Created}}"],
    capture_output=True, text=True,
)
if result.returncode != 0:
    sys.exit(1)  # missing -- treat as stale

created = datetime.datetime.strptime(result.stdout.strip().split(".")[0], "%Y-%m-%dT%H:%M:%S")

newest_mtime = 0.0
for path in paths:
    if os.path.isfile(path):
        newest_mtime = max(newest_mtime, os.path.getmtime(path))
    elif os.path.isdir(path):
        # followlinks=True: clients/inspectai is a symlink (into a sibling
        # repo); os.walk skips symlinked dirs by default and would silently
        # never detect changes there otherwise.
        for root, _, files in os.walk(path, followlinks=True):
            for name in files:
                try:
                    newest_mtime = max(newest_mtime, os.path.getmtime(os.path.join(root, name)))
                except OSError:
                    pass

newest = datetime.datetime.fromtimestamp(newest_mtime, tz=datetime.timezone.utc).replace(tzinfo=None)
sys.exit(1 if newest > created else 0)
PYEOF
then
    echo "    Source is newer than the image."
    needs_image_rebuild=true
fi

if [[ "$needs_image_rebuild" == true ]]; then
    echo "==> Rebuilding agent Docker image..."
    bash "$SCRIPT_DIR/../docker/agents/build.sh"
else
    echo "    Image is up to date; skipping rebuild."
fi

# ─────────────────────────────────────────────
# 2. kind cluster
# ─────────────────────────────────────────────
echo "==> Checking kind cluster ($CLUSTER_NAME)..."

cluster_exists=$(kind get clusters 2>/dev/null | grep -Fx "$CLUSTER_NAME" || true)

if [[ "$FORCE" == true && -n "$cluster_exists" ]]; then
    echo "    --force: deleting existing cluster before recreating..."
    kind delete cluster --name "$CLUSTER_NAME"
    cluster_exists=""
fi

if [[ -z "$cluster_exists" ]]; then
    echo "    No cluster found; creating one..."
    if [[ "$(uname)" == "Darwin" ]]; then
        arch="$([[ "$(sysctl -n hw.optional.arm64 2>/dev/null)" == "1" ]] && echo arm || echo x86)"
    else
        arch="$([[ "$(uname -m)" == "aarch64" || "$(uname -m)" == "arm64" ]] && echo arm || echo x86)"
    fi
    bash "$SCRIPT_DIR/../kind/setup_kind_cluster.sh" "$arch"
else
    echo "    Cluster already exists."
    kubectl config use-context "kind-$CLUSTER_NAME" >/dev/null
fi

# ─────────────────────────────────────────────
# 3. Pod health report (informational only -- nothing is deleted/restarted)
# ─────────────────────────────────────────────
echo "==> Checking pod health..."

unhealthy=$(kubectl get pods -A --no-headers 2>/dev/null | awk '
    { split($3, ready, "/");
      if ($4 != "Running" && $4 != "Completed") print;
      else if (ready[1] != ready[2]) print;
    }
')

if [[ -n "$unhealthy" ]]; then
    echo "⚠️  Pods not Running/Ready:"
    echo "$unhealthy"
    echo "    Not touching these automatically -- SREGym's own fault-recovery/"
    echo "    reconciliation (run via main.py/the conductor) is what should fix"
    echo "    them if a run is in progress. Investigate with:"
    echo "      kubectl -n <namespace> describe pod <name>"
else
    echo "    All pods Running/Ready."
fi

echo "==> Done."
