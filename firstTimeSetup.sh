#!/usr/bin/env bash
# firstTimeSetup.sh - One-time setup for new contributors to this repo.
#
# What it does:
#   1. Installs Miniconda (if not already present)
#   2. Creates the 'wand' conda environment with Python 3.11 and git-annex
#   3. Installs Python dependencies (nibabel, nilearn, matplotlib, scipy, pyyaml, pandas)
#   4. Sets up GIN access (deploy key + gin CLI binary)
#   5. Downloads the CUBRIC/WAND dataset into data/
#
# Usage:
#   bash firstTimeSetup.sh
#
# After running, activate the environment with:
#   conda activate wand

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONDA_ROOT="$HOME/miniconda3"
ENV_NAME="wand"
DEPLOY_KEY_SRC="$REPO_ROOT/scripts/wand_deploy_key"
DEPLOY_KEY_DST="$HOME/.ssh/wand_deploy_key"
SSH_CONFIG="$HOME/.ssh/config"

# ── Helpers ───────────────────────────────────────────────────────────────────
cyan()  { printf '\033[0;36m%s\033[0m\n' "$*"; }
green() { printf '\033[0;32m%s\033[0m\n' "$*"; }
warn()  { printf '\033[0;33mWARN: %s\033[0m\n' "$*"; }
err()   { printf '\033[0;31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }

# Animated spinner shown while a background PID is running.
# Usage: spin_wait <pid> <label>
# Returns the exit code of the background process.
spin_wait() {
    local pid=$1 label=$2
    local frames=(⠋ ⠙ ⠹ ⠸ ⠼ ⠴ ⠦ ⠧ ⠇ ⠏)
    local i=0 elapsed=0
    printf "\n"
    while kill -0 "$pid" 2>/dev/null; do
        printf "\r  \033[0;36m%s\033[0m  %s  (\033[0;33m%ds\033[0m elapsed)" \
            "${frames[$((i % 10))]}" "$label" "$elapsed"
        sleep 1
        (( i++, elapsed++ )) || true
    done
    printf "\r%-70s\r" ""   # clear spinner line
    wait "$pid"
}

# ── OS / Architecture detection ──────────────────────────────────────────────
case "$(uname -s 2>/dev/null)" in
    Darwin)               OS="macos"   ;;
    Linux)                OS="linux"   ;;
    MINGW*|MSYS*|CYGWIN*) OS="windows" ;;
    *) err "Unsupported OS: $(uname -s). This script supports macOS, Linux, and Windows (Git Bash)." ;;
esac

case "$(uname -m 2>/dev/null)" in
    arm64|aarch64)  ARCH="arm64"  ;;
    *)              ARCH="x86_64" ;;
esac

if [[ "$OS" == "windows" ]]; then
    CONDA="$CONDA_ROOT/Scripts/conda"
    ENV_BIN="$CONDA_ROOT/envs/$ENV_NAME/Scripts"
    GIN_EXE_SUFFIX=".exe"
else
    CONDA="$CONDA_ROOT/bin/conda"
    ENV_BIN="$CONDA_ROOT/envs/$ENV_NAME/bin"
    GIN_EXE_SUFFIX=""
fi

cyan "==================================================="
cyan "  WAND Analysis — First-Time Setup"
cyan "==================================================="
echo ""

# ── Step 1: Miniconda ─────────────────────────────────────────────────────────
cyan "[1/5] Checking for Miniconda ..."

if [[ ! -x "$CONDA" ]]; then
    echo "  Miniconda not found at $CONDA_ROOT — installing ..."
    case "$OS" in
        macos)
            [[ "$ARCH" == "arm64" ]] \
                && MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-arm64.sh" \
                || MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh"
            curl -fsSL "$MINICONDA_URL" -o /tmp/miniconda.sh
            bash /tmp/miniconda.sh -b -p "$CONDA_ROOT"
            rm -f /tmp/miniconda.sh
            "$CONDA_ROOT/bin/conda" init bash
            "$CONDA_ROOT/bin/conda" init zsh
            ;;
        linux)
            curl -fsSL "https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh" \
                -o /tmp/miniconda.sh
            bash /tmp/miniconda.sh -b -p "$CONDA_ROOT"
            rm -f /tmp/miniconda.sh
            "$CONDA_ROOT/bin/conda" init bash
            ;;
        windows)
            echo "  Downloading Windows installer ..."
            curl -fsSL "https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe" \
                -o /tmp/miniconda.exe
            echo "  Running silent installer (may take a few minutes) ..."
            cmd.exe //c "start /wait \"\" \"$(cygpath -w /tmp/miniconda.exe)\" /S /D=$(cygpath -w "$CONDA_ROOT")"
            rm -f /tmp/miniconda.exe
            "$CONDA_ROOT/Scripts/conda" init bash
            ;;
    esac
    green "  Miniconda installed."
    echo ""
    warn "  Your shell config has been updated by 'conda init'."
    warn "  Please close this terminal, open a new one, and re-run:"
    warn "    bash firstTimeSetup.sh"
    exit 0
