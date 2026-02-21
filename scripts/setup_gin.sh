#!/usr/bin/env bash
# setup_gin.sh - Configure the GIN CLI for accessing the WAND dataset.
# Assumes the 'wand' conda environment already exists (created by setup_env.sh).
# Usage: bash scripts/setup_gin.sh

set -e

CONDA_BIN="$HOME/miniconda3/envs/wand/bin"

# ── 1. Verify git-annex ───────────────────────────────────────────────────────
echo "Checking for git-annex in wand env ..."
if [[ ! -x "$CONDA_BIN/git-annex" ]]; then
    echo "ERROR: git-annex not found in $CONDA_BIN"
    echo "Recreate the wand env with: conda create -n wand python=3.11 git-annex -c conda-forge -y"
    exit 1
fi
echo "  git-annex: $($CONDA_BIN/git-annex version | head -1)"

# ── 2. Install gin CLI if missing ────────────────────────────────────────────
echo "Checking for gin CLI ..."
if [[ ! -x "$CONDA_BIN/gin" ]]; then
    echo "  gin not found — downloading v1.12 ..."
    curl -sL https://github.com/G-Node/gin-cli/releases/download/v1.12/gin-cli-1.12-linux.tar.gz \
        | tar xz -C /tmp
    cp /tmp/gin "$CONDA_BIN/gin"
    chmod +x "$CONDA_BIN/gin"
    echo "  gin installed."
fi
echo "  gin: $(PATH=$CONDA_BIN:$PATH $CONDA_BIN/gin --version 2>&1 | head -1)"

# ── 3. Log in ────────────────────────────────────────────────────────────────
echo ""
echo "Logging into GIN (gin.g-node.org) ..."
echo "If you don't have an account, register at: https://gin.g-node.org/user/sign_up"
echo ""
PATH=$CONDA_BIN:$PATH $CONDA_BIN/gin login

# ── 4. Next steps ────────────────────────────────────────────────────────────
echo ""
echo "Setup complete. Next steps:"
echo ""
echo "  1. Add your SSH public key at: https://gin.g-node.org/user/settings/ssh"
echo "     Your public key: ~/.ssh/id_rsa.pub (or id_ed25519.pub)"
echo ""
echo "  2. Activate the wand environment:"
echo "     conda activate wand"
echo ""
echo "  3. Clone the WAND repo (metadata only, no large files):"
echo "     cd /path/to/your/data && gin get CUBRIC/WAND"
echo ""
echo "  4. Update configs/paths.yaml to point wand_raw at the cloned WAND directory."
echo ""
echo "  5. Fetch a subject's 7T T1w (example):"
echo "     cd /path/to/WAND"
echo "     gin get-content sub-00395/ses-03/anat/sub-00395_ses-03_T1w.nii.gz"
echo ""
echo "     Or use the helper script:"
echo "     bash scripts/fetch_subject.sh sub-00395 anat"
