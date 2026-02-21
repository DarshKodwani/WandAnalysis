#!/usr/bin/env bash
# setup_gin.sh - Install and configure the GIN CLI for accessing the WAND dataset.
# Usage: bash scripts/setup_gin.sh

set -e

BIN_DIR="$HOME/.local/bin"
mkdir -p "$BIN_DIR"

# ── 1. Check git-annex ───────────────────────────────────────────────────────
echo "Checking for git-annex ..."
if ! command -v git-annex &>/dev/null; then
    echo "WARNING: git-annex not found. GIN requires git-annex to fetch large files."
    echo "Ask your sysadmin to install it, or install via conda:"
    echo "  conda install -c conda-forge git-annex"
    echo ""
else
    echo "  git-annex found: $(git-annex version | head -1)"
fi

# ── 2. Install gin CLI if missing ────────────────────────────────────────────
echo "Checking for gin CLI ..."
if command -v gin &>/dev/null; then
    echo "  gin found: $(gin --version 2>&1 | head -1)"
else
    echo "  gin not found — downloading to $BIN_DIR ..."
    GIN_VERSION="v1.24"
    GIN_URL="https://gin.g-node.org/G-Node/gin-cli/releases/download/${GIN_VERSION}/gin-cli-${GIN_VERSION}-linux-amd64.tar.gz"
    curl -sL "$GIN_URL" | tar xz -C /tmp
    cp /tmp/gin "$BIN_DIR/gin"
    chmod +x "$BIN_DIR/gin"
    echo "  gin installed at $BIN_DIR/gin"

    # Ensure ~/.local/bin is on PATH
    if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
        echo ""
        echo "  NOTE: Add $BIN_DIR to your PATH by adding this to your ~/.bashrc:"
        echo "    export PATH=\"\$HOME/.local/bin:\$PATH\""
    fi
fi

# ── 3. Log in ────────────────────────────────────────────────────────────────
echo ""
echo "Logging into GIN (gin.g-node.org) ..."
echo "If you don't have an account, register at: https://gin.g-node.org/user/sign_up"
echo ""
gin login

# ── 4. Next steps ────────────────────────────────────────────────────────────
echo ""
echo "Setup complete. Next steps:"
echo ""
echo "  1. Add your SSH public key at: https://gin.g-node.org/user/settings/ssh"
echo "     Your public key is at: ~/.ssh/id_rsa.pub (or id_ed25519.pub)"
echo ""
echo "  2. Clone the WAND repo (metadata only, no large files):"
echo "     cd /path/to/your/data && gin get CUBRIC/WAND"
echo ""
echo "  3. Update configs/paths.yaml to point wand_raw at the cloned WAND directory."
echo ""
echo "  4. Fetch a subject:"
echo "     bash scripts/fetch_subject.sh sub-001"
