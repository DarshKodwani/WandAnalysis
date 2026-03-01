#!/usr/bin/env bash
# firstTimeSetup.sh - One-time setup for new contributors to this repo.
#
# What it does:
#   1. Installs Miniconda (if not already present)
#   2. Creates the 'wand' conda environment with Python 3.11 and git-annex
#   3. Installs Python dependencies (nibabel, nilearn, matplotlib, scipy, pyyaml)
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
CONDA="$CONDA_ROOT/bin/conda"
ENV_NAME="wand"
ENV_BIN="$CONDA_ROOT/envs/$ENV_NAME/bin"
DEPLOY_KEY_SRC="$REPO_ROOT/scripts/wand_deploy_key"
DEPLOY_KEY_DST="$HOME/.ssh/wand_deploy_key"
SSH_CONFIG="$HOME/.ssh/config"

# ── Helpers ───────────────────────────────────────────────────────────────────
cyan()  { printf '\033[0;36m%s\033[0m\n' "$*"; }
green() { printf '\033[0;32m%s\033[0m\n' "$*"; }
warn()  { printf '\033[0;33mWARN: %s\033[0m\n' "$*"; }
err()   { printf '\033[0;31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }

cyan "==================================================="
cyan "  WAND Analysis — First-Time Setup"
cyan "==================================================="
echo ""

# ── Step 1: Miniconda ─────────────────────────────────────────────────────────
cyan "[1/5] Checking for Miniconda ..."

if [[ ! -x "$CONDA" ]]; then
    echo "  Miniconda not found at $CONDA_ROOT — installing ..."
    MINICONDA_INSTALLER="/tmp/miniconda.sh"
    wget -q https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh \
        -O "$MINICONDA_INSTALLER"
    bash "$MINICONDA_INSTALLER" -b -p "$CONDA_ROOT"
    rm -f "$MINICONDA_INSTALLER"
    "$CONDA_ROOT/bin/conda" init bash
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
    "$CONDA" create -n "$ENV_NAME" python=3.11 git-annex -c conda-forge -y
    green "  Environment '$ENV_NAME' created."
fi

# ── Step 3: Install Python dependencies ──────────────────────────────────────────
cyan "[3/5] Installing Python dependencies ..."

"$ENV_BIN/pip" install -q nibabel nilearn matplotlib scipy pyyaml
green "  Dependencies installed."

# ── Quick sanity check ────────────────────────────────────────────────────────
echo ""
cyan "Sanity check ..."
"$ENV_BIN/python" - <<'EOF'
import nibabel, nilearn, matplotlib, yaml, scipy
print(f"  nibabel    {nibabel.__version__}")
print(f"  nilearn    {nilearn.__version__}")
print(f"  matplotlib {matplotlib.__version__}")
print(f"  scipy      {scipy.__version__}")
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
GIN_BIN="$GIN_BIN_DIR/gin"

if command -v gin &>/dev/null; then
    echo "  gin CLI already available: $(gin --version 2>&1 | head -1)"
elif [[ -x "$GIN_BIN" ]]; then
    export PATH="$GIN_BIN_DIR:$PATH"
    echo "  gin CLI found at $GIN_BIN: $(gin --version 2>&1 | head -1)"
else
    echo "  gin CLI not found — downloading latest Linux binary ..."
    mkdir -p "$GIN_BIN_DIR"
    GIN_TMP="/tmp/gin-cli-latest-linux.tar.gz"
    wget -q --show-progress \
        "https://gin.g-node.org/G-Node/gin-cli-releases/raw/master/gin-cli-latest-linux.tar.gz" \
        -O "$GIN_TMP"
    GIN_TMP_DIR=$(mktemp -d)
    tar -xzf "$GIN_TMP" -C "$GIN_TMP_DIR"
    GIN_EXTRACTED=$(find "$GIN_TMP_DIR" -name "gin" -type f | head -1)
    if [[ -z "$GIN_EXTRACTED" ]]; then
        rm -rf "$GIN_TMP_DIR" "$GIN_TMP"
        err "  Could not find gin binary in the downloaded archive."
    fi
    mv "$GIN_EXTRACTED" "$GIN_BIN"
    chmod +x "$GIN_BIN"
    rm -rf "$GIN_TMP_DIR" "$GIN_TMP"
    export PATH="$GIN_BIN_DIR:$PATH"
    green "  gin CLI installed at $GIN_BIN"
    warn "  Ensure ~/.local/bin is in your PATH. Add to ~/.bashrc if needed:"
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
    warn "  This may take several minutes — progress is shown below."
    echo ""
    T_START=$(date +%s)
    cd "$DATA_DIR"
    gin get CUBRIC/WAND
    T_END=$(date +%s)
    ELAPSED=$(( T_END - T_START ))
    echo ""
    green "  WAND dataset ready at $WAND_DIR  (took ${ELAPSED}s)"
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
green "==================================================="
green "  Setup complete!"
green "==================================================="
echo ""
echo "Activate your environment in any new terminal with:"
echo ""
echo "    conda activate $ENV_NAME"
echo ""
echo "Data is in: $DATA_DIR/WAND"
echo ""
echo "Then run the pipeline, e.g.:"
echo ""
echo "    python scripts/batch_qc.py --all"
echo "    python scripts/visualise_bold.py sub-43766"
echo ""
