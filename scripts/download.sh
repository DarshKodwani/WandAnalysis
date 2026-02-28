#!/usr/bin/env bash
# download.sh - Fetch WAND data at any level of the BIDS hierarchy via GIN.
#
# Pass 1–4 arguments to drill down from subject → session → folder → file.
# Everything inside the specified level is fetched.
#
#   bash scripts/download.sh <subject>
#   bash scripts/download.sh <subject> <session>
#   bash scripts/download.sh <subject> <session> <folder>
#   bash scripts/download.sh <subject> <session> <folder> <filename>
#
# Examples:
#   bash scripts/download.sh sub-43766                          # all sessions
#   bash scripts/download.sh sub-43766 ses-06                  # entire 7T session
#   bash scripts/download.sh sub-43766 ses-06 func             # just func folder
#   bash scripts/download.sh sub-43766 ses-06 func sub-43766_ses-06_task-rest_bold.nii.gz
#
# Prerequisites:
#   - wand conda environment active  (bash firstTimeSetup.sh)
#   - GIN CLI configured             (bash scripts/setup_gin.sh)

set -e

CONDA_BIN="$HOME/miniconda3/envs/wand/bin"
DEPLOY_KEY="$HOME/.ssh/wand_deploy_key"

# ── Colours ───────────────────────────────────────────────────────────────────
BOLD="\033[1m"
RESET="\033[0m"
CYAN="\033[0;36m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
DIM="\033[2m"
MAGENTA="\033[0;35m"

WAND_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../data/WAND" && pwd)"

