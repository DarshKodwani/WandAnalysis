"""utils.py - Shared constants and helpers for dataset-aware analysis scripts."""

import sys
from pathlib import Path
from typing import Any

import nibabel as nib
import numpy as np
import yaml

# ── Paths ─────────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parents[1]
DATASET_CONFIG_PATH = REPO_ROOT / "configs" / "dataset.yaml"


def _load_dataset_config() -> dict[str, Any]:
    if not DATASET_CONFIG_PATH.exists():
        return {}
    with open(DATASET_CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    if not isinstance(cfg, dict):
        raise ValueError(f"Dataset config must be a mapping: {DATASET_CONFIG_PATH}")
    return cfg


DATASET_CONFIG = _load_dataset_config()
DATASET_NAME = str(DATASET_CONFIG.get("name", "WAND"))
DATASET_ROOT = REPO_ROOT / str(DATASET_CONFIG.get("data_root", "data/WAND"))
RESULTS_ROOT = REPO_ROOT / str(DATASET_CONFIG.get("results_root", "results"))
DEFAULT_SESSION = str(DATASET_CONFIG.get("default_session", "ses-06"))
DEFAULT_TASK = str(DATASET_CONFIG.get("default_task", "rest"))
MRIQC_ANALYSIS_DIR = DATASET_ROOT / str(DATASET_CONFIG.get("mriqc_analysis_relpath", "derivatives/mriqc/analysis"))
FIELD_STRENGTH_SESSIONS = DATASET_CONFIG.get("field_strength_sessions", {"3t": "ses-03", "7t": "ses-06"})

# Backward-compatible alias for scripts/tests still using WAND_ROOT.
WAND_ROOT = DATASET_ROOT


def session_for_field_strength(field_strength: str) -> str:
    session = FIELD_STRENGTH_SESSIONS.get(field_strength.lower())
    if session is None:
        raise KeyError(f"No session mapping found for field strength: {field_strength}")
    return str(session)


def bold_path(subject: str, session: str, task: str = DEFAULT_TASK) -> Path:
    return DATASET_ROOT / subject / session / "func" / f"{subject}_{session}_task-{task}_bold.nii.gz"


def is_real_file(path: Path) -> bool:
    """Return True if path exists and is larger than 1 MB (real file, not a git-annex pointer)."""
    return path.exists() and path.stat().st_size > 1024 * 1024


def find_bold(subject: str, session: str, task: str = DEFAULT_TASK) -> Path:
    """Locate and validate the BOLD file for a subject/session.
    Exits with a clear error message if the file is missing or not yet downloaded."""
    path = bold_path(subject, session, task)
    if not path.exists():
        sys.exit(
            f"ERROR: BOLD file not found:\n  {path}\n"
            f"Run: bash scripts/download.sh {subject} {session} func"
        )
    if path.stat().st_size < 1024 * 1024:
        sys.exit(
            f"ERROR: {path.name} looks like a git-annex pointer "
            f"({path.stat().st_size} bytes).\n"
            f"Run: bash scripts/download.sh {subject} {session} func {path.name}"
        )
    return path


def load_bold(path: Path):
    """Load a 4D BOLD NIfTI and return (img, data_float32, affine)."""
    print(f"  Loading {path.name} ...", flush=True)
    img  = nib.load(str(path))
    data = img.get_fdata(dtype=np.float32)
    print(f"  Shape: {data.shape}  |  voxel size: {img.header.get_zooms()[:3]}")
    return img, data, img.affine
