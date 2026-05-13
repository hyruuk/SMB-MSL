#!/usr/bin/env bash
# setup.sh — provision the SMB-SSL environment and data:
#   1. `uv sync` to create .venv and install all project dependencies
#      (psychopy, stable-retro, numpy, datalad, tqdm).
#   2. `datalad install` + `datalad get` for the two CNeuroMod datasets:
#        - mario.stimuli  (NES ROM + retro integration metadata)
#        - mario.scenes   (per-session gameplay archives)
#   3. Unpack the per-session gamelogs.tar archives inside mario.scenes
#      using the decompress script shipped with that dataset.
#
# Usage:
#   ./setup.sh                  # interactive: prompts for the data root
#   ./setup.sh /path/to/root    # non-interactive: install into <root>
#
# Both datasets are installed as <root>/mario.stimuli and <root>/mario.scenes.
# The default <root> is the SMB-MSL repository directory.

set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
cd "$REPO_ROOT"

STIMULI_URL="git@github.com:courtois-neuromod/mario.stimuli"
SCENES_URL="git@github.com:courtois-neuromod/mario.scenes"

# --- uv check ---
if ! command -v uv >/dev/null 2>&1; then
    echo "ERROR: 'uv' not found in PATH." >&2
    echo "       Install it from https://docs.astral.sh/uv/getting-started/installation/" >&2
    echo "       or run:  curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
    exit 1
fi
command -v git >/dev/null 2>&1 || { echo "ERROR: 'git' not found." >&2; exit 1; }

# --- Resolve data root ---
if [[ $# -ge 1 ]]; then
    DATA_ROOT="$1"
else
    read -e -r -p "Data root for datalad datasets [${REPO_ROOT}]: " DATA_ROOT
    DATA_ROOT="${DATA_ROOT:-$REPO_ROOT}"
fi
mkdir -p "$DATA_ROOT"
DATA_ROOT="$(cd "$DATA_ROOT" && pwd)"
echo "Installing datasets into: $DATA_ROOT"

# --- Project environment (.venv) ---
echo "[uv sync] installing project dependencies into .venv"
uv sync

# --- Install + fetch one dataset ---
install_and_get() {
    local url="$1" dest="$2"
    if [[ -d "$dest/.git" ]]; then
        echo "[skip install] $dest already a dataset"
    else
        echo "[datalad install] $url -> $dest"
        uv run datalad install -s "$url" "$dest"
    fi
    echo "[datalad get] $dest"
    uv run datalad get -d "$dest" "$dest"
}

install_and_get "$STIMULI_URL" "$DATA_ROOT/mario.stimuli"
install_and_get "$SCENES_URL"  "$DATA_ROOT/mario.scenes"

# --- Unpack scene archives ---
SCENES_DIR="$DATA_ROOT/mario.scenes"
DECOMPRESS_SCRIPT="$SCENES_DIR/code/archives/decompress.py"

if [[ -f "$DECOMPRESS_SCRIPT" ]]; then
    echo "[unpack] $DECOMPRESS_SCRIPT -o $SCENES_DIR"
    uv run python "$DECOMPRESS_SCRIPT" -o "$SCENES_DIR"
else
    echo "WARNING: decompress script not found at $DECOMPRESS_SCRIPT — skipping unpack." >&2
fi

echo
echo "Done."
echo "  Scenes dataset dir    -> $DATA_ROOT/mario.scenes"
echo "  Retro integration dir -> $DATA_ROOT/mario.stimuli"
echo
echo "Run the task with:"
echo "  uv run smb-ssl-task           # entry point"
echo "  uv run python -m smb_ssl_task # equivalent"
