"""utils.py - Shared constants and helpers used by all WAND analysis scripts."""

import sys
from pathlib import Path

import nibabel as nib
import numpy as np

# ── Paths ─────────────────────────────────────────────────────────────────────
REPO_ROOT       = Path(__file__).resolve().parents[1]
WAND_ROOT       = REPO_ROOT / "data" / "WAND"
DEFAULT_SESSION = "ses-06"


def is_real_file(path: Path) -> bool:
    """Return True if path exists and is larger than 1 MB (real file, not a git-annex pointer)."""
    return path.exists() and path.stat().st_size > 1024 * 1024


def find_bold(subject: str, session: str) -> Path:
    """Locate and validate the BOLD file for a subject/session.
    Exits with a clear error message if the file is missing or not yet downloaded."""
    path = WAND_ROOT / subject / session / "func" / \
           f"{subject}_{session}_task-rest_bold.nii.gz"
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
