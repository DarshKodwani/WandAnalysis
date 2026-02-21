"""
visualise_t1w.py - Plot orthogonal slices and a mosaic for a T1w NIfTI image.

Usage:
    python scripts/visualise_t1w.py                         # uses default subject
    python scripts/visualise_t1w.py sub-00395               # specific subject
    python scripts/visualise_t1w.py sub-00395 --save        # save PNG instead of display
"""

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import nibabel as nib
import numpy as np
import yaml


def load_config(repo_root: Path) -> dict:
    cfg_path = repo_root / "configs" / "paths.yaml"
    if not cfg_path.exists():
        sys.exit(
            f"ERROR: {cfg_path} not found.\n"
            "Copy configs/paths.example.yaml to configs/paths.yaml and fill in your paths."
        )
    with open(cfg_path) as f:
        return yaml.safe_load(f)


def find_t1w(wand_root: Path, subject: str) -> Path:
    # 7T anat is in ses-03
    t1w = wand_root / subject / "ses-03" / "anat" / f"{subject}_ses-03_T1w.nii.gz"
    if not t1w.exists():
        sys.exit(f"ERROR: T1w not found at {t1w}\nHave you run: gin get-content {subject}/ses-03/anat/")
    # Check it's real data, not a git-annex pointer
    if t1w.stat().st_size < 1000:
        sys.exit(f"ERROR: {t1w} looks like a git-annex pointer ({t1w.stat().st_size} bytes).\nRun: gin get-content {subject}/ses-03/anat/{t1w.name}")
    return t1w


def brain_centre(data: np.ndarray) -> tuple[int, int, int]:
    """Return the centre of mass of non-zero voxels as (x, y, z)."""
    from scipy.ndimage import center_of_mass
    mask = data > np.percentile(data[data > 0], 20)  # rough brain mask
    cx, cy, cz = center_of_mass(mask)
    return int(cx), int(cy), int(cz)


def plot_orthogonal(data: np.ndarray, subject: str, save_path: Path | None = None):
    """Plot sagittal, coronal, axial slices through the centre of mass of the brain."""
    cx, cy, cz = brain_centre(data)

    fig, axes = plt.subplots(1, 3, figsize=(15, 5), facecolor="black")
    fig.suptitle(f"{subject}  —  ses-03 7T T1w", color="white", fontsize=14)

    slices = [
        (data[cx, :, :], "Sagittal"),
        (data[:, cy, :], "Coronal"),
        (data[:, :, cz], "Axial"),
    ]

    for ax, (sl, title) in zip(axes, slices):
        ax.imshow(np.rot90(sl), cmap="gray", origin="lower")
        ax.set_title(title, color="white")
        ax.axis("off")

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight", facecolor="black")
        print(f"Saved: {save_path}")
    else:
        plt.show()


def plot_mosaic(data: np.ndarray, subject: str, save_path: Path | None = None):
    """Plot a mosaic of every 8th axial slice."""
    n_slices = data.shape[2]
    step = 8
    indices = range(0, n_slices, step)
    n_cols = 8
    n_rows = int(np.ceil(len(indices) / n_cols))

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(n_cols * 2, n_rows * 2), facecolor="black")
    fig.suptitle(f"{subject}  —  ses-03 7T T1w  (axial mosaic, every {step} slices)", color="white")
    axes = axes.flatten()

    for i, (ax, z) in enumerate(zip(axes, indices)):
        ax.imshow(np.rot90(data[:, :, z]), cmap="gray", origin="lower")
        ax.set_title(str(z), color="grey", fontsize=7)
        ax.axis("off")
    for ax in axes[i + 1:]:
        ax.axis("off")

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=100, bbox_inches="tight", facecolor="black")
        print(f"Saved: {save_path}")
    else:
        plt.show()


def main():
    parser = argparse.ArgumentParser(description="Visualise a WAND 7T T1w scan.")
    parser.add_argument("subject", nargs="?", default="sub-00395", help="Subject ID (default: sub-00395)")
    parser.add_argument("--save", action="store_true", help="Save PNGs to results/ instead of displaying")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    cfg = load_config(repo_root)
    wand_root = Path(cfg["wand_raw"])
    results_dir = Path(cfg["results"])
    results_dir.mkdir(parents=True, exist_ok=True)

    t1w_path = find_t1w(wand_root, args.subject)
    print(f"Loading {t1w_path} ...")
    img = nib.load(t1w_path)
    data = img.get_fdata()
    print(f"Shape: {data.shape}  |  Voxel size: {img.header.get_zooms()}")

    save_ortho = results_dir / f"{args.subject}_ses-03_T1w_orthogonal.png" if args.save else None
    save_mosaic = results_dir / f"{args.subject}_ses-03_T1w_mosaic.png" if args.save else None

    plot_orthogonal(data, args.subject, save_ortho)
    plot_mosaic(data, args.subject, save_mosaic)


if __name__ == "__main__":
    main()
