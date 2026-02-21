#!/usr/bin/env bash
# fetch_subject.sh - Download a single subject's data from the WAND GIN repo.
# Usage:
#   bash scripts/fetch_subject.sh sub-00395              # fetch all modalities
#   bash scripts/fetch_subject.sh sub-00395 anat         # fetch one session folder (e.g. anat, func, dwi)
#
# Note: WAND subject IDs are 5-digit numbers e.g. sub-00395, not sub-001.
# Check data/WAND/participants.tsv for the full subject list.
#
# Prerequisites: wand conda env active with gin CLI installed (bash scripts/setup_gin.sh)

set -e

SUBJECT="${1:?Usage: bash scripts/fetch_subject.sh <subject_id> [modality]}"
MODALITY="${2:-}"  # optional: anat, func, dwi, etc.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG="$REPO_ROOT/configs/paths.yaml"

if [[ ! -f "$CONFIG" ]]; then
    echo "ERROR: $CONFIG not found. Copy configs/paths.example.yaml to configs/paths.yaml and fill in your paths."
    exit 1
fi

# Parse wand_raw (GIN clone root) from YAML
WAND_RAW=$(python3 -c "import yaml; print(yaml.safe_load(open('$CONFIG'))['wand_raw'])")

if [[ ! -d "$WAND_RAW/.git" ]]; then
    echo "ERROR: $WAND_RAW does not look like a GIN repo. Run 'gin get CUBRIC/WAND' there first."
    exit 1
fi

cd "$WAND_RAW"

if [[ -n "$MODALITY" ]]; then
    TARGET="$SUBJECT/*/$MODALITY"
    echo "Fetching $SUBJECT/$MODALITY ..."
else
    TARGET="$SUBJECT"
    echo "Fetching all data for $SUBJECT ..."
fi

gin get-content "$TARGET"

echo "Done: data available at $WAND_RAW/$TARGET"
