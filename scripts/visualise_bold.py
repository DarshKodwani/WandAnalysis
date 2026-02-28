"""
visualise_bold.py - QC visualisation of a 7T resting-state BOLD scan.

Generates four plots saved to results/<subject>/visualise_bold/:
  1. mean_bold.png       - Mean EPI image (ortho view)
  2. std_bold.png        - Std dev across time (highlights motion/signal variance)
  3. carpet_plot.png     - Carpet plot: voxel signal over time (QC for artefacts)
  4. middle_volume.png   - Axial mosaic of the middle timepoint

Usage:
    python scripts/visualise_bold.py sub-43766
    python scripts/visualise_bold.py sub-43766 --session ses-06
"""

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import nibabel as nib
import numpy as np
from nilearn import plotting, image

# ── Config ────────────────────────────────────────────────────────────────────
REPO_ROOT   = Path(__file__).resolve().parents[1]
WAND_ROOT   = REPO_ROOT / "data" / "WAND"
RESULTS_SUBDIR = "visualise_bold"
DEFAULT_SESSION = "ses-06"


# ── Helpers ───────────────────────────────────────────────────────────────────
def find_bold(subject: str, session: str) -> Path:
    path = WAND_ROOT / subject / session / "func" / f"{subject}_{session}_task-rest_bold.nii.gz"
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
    """Load 4D BOLD and return (img, data, affine)."""
    print(f"  Loading {path.name}  ...", flush=True)
    img  = nib.load(str(path))
    data = img.get_fdata(dtype=np.float32)
    print(f"  Shape: {data.shape}  |  voxel size: {img.header.get_zooms()[:3]}")
    return img, data, img.affine


def save_fig(fig, out_path: Path, title: str):
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="black")
    plt.close(fig)
    print(f"  Saved  → {out_path.relative_to(REPO_ROOT)}")


# ── Plot functions ─────────────────────────────────────────────────────────────
def plot_mean(data, affine, out_dir: Path, subject: str, session: str):
    """Mean image across time — standard EPI reference."""
    mean_data = data.mean(axis=-1)
    mean_img  = nib.Nifti1Image(mean_data, affine)

    nib.save(mean_img, str(out_dir / "mean_bold.nii.gz"))
    print(f"  Saved  → {(out_dir / 'mean_bold.nii.gz').relative_to(REPO_ROOT)}")

    fig, axes = plt.subplots(1, 3, figsize=(15, 5), facecolor="black")
    fig.suptitle(f"{subject}  {session}  —  Mean BOLD", color="white", fontsize=13)

    display = plotting.plot_epi(
        mean_img,
        title="",
        display_mode="ortho",
        cut_coords=(0, 0, 0),
        colorbar=True,
        cmap="gray",
        figure=fig,
        axes=axes[1],
    )
    axes[0].axis("off")
    axes[2].axis("off")
    save_fig(fig, out_dir / "mean_bold.png", "mean")


def plot_std(data, affine, out_dir: Path, subject: str, session: str):
    """Std dev across time — bright regions indicate motion or pulsatile signal."""
    std_data = data.std(axis=-1)
    std_img  = nib.Nifti1Image(std_data, affine)

    nib.save(std_img, str(out_dir / "std_bold.nii.gz"))
    print(f"  Saved  → {(out_dir / 'std_bold.nii.gz').relative_to(REPO_ROOT)}")

    fig = plt.figure(figsize=(14, 5), facecolor="black")
    fig.suptitle(f"{subject}  {session}  —  Temporal Std Dev", color="white", fontsize=13)
    plotting.plot_stat_map(
        std_img,
        display_mode="ortho",
        cut_coords=(0, 0, 0),
        colorbar=True,
        cmap="hot",
        figure=fig,
        title="",
    )
    save_fig(fig, out_dir / "std_bold.png", "std")


