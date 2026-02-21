#!/usr/bin/env bash
# setup_env.sh - Run once after cloning to create a virtual environment
# and install the wand_analysis package in editable mode.
# Usage: bash scripts/setup_env.sh

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$REPO_ROOT/.venv"

echo "Creating virtual environment at $VENV_DIR ..."
python3 -m venv "$VENV_DIR"

echo "Activating and installing package ..."
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install -e "$REPO_ROOT"

echo ""
echo "Done. Activate your environment with:"
echo "  source .venv/bin/activate"