else
    echo "  Found: $("$CONDA" --version)"
fi

# ── Step 2: Create / update the conda environment ────────────────────────────
cyan "[2/5] Setting up the '$ENV_NAME' conda environment ..."

if "$CONDA" env list | grep -qE "^${ENV_NAME}[[:space:]]"; then
    echo "  Environment '$ENV_NAME' already exists — skipping creation."
    echo "  To recreate it from scratch run:"
    echo "    conda env remove -n $ENV_NAME && bash firstTimeSetup.sh"
else
    echo "  Creating environment (this may take a few minutes) ..."
    "$CONDA" create -n "$ENV_NAME" python=3.11 -c conda-forge -y
    green "  Environment '$ENV_NAME' created."
fi

# Install git-annex — conda-forge doesn't ship it for osx-arm64, so use Homebrew there
echo ""
cyan "Installing git-annex ..."
if [[ "$OS" == "macos" ]]; then
    if command -v git-annex &>/dev/null; then
        echo "  git-annex already installed: $(git-annex version | head -1)"
    elif command -v brew &>/dev/null; then
        brew install git-annex
        green "  git-annex installed via Homebrew."
    else
        warn "  Homebrew not found — cannot install git-annex automatically on macOS."
        warn "  Install Homebrew first: https://brew.sh  then re-run this script."
        warn "  Or install git-annex manually and ensure it is on your PATH."
    fi
elif [[ "$OS" == "linux" ]]; then
    if command -v git-annex &>/dev/null; then
        echo "  git-annex already installed: $(git-annex version | head -1)"
    else
        "$CONDA" install -n "$ENV_NAME" git-annex -c conda-forge -y
        green "  git-annex installed via conda-forge."
    fi
fi

# ── Step 3: Install Python dependencies ──────────────────────────────────────────
cyan "[3/5] Installing Python dependencies ..."

"$ENV_BIN/pip" install -q nibabel nilearn matplotlib scipy pyyaml pandas
green "  Dependencies installed."

echo ""
cyan "Installing optional developer tooling ..."
"$ENV_BIN/pip" install -q pytest ruff pre-commit || warn "  Could not install optional developer tooling."

# ── Quick sanity check ────────────────────────────────────────────────────────
echo ""
cyan "Sanity check ..."
"$ENV_BIN/python" - <<'EOF'
import nibabel, nilearn, matplotlib, yaml, scipy, pandas
print(f"  nibabel    {nibabel.__version__}")
print(f"  nilearn    {nilearn.__version__}")
print(f"  matplotlib {matplotlib.__version__}")
print(f"  scipy      {scipy.__version__}")
print(f"  pandas     {pandas.__version__}")
print("  All dependencies importable ✓")
EOF

# ── Step 4: GIN deploy key + CLI setup ───────────────────────────────────────
echo ""
cyan "[4/5] Configuring GIN access (deploy key + gin CLI) ..."

# -- Deploy key --
if [[ ! -f "$DEPLOY_KEY_SRC" ]]; then
    warn "  Deploy key not found at $DEPLOY_KEY_SRC — skipping."
    warn "  Private data download may not work until the key is present in scripts/."
else
    mkdir -p "$HOME/.ssh"
    cp "$DEPLOY_KEY_SRC" "$DEPLOY_KEY_DST"
    chmod 600 "$DEPLOY_KEY_DST"
    echo "  Deploy key installed at $DEPLOY_KEY_DST"

    touch "$SSH_CONFIG"
    chmod 600 "$SSH_CONFIG"
    if ! grep -q "# WAND deploy key" "$SSH_CONFIG"; then
        cat >> "$SSH_CONFIG" <<SSHEOF

# WAND deploy key (added by WandAnalysis/firstTimeSetup.sh)
Host gin.g-node.org
    IdentityFile $DEPLOY_KEY_DST
    IdentitiesOnly yes
    StrictHostKeyChecking no
SSHEOF
        echo "  SSH config updated."
    else
        echo "  SSH config already set — skipping."
    fi

    if [[ ! -x "$ENV_BIN/git-annex" ]]; then
        warn "  git-annex not found in $ENV_BIN — data download unavailable."
        warn "  Try: conda install -n $ENV_NAME git-annex -c conda-forge"
    else
        echo "  git-annex: $($ENV_BIN/git-annex version | head -1)"
    fi
fi

# -- gin CLI --
GIN_BIN_DIR="$HOME/.local/bin"
GIN_BIN="$GIN_BIN_DIR/gin${GIN_EXE_SUFFIX}"

if command -v gin &>/dev/null; then
    echo "  gin CLI already available: $(gin --version 2>&1 | head -1)"
elif [[ -x "$GIN_BIN" ]]; then
    export PATH="$GIN_BIN_DIR:$PATH"
    echo "  gin CLI found at $GIN_BIN: $(gin --version 2>&1 | head -1)"
