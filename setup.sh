#!/usr/bin/env bash
# setup.sh — provision the SMB-SSL environment and data:
#   1. detect the Linux distro and pick the matching wxPython wheel index
#      at https://extras.wxpython.org/wxPython4/extras/linux/gtk3/
#      (PyPI has no Linux wxPython wheels — building from sdist needs
#      GTK dev headers, which we want to avoid).
#   2. `uv sync` to create .venv and install all project dependencies
#      (psychopy, stable-retro, numpy, scipy, wxpython, datalad, tqdm).
#   3. `datalad install` + `datalad get` for the two CNeuroMod datasets:
#        - mario.stimuli  (NES ROM + retro integration metadata)
#        - mario.scenes   (per-session gameplay archives)
#   4. unpack the per-session gamelogs.tar archives inside mario.scenes
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
WX_INDEX_ROOT="https://extras.wxpython.org/wxPython4/extras/linux/gtk3"

# --- Detect distro → wxPython find-links URL ---------------------------------
# Echoes the wxPython find-links URL on stdout, or nothing if not applicable.
detect_wx_find_links() {
    [[ "$(uname -s)" != "Linux" ]] && return 0    # macOS/Windows: PyPI wheels work
    [[ ! -r /etc/os-release ]] && return 0

    local id="" version_id="" id_like="" ubuntu_codename=""
    # shellcheck source=/dev/null
    . /etc/os-release
    id="${ID:-}"
    version_id="${VERSION_ID:-}"
    id_like="${ID_LIKE:-}"
    ubuntu_codename="${UBUNTU_CODENAME:-}"

    # Map Ubuntu codenames → version (covers Ubuntu, Mint, Pop!_OS, elementary, Zorin…)
    codename_to_ubuntu() {
        case "$1" in
            noble)  echo "24.04" ;;
            jammy)  echo "22.04" ;;
            focal)  echo "20.04" ;;
            *)      return 1 ;;
        esac
    }
    # Debian codename → numeric major
    codename_to_debian() {
        case "$1" in
            bookworm) echo "12" ;;
            bullseye) echo "11" ;;
            *)        return 1 ;;
        esac
    }

    local flavour="" version=""
    case "$id" in
        ubuntu)
            flavour="ubuntu"; version="$version_id"
            ;;
        debian)
            flavour="debian"; version="${version_id%%.*}"
            ;;
        fedora)
            flavour="fedora"; version="${version_id%%.*}"
            ;;
        linuxmint|pop|neon|elementary|zorin|tuxedo|kde-neon)
            flavour="ubuntu"
            version="$(codename_to_ubuntu "$ubuntu_codename")" || version=""
            ;;
        *)
            if [[ " $id_like " == *" ubuntu "* ]]; then
                flavour="ubuntu"
                version="$(codename_to_ubuntu "$ubuntu_codename")" || version=""
            elif [[ " $id_like " == *" debian "* ]]; then
                flavour="debian"
                version="$(codename_to_debian "${VERSION_CODENAME:-}")" || version=""
            fi
            ;;
    esac

    if [[ -z $flavour || -z $version ]]; then
        echo "WARN: could not map distro '$id' '$version_id' to a wxPython wheel index." >&2
        echo "      Falling back to PyPI; uv sync may fail on wxpython." >&2
        return 0
    fi
    echo "${WX_INDEX_ROOT}/${flavour}-${version}/"
}

# --- Resolve data root --------------------------------------------------------
if [[ $# -ge 1 ]]; then
    DATA_ROOT="$1"
else
    read -e -r -p "Data root for datalad datasets [${REPO_ROOT}]: " DATA_ROOT
    DATA_ROOT="${DATA_ROOT:-$REPO_ROOT}"
fi
mkdir -p "$DATA_ROOT"
DATA_ROOT="$(cd "$DATA_ROOT" && pwd)"
echo "Installing datasets into: $DATA_ROOT"

# --- Tool checks --------------------------------------------------------------
if ! command -v uv >/dev/null 2>&1; then
    echo "ERROR: 'uv' not found in PATH." >&2
    echo "       Install it from https://docs.astral.sh/uv/getting-started/installation/" >&2
    echo "       or run:  curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
    exit 1
fi
command -v git >/dev/null 2>&1 || { echo "ERROR: 'git' not found." >&2; exit 1; }

# --- uv sync (with distro-matched wxPython wheel index) -----------------------
WX_LINKS="$(detect_wx_find_links || true)"
if [[ -n $WX_LINKS ]]; then
    echo "[uv sync] using wxPython wheel index: $WX_LINKS"
    uv sync --find-links "$WX_LINKS"
else
    echo "[uv sync]"
    uv sync
fi

# --- Install one dataset (no automatic get) ----------------------------------
install_dataset() {
    local url="$1" dest="$2"
    if [[ -d "$dest/.git" ]]; then
        echo "[skip install] $dest already a dataset"
    else
        echo "[datalad install] $url -> $dest"
        uv run datalad install -s "$url" "$dest"
    fi
}

# mario.stimuli is small (ROM + integration metadata) — fetch everything.
STIMULI_DEST="$DATA_ROOT/mario.stimuli"
install_dataset "$STIMULI_URL" "$STIMULI_DEST"
echo "[datalad get] $STIMULI_DEST (all)"
uv run datalad get -d "$STIMULI_DEST" "$STIMULI_DEST"

# mario.scenes contains BIDS-side func/ files (events.tsv, bold, etc.) that
# (a) we don't use and (b) have no publicurl configured on the public mirror
# and would fail to download. Restrict the get to the paths we actually need:
#   - sourcedata/scenes_info/  (scenes_mastersheet.csv)
#   - sub-*/ses-*/gamelogs.tar (per-session archives, unpacked below)
SCENES_DEST="$DATA_ROOT/mario.scenes"
install_dataset "$SCENES_URL" "$SCENES_DEST"

# Glob is shell-expanded against the annex symlinks that exist on disk after
# install. nullglob keeps an empty match from leaving the literal pattern.
shopt -s nullglob
SCENES_PATHS=( "$SCENES_DEST/sourcedata/scenes_info" )
for tar in "$SCENES_DEST"/sub-*/ses-*/gamelogs.tar; do
    SCENES_PATHS+=("$tar")
done
shopt -u nullglob
echo "[datalad get] $SCENES_DEST (${#SCENES_PATHS[@]} scoped paths: scenes_info + gamelogs.tar per session)"
uv run datalad get -d "$SCENES_DEST" "${SCENES_PATHS[@]}"

# --- Unpack scene archives ---------------------------------------------------
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
