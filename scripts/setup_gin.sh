#!/usr/bin/env bash
# setup_gin.sh - Set up read-only access to the WAND dataset using the bundled
#                deploy key. No GIN account required.
# Assumes the 'wand' conda environment already exists (created by firstTimeSetup.sh).
# Usage: bash scripts/setup_gin.sh

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONDA_BIN="$HOME/miniconda3/envs/wand/bin"
DEPLOY_KEY_SRC="$REPO_ROOT/scripts/wand_deploy_key"
DEPLOY_KEY_DST="$HOME/.ssh/wand_deploy_key"
SSH_CONFIG="$HOME/.ssh/config"

# ── 1. Verify git-annex ───────────────────────────────────────────────────────
echo "Checking for git-annex in wand env ..."
if [[ ! -x "$CONDA_BIN/git-annex" ]]; then
    echo "ERROR: git-annex not found in $CONDA_BIN"
    echo "Recreate the wand env with: conda create -n wand python=3.11 git-annex -c conda-forge -y"
    exit 1
fi
echo "  git-annex: $($CONDA_BIN/git-annex version | head -1)"

# ── 2. Install deploy key ─────────────────────────────────────────────────────
echo "Installing WAND deploy key ..."
mkdir -p "$HOME/.ssh"
cp "$DEPLOY_KEY_SRC" "$DEPLOY_KEY_DST"
chmod 600 "$DEPLOY_KEY_DST"
echo "  Key installed at $DEPLOY_KEY_DST"

# ── 3. Configure SSH for gin.g-node.org ──────────────────────────────────────
echo "Configuring SSH ..."
touch "$SSH_CONFIG"
chmod 600 "$SSH_CONFIG"
if ! grep -q "# WAND deploy key" "$SSH_CONFIG"; then
    cat >> "$SSH_CONFIG" <<EOF

# WAND deploy key (added by WandAnalysis/scripts/setup_gin.sh)
Host gin.g-node.org
    IdentityFile $DEPLOY_KEY_DST
    IdentitiesOnly yes
    StrictHostKeyChecking no
EOF
    echo "  SSH config updated."
else
    echo "  SSH config already set — skipping."
fi

# ── 4. Locate the WAND dataset ───────────────────────────────────────────────
BUNDLED_WAND="$REPO_ROOT/data/WAND"

if [[ -d "$BUNDLED_WAND" ]]; then
    echo "  WAND data found at $BUNDLED_WAND — no clone needed."
    WAND_DIR="$BUNDLED_WAND"
else
    echo ""
    echo "WAND data not found inside this folder."
    echo "Where should it be cloned?"
    read -r -p "  Destination path [default: $HOME/data/WAND]: " WAND_DIR
    WAND_DIR="${WAND_DIR:-$HOME/data/WAND}"

    if [[ -d "$WAND_DIR/.git" ]]; then
        echo "  Repo already exists at $WAND_DIR — skipping clone."
    else
        echo "  Cloning WAND metadata (no large files) ..."
        mkdir -p "$(dirname "$WAND_DIR")"
        GIT_SSH_COMMAND="ssh -i $DEPLOY_KEY_DST -o IdentitiesOnly=yes" \
            git clone git@gin.g-node.org:CUBRIC/WAND "$WAND_DIR"
        cd "$WAND_DIR"
        PATH="$CONDA_BIN:$PATH" git-annex init --quiet
        echo "  Cloned to $WAND_DIR"
    fi
fi

# ── 5. Write path into configs/paths.yaml ────────────────────────────────────
PATHS_YAML="$REPO_ROOT/configs/paths.yaml"
PATHS_EXAMPLE="$REPO_ROOT/configs/paths.example.yaml"
if [[ ! -f "$PATHS_YAML" ]] && [[ -f "$PATHS_EXAMPLE" ]]; then
    cp "$PATHS_EXAMPLE" "$PATHS_YAML"
fi
if [[ -f "$PATHS_YAML" ]] && ! grep -q "^wand_raw:" "$PATHS_YAML"; then
    echo "wand_raw: $WAND_DIR" >> "$PATHS_YAML"
    echo "  Written wand_raw to configs/paths.yaml"
elif [[ -f "$PATHS_YAML" ]]; then
    sed -i "s|^wand_raw:.*|wand_raw: $WAND_DIR|" "$PATHS_YAML"
    echo "  Updated wand_raw in configs/paths.yaml"
fi

# ── 6. Next steps ─────────────────────────────────────────────────────────────
echo ""
echo "Setup complete. To download a subject's data:"
echo ""
echo "  bash scripts/fetch_subject.sh sub-00395           # all modalities"
echo "  bash scripts/fetch_subject.sh sub-00395 anat      # one modality"
