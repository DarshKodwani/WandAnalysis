#!/usr/bin/env bash
# find_downloaded.sh - List NIfTI files that have been fully downloaded from GIN.
#
# git-annex stores undownloaded files as tiny pointer files (~64 bytes).
# A file is considered "downloaded" if it passes BOTH:
#   1. Pointer check  — content does NOT start with /annex/objects/
#   2. Size threshold — file is at least MIN_SIZE_MB megabytes
#
# Why combine both?
#   - Small files git-tracks directly (field maps, JSON, ~100-900 KB) are never
#     annexed, so they always pass the pointer check. The size filter removes them.
#   - The smallest real annexed fMRI file seen in WAND is the sbref (~2 MB),
#     so 1 MB is a safe default that catches everything meaningful.
#
# To change the threshold, edit MIN_SIZE_MB below.
#
# Usage:
#   bash scripts/find_downloaded.sh              # all subjects
#   bash scripts/find_downloaded.sh sub-43766    # one subject
#
# Output columns: size, subject/session, filename

set -e

# ── Colours ───────────────────────────────────────────────────────────────────
BOLD="\033[1m"
RESET="\033[0m"
CYAN="\033[0;36m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
DIM="\033[2m"

# ── Size threshold (edit this to change what counts as "real" data) ──────────
# Files smaller than this (in MB) are treated as git-tracked metadata and ignored
# even if they pass the pointer check.
# Recommended: 1 MB  (smallest real annexed fMRI file in WAND is sbref ~2 MB)
MIN_SIZE_MB=1
MIN_BYTES=$(( MIN_SIZE_MB * 1024 * 1024 ))

WAND_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../data/WAND" && pwd)"
SUBJECT_FILTER="${1:-}"

# ── Detection: pointer check + size threshold ─────────────────────────────────
# A file is "downloaded" if it is NOT a git-annex pointer AND is >= MIN_SIZE_MB.
# Detect a real downloaded file vs a git-annex pointer file.
# Pointer files (unlocked mode) begin with the literal text "/annex/objects/".
# Real NIfTI .nii.gz files begin with gzip magic bytes — pipe to grep avoids
# null-byte warnings from bash command substitution on binary files.
is_downloaded() {
    ! head -c 14 "$1" 2>/dev/null | grep -q '^/annex/objects'
}

if [[ -n "$SUBJECT_FILTER" ]]; then
    SEARCH_ROOT="$WAND_ROOT/$SUBJECT_FILTER"
    if [[ ! -d "$SEARCH_ROOT" ]]; then
        printf "${RED}ERROR:${RESET} Subject directory not found: %s\n" "$SUBJECT_FILTER"
        exit 1
    fi
else
    SEARCH_ROOT="$WAND_ROOT"
fi

printf "\n"
printf "${BOLD}${CYAN}  Downloaded NIfTI Files${RESET}\n"
printf "${DIM}  Scanning: %s${RESET}\n" "$SEARCH_ROOT"
printf "${DIM}  Size threshold: >= %d MB (edit MIN_SIZE_MB in the script to change)${RESET}\n" "$MIN_SIZE_MB"
printf "\n"
printf "  ${BOLD}%-10s  %-30s  %s${RESET}\n" "SIZE" "SUBJECT / SESSION" "FILENAME"
printf "  ${DIM}%s${RESET}\n" "$(printf '%.0s─' {1..72})"

TOTAL=0
COUNT=0

while IFS= read -r -d '' FILE; do
    if is_downloaded "$FILE"; then
        SIZE_BYTES=$(stat -c '%s' "$FILE")
        # Skip small git-tracked files that were never annexed
        (( SIZE_BYTES < MIN_BYTES )) && continue
        HUMAN=$(du -sh "$FILE" 2>/dev/null | cut -f1)
        REL="${FILE#$WAND_ROOT/}"
        DIR=$(dirname "$REL")
        FNAME=$(basename "$REL")
        if (( SIZE_BYTES >= 500 * 1024 * 1024 )); then
            SIZE_CLR="$RED"
        elif (( SIZE_BYTES >= 50 * 1024 * 1024 )); then
            SIZE_CLR="$YELLOW"
        else
            SIZE_CLR="$GREEN"
        fi
        printf "  ${SIZE_CLR}${BOLD}%-10s${RESET}  ${CYAN}%-30s${RESET}  %s\n" \
            "$HUMAN" "$DIR" "$FNAME"
        TOTAL=$(( TOTAL + SIZE_BYTES ))
        COUNT=$(( COUNT + 1 ))
    fi
done < <(find "$SEARCH_ROOT" -name "*.nii.gz" -print0 | sort -z)

printf "  ${DIM}%s${RESET}\n" "$(printf '%.0s─' {1..72})"

if (( COUNT == 0 )); then
    printf "\n  ${YELLOW}No downloaded NIfTI files found.${RESET}\n\n"
else
    TOTAL_HUMAN=$(echo "$TOTAL" | awk '{
        if ($1 >= 1073741824) printf "%.1f GB", $1/1073741824
        else if ($1 >= 1048576) printf "%.1f MB", $1/1048576
        else printf "%d KB", $1/1024
    }')
    printf "\n  ${GREEN}${BOLD}%d file(s) downloaded${RESET}  ${DIM}│${RESET}  Total on disk: ${BOLD}%s${RESET}\n\n" \
        "$COUNT" "$TOTAL_HUMAN"
fi
