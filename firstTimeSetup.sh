#!/usr/bin/env bash
# firstTimeSetup.sh - One-time setup for new contributors to this repo.
#
# What it does:
#   1. Installs Miniconda (if not already present)
#   2. Creates the 'wand' conda environment with Python 3.11 and git-annex
#   3. Installs the wand_analysis package in editable mode
#   4. Optionally runs the GIN CLI setup (for WAND dataset access)
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

# ── Step 3: Install dependencies ─────────────────────────────────────────────
cyan "[3/3] Installing dependencies from pyproject.toml ..."

"$ENV_BIN/pip" install -q -e "$REPO_ROOT"
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

# ── Optional: GIN setup ───────────────────────────────────────────────────────
echo ""
echo "GIN gives you access to the WAND raw dataset (no GIN account needed)."
read -r -p "Set up WAND data access now? [y/N] " GIN_REPLY
if [[ "${GIN_REPLY,,}" == "y" ]]; then
    bash "$REPO_ROOT/scripts/setup_gin.sh"
else
    echo "  Skipped. Run later with:  bash scripts/setup_gin.sh"
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
echo "Then you can run the analysis scripts, e.g.:"
echo ""
echo "    python scripts/step1_visualiseT1w.py"
echo "    python scripts/step2_inspectParams.py"
echo ""