else
    case "$OS" in
        macos)   GIN_ASSET="gin-cli-latest-macOS.tar.gz"  ;;
        linux)   GIN_ASSET="gin-cli-latest-linux.tar.gz"  ;;
        windows) GIN_ASSET="gin-cli-latest-windows.zip"   ;;
    esac
    echo "  gin CLI not found — downloading $GIN_ASSET ..."
    mkdir -p "$GIN_BIN_DIR"
    GIN_TMP="/tmp/$GIN_ASSET"
    curl -fL \
        "https://gin.g-node.org/G-Node/gin-cli-releases/raw/master/$GIN_ASSET" \
        -o "$GIN_TMP"
    GIN_TMP_DIR=$(mktemp -d)
    if [[ "$OS" == "windows" ]]; then
        unzip -q "$GIN_TMP" -d "$GIN_TMP_DIR"
    else
        tar -xzf "$GIN_TMP" -C "$GIN_TMP_DIR"
    fi
    GIN_EXTRACTED=$(find "$GIN_TMP_DIR" -name "gin${GIN_EXE_SUFFIX}" -type f | head -1)
    if [[ -z "$GIN_EXTRACTED" ]]; then
        rm -rf "$GIN_TMP_DIR" "$GIN_TMP"
        err "  Could not find gin binary in the downloaded archive."
    fi
    mv "$GIN_EXTRACTED" "$GIN_BIN"
    [[ "$OS" != "windows" ]] && chmod +x "$GIN_BIN"
    rm -rf "$GIN_TMP_DIR" "$GIN_TMP"
    export PATH="$GIN_BIN_DIR:$PATH"
    green "  gin CLI installed at $GIN_BIN"
    warn "  Ensure ~/.local/bin is in your PATH. Add to your shell config if needed:"
    warn "    export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

green "  GIN access configured."

# ── Step 5: Download WAND dataset ─────────────────────────────────────────────
echo ""
cyan "[5/5] Setting up WAND dataset in data/ ..."

DATA_DIR="$REPO_ROOT/data"
WAND_DIR="$DATA_DIR/WAND"
DO_DOWNLOAD=true

if [[ -d "$WAND_DIR/.git" ]]; then
    echo ""
    warn "  WAND dataset already exists at $WAND_DIR"
    echo ""
    printf "  Delete and re-download, or skip? [d = delete & re-download / s = skip]: "
    read -r WAND_CHOICE
    echo ""
    case "$WAND_CHOICE" in
        d|D)
            echo "  Removing existing WAND directory ..."
            rm -rf "$WAND_DIR"
            green "  Removed. Will re-download."
            ;;
        *)
            echo "  Skipping WAND download."
            DO_DOWNLOAD=false
            ;;
    esac
fi

if [[ "$DO_DOWNLOAD" == true ]]; then
    echo "  Running: gin get CUBRIC/WAND"
    GIN_LOG=$(mktemp /tmp/gin_get_XXXXXX.log)
    T_START=$(date +%s)
    cd "$DATA_DIR"
    gin get CUBRIC/WAND > "$GIN_LOG" 2>&1 &
    GIN_PID=$!
    spin_wait "$GIN_PID" "Downloading WAND dataset (this may take several minutes) ..."
    GIN_EXIT=$?
    T_END=$(date +%s)
    ELAPSED=$(( T_END - T_START ))
    if [[ $GIN_EXIT -ne 0 ]]; then
        echo ""
        warn "  gin get output:"
        cat "$GIN_LOG"
        rm -f "$GIN_LOG"
        err "  gin get CUBRIC/WAND failed (exit code $GIN_EXIT)."
    fi
    rm -f "$GIN_LOG"
    echo ""
    green "  WAND dataset ready at $WAND_DIR  (took ${ELAPSED}s)"
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
green "==================================================="
green "  Setup complete!"
green "==================================================="
echo ""
echo "Data is in: $REPO_ROOT/data/WAND"
echo ""
echo "Then run the pipeline, e.g.:"
echo ""
echo "    python scripts/batch_qc.py --all"
echo "    python scripts/visualise_bold.py sub-43766"
echo ""

# ── Activate the conda environment ───────────────────────────────────────────
# Source conda so 'conda activate' is available, then activate.
CONDA_SH="$CONDA_ROOT/etc/profile.d/conda.sh"
if [[ -f "$CONDA_SH" ]]; then
    # shellcheck source=/dev/null
    source "$CONDA_SH"
    conda activate "$ENV_NAME"
    green "  ✓ conda env '$ENV_NAME' is now active in this terminal."
else
    warn "  Could not find $CONDA_SH to activate the environment."
    warn "  Run manually: conda activate $ENV_NAME"
fi

# If the script was run directly (bash firstTimeSetup.sh) rather than sourced,
# the activated environment only affects this subprocess.  Inform the user.
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo ""
    warn "  Tip: this terminal won't inherit the activated env because the script"
    warn "  was run as a subprocess.  To make it stick, either:"
    warn "    1) source firstTimeSetup.sh   (re-run from scratch in this shell)"
    warn "    2) conda activate $ENV_NAME   (quick one-liner after this script)"
    echo ""
fi
