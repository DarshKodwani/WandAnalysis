#!/usr/bin/env bash
# firstTimeSetup.sh - One-time setup for new contributors to this repo.
#
# What it does:
#   1. Installs Miniconda (if not already present)
#   2. Creates the 'wand' conda environment with Python 3.11 and git-annex
#   3. Installs Python dependencies (nibabel, nilearn, matplotlib, scipy, pyyaml)
#   4. Sets up read-only GIN access using the bundled deploy key
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
cyan "[1/3] Checking for Miniconda ..."

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
cyan "[2/3] Setting up the '$ENV_NAME' conda environment ..."

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
cyan "[3/4] Installing Python dependencies ..."

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

# ── Step 4: GIN deploy key setup ─────────────────────────────────────────────
echo ""
cyan "[4/4] Configuring WAND data access (GIN deploy key) ..."

if [[ ! -f "$DEPLOY_KEY_SRC" ]]; then
    warn "  Deploy key not found at $DEPLOY_KEY_SRC — skipping."
    warn "  Data download will not work until the key is present in scripts/."
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
    green "  GIN access configured."
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
echo "Then run the pipeline, e.g.:"
echo ""
echo "    python scripts/batch_qc.py --all"
echo "    python scripts/visualise_bold.py sub-43766"
echo ""