def plot_carpet(data, affine, out_dir: Path, subject: str, session: str):
    """Carpet plot: each row = one brain voxel, each column = one timepoint.
    Dark horizontal bands indicate dropout; vertical bands indicate motion spikes."""
    nx, ny, nz, nt = data.shape

    # Flatten spatial dims, keep only voxels above 10% of max signal
    flat  = data.reshape(-1, nt)
    mask  = flat.mean(axis=1) > (0.1 * flat.max())
    flat  = flat[mask]

    # Normalise each voxel to zero mean / unit std for display
    mu    = flat.mean(axis=1, keepdims=True)
    sigma = flat.std(axis=1, keepdims=True)
    sigma[sigma == 0] = 1
    flat_norm = (flat - mu) / sigma

    # Downsample rows if very large (keep ~10 000 voxels for speed)
    max_rows = 10_000
    if flat_norm.shape[0] > max_rows:
        idx = np.linspace(0, flat_norm.shape[0] - 1, max_rows, dtype=int)
        flat_norm = flat_norm[idx]

    fig, ax = plt.subplots(figsize=(16, 8), facecolor="black")
    ax.imshow(flat_norm, aspect="auto", cmap="RdBu_r", vmin=-2, vmax=2,
              interpolation="none")
    ax.set_xlabel("Timepoint", color="white")
    ax.set_ylabel("Brain voxels", color="white")
    ax.tick_params(colors="white")
    for spine in ax.spines.values():
        spine.set_edgecolor("white")
    fig.suptitle(f"{subject}  {session}  —  Carpet Plot  ({nt} timepoints)",
                 color="white", fontsize=13)
    cbar = fig.colorbar(ax.images[0], ax=ax, fraction=0.02, pad=0.01)
    cbar.ax.tick_params(colors="white")
    cbar.set_label("z-score", color="white")
    save_fig(fig, out_dir / "carpet_plot.png", "carpet")


def plot_middle_volume(data, affine, out_dir: Path, subject: str, session: str):
    """Axial mosaic of the middle timepoint."""
    mid_vol  = data[..., data.shape[-1] // 2]
    mid_img  = nib.Nifti1Image(mid_vol, affine)

    fig = plt.figure(figsize=(18, 6), facecolor="black")
    fig.suptitle(f"{subject}  {session}  —  Middle Volume (axial mosaic)",
                 color="white", fontsize=13)
    plotting.plot_epi(
        mid_img,
        display_mode="z",
        cut_coords=8,
        colorbar=False,
        cmap="gray",
        figure=fig,
        title="",
    )
    save_fig(fig, out_dir / "middle_volume.png", "middle volume")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="QC visualisation of a 7T resting-state BOLD scan."
    )
    parser.add_argument("subject", help="Subject ID, e.g. sub-43766")
    parser.add_argument("--session", default=DEFAULT_SESSION,
                        help=f"Session ID (default: {DEFAULT_SESSION})")
    args = parser.parse_args()

    bold_path = find_bold(args.subject, args.session)
    out_dir   = REPO_ROOT / "results" / args.subject / RESULTS_SUBDIR
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n  Subject : {args.subject}")
    print(f"  Session : {args.session}")
    print(f"  Output  : {out_dir.relative_to(REPO_ROOT)}\n")

    img, data, affine = load_bold(bold_path)

    print("\n  [1/4] Mean BOLD image ...")
    plot_mean(data, affine, out_dir, args.subject, args.session)

    print("  [2/4] Temporal std dev ...")
    plot_std(data, affine, out_dir, args.subject, args.session)

    print("  [3/4] Carpet plot ...")
    plot_carpet(data, affine, out_dir, args.subject, args.session)

    print("  [4/4] Middle volume mosaic ...")
    plot_middle_volume(data, affine, out_dir, args.subject, args.session)

    print(f"\n  Done. All plots saved to:  {out_dir.relative_to(REPO_ROOT)}\n")


if __name__ == "__main__":
    main()
