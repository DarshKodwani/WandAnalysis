#!/usr/bin/env bash
# fetch_subject.sh - Download a single subject's data from the WAND dataset.
# Usage: bash scripts/fetch_subject.sh sub-001

set -e

SUBJECT="${1:?Usage: bash scripts/fetch_subject.sh <subject_id>}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG="$REPO_ROOT/configs/paths.yaml"

if [[ ! -f "$CONFIG" ]]; then
    echo "ERROR: $CONFIG not found. Copy configs/paths.example.yaml to configs/paths.yaml and fill in your paths."
    exit 1
fi

# Parse wand_raw path from YAML (requires python3)
WAND_RAW=$(python3 -c "import yaml; print(yaml.safe_load(open('$CONFIG'))['wand_raw'])")

echo "Fetching $SUBJECT from $WAND_RAW ..."
datalad get "$WAND_RAW/$SUBJECT"

echo "Done: $SUBJECT data available at $WAND_RAW/$SUBJECT"