# ── Usage ─────────────────────────────────────────────────────────────────────
if [[ $# -eq 0 ]]; then
    printf "\n${BOLD}Usage:${RESET}\n"
    printf "  bash scripts/download.sh ${CYAN}<subject>${RESET}\n"
    printf "  bash scripts/download.sh ${CYAN}<subject> <session>${RESET}\n"
    printf "  bash scripts/download.sh ${CYAN}<subject> <session> <folder>${RESET}\n"
    printf "  bash scripts/download.sh ${CYAN}<subject> <session> <folder> <filename>${RESET}\n"
    printf "\n${BOLD}Examples:${RESET}\n"
    printf "  bash scripts/download.sh sub-43766\n"
    printf "  bash scripts/download.sh sub-43766 ses-06\n"
    printf "  bash scripts/download.sh sub-43766 ses-06 func\n"
    printf "  bash scripts/download.sh sub-43766 ses-06 func sub-43766_ses-06_task-rest_bold.nii.gz\n"
    printf "\n${BOLD}Available subjects (first 10):${RESET}\n"
    ls -d "$WAND_ROOT"/sub-* 2>/dev/null | head -10 | xargs -I{} basename {} | \
        while read -r s; do printf "  ${CYAN}%s${RESET}\n" "$s"; done
    printf "\n"
    exit 1
fi

# ── Check git-annex and deploy key are available ─────────────────────────────
if [[ ! -x "$CONDA_BIN/git-annex" ]]; then
    printf "${RED}${BOLD}ERROR:${RESET} git-annex not found.\n"
    printf "Activate the wand environment and run: ${CYAN}bash scripts/setup_gin.sh${RESET}\n"
    exit 1
fi
if [[ ! -f "$DEPLOY_KEY" ]]; then
    printf "${RED}${BOLD}ERROR:${RESET} Deploy key not found at $DEPLOY_KEY.\n"
    printf "Run: ${CYAN}bash scripts/setup_gin.sh${RESET}\n"
    exit 1
fi

# ── Check if content is already downloaded (git-annex pointer detection) ──────
# Pointer files begin with /annex/objects/ — if the file doesn't, it's real data.
is_downloaded() {
    [[ -f "$1" ]] && ! head -c 14 "$1" 2>/dev/null | grep -q '^/annex/objects'
}

# ── Build target path from arguments ─────────────────────────────────────────
SUBJECT="${1}"
SESSION="${2:-}"
FOLDER="${3:-}"
FILENAME="${4:-}"

TARGET="$SUBJECT"
[[ -n "$SESSION"  ]] && TARGET="$TARGET/$SESSION"
[[ -n "$FOLDER"   ]] && TARGET="$TARGET/$FOLDER"
[[ -n "$FILENAME" ]] && TARGET="$TARGET/$FILENAME"

# ── Validate target exists in the repo ───────────────────────────────────────
if [[ ! -e "$WAND_ROOT/$TARGET" ]]; then
    printf "\n${RED}${BOLD}ERROR:${RESET} Path not found in repo:\n"
    printf "  %s\n\n" "$WAND_ROOT/$TARGET"
    exit 1
fi

# ── Print summary ─────────────────────────────────────────────────────────────
printf "\n"
printf "${BOLD}${CYAN}  WAND Download${RESET}\n"
printf "  ${DIM}%s${RESET}\n" "$(printf '%.0s─' {1..50})"
printf "  ${BOLD}${MAGENTA}%-12s${RESET} %s\n"  "Subject:"  "$SUBJECT"
[[ -n "$SESSION"  ]] && printf "  ${BOLD}%-12s${RESET} %s\n" "Session:"  "$SESSION"
[[ -n "$FOLDER"   ]] && printf "  ${BOLD}%-12s${RESET} %s\n" "Folder:"   "$FOLDER"
[[ -n "$FILENAME" ]] && printf "  ${BOLD}%-12s${RESET} %s\n" "File:"     "$FILENAME"
printf "  ${DIM}%s${RESET}\n\n" "$(printf '%.0s─' {1..50})"
printf "  Fetching: ${CYAN}%s${RESET}\n\n" "$TARGET"

# ── Check if already downloaded ───────────────────────────────────────────────
if [[ -f "$WAND_ROOT/$TARGET" ]]; then
    # Single file — check directly
    if is_downloaded "$WAND_ROOT/$TARGET"; then
        SIZE=$(du -sh "$WAND_ROOT/$TARGET" 2>/dev/null | cut -f1)
        printf "  ${GREEN}${BOLD}✔ Already downloaded.${RESET}  ${DIM}%s (%s)${RESET}\n\n" \
            "$TARGET" "$SIZE"
        exit 0
    fi
else
    # Directory — count already-present vs pointer files
    ALREADY=0
    PENDING=0
    while IFS= read -r -d '' F; do
        if is_downloaded "$F"; then
            ALREADY=$(( ALREADY + 1 ))
        else
            PENDING=$(( PENDING + 1 ))
        fi
    done < <(find "$WAND_ROOT/$TARGET" -name "*.nii.gz" -print0 2>/dev/null)
    if (( PENDING == 0 && ALREADY > 0 )); then
        printf "  ${GREEN}${BOLD}✔ Already downloaded${RESET}  ${DIM}(%d NIfTI file(s) present)${RESET}\n\n" "$ALREADY"
        exit 0
    elif (( ALREADY > 0 )); then
        printf "  ${YELLOW}${BOLD}⚠ Partially downloaded${RESET}  ${DIM}%d present, %d pending${RESET}\n\n" \
            "$ALREADY" "$PENDING"
    fi
fi

# ── Run git-annex get ────────────────────────────────────────────────────────
cd "$WAND_ROOT"
GIT_SSH_COMMAND="ssh -i $DEPLOY_KEY -o IdentitiesOnly=yes" \
    PATH="$CONDA_BIN:$PATH" git-annex get "$TARGET"

# ── Done ──────────────────────────────────────────────────────────────────────
SIZE=$(du -sh "$WAND_ROOT/$TARGET" 2>/dev/null | cut -f1)
printf "\n  ${GREEN}${BOLD}✔ Done.${RESET}  ${BOLD}%s${RESET} fetched  ${DIM}(total: %s)${RESET}\n\n" \
    "$TARGET" "$SIZE"
