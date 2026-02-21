#!/usr/bin/env bash
# setup_env.sh - Set up the wand conda environment.
# Creates a 'wand' conda env with git-annex and installs the wand_analysis package.
# Usage: bash scripts/setup_env.sh

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONDA="$HOME/miniconda3/bin/conda"

# ── 1. Check for Miniconda ───────────────────────────────────────────────────
if [[ ! -x "$CONDA" ]]; then
    echo "Miniconda not found at ~/miniconda3. Installing ..."
    wget -q https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/miniconda.sh
    bash /tmp/miniconda.sh -b -p ~/miniconda3
    ~/miniconda3/bin/conda init bash
    echo "Miniconda installed. Please restart your shell, then re-run this script."
    exit 0
fi

# ── 2. Create the wand conda env ─────────────────────────────────────────────
echo "Creating 'wand' conda environment with git-annex ..."
$CONDA create -n wand python=3.11 git-annex -c conda-forge -y

# ── 3. Install the wand_analysis package in editable mode ───────────────────
echo "Installing wand_analysis package ..."
~/miniconda3/envs/wand/bin/pip install -e "$REPO_ROOT"

echo ""
echo "Done. Activate your environment with:"
echo "  conda activate wand"
