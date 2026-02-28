"""
slice_qc.py - Slice-based fMRI QC, equivalent to the standard MATLAB QC script.

For each slice at each timepoint, computes the mean signal intensity, then
produces 5 plots saved to results/<subject>/slice_qc/:

  1. slicemean_raw.png       - Mean signal per slice per volume (raw heatmap)
  2. slicemean_mean.png      - Mean signal per slice averaged across time
  3. slicemean_std.png       - Std dev per slice across time
  4. slicemean_corrected.png - Slice-mean-corrected heatmap (detrended)
  5. slicemean_fft.png       - FFT of the corrected timeseries per slice

Usage:
    python scripts/slice_qc.py sub-43766
    python scripts/slice_qc.py sub-43766 --session ses-06
"""

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import nibabel as nib
import numpy as np

# ── Config ────────────────────────────────────────────────────────────────────
REPO_ROOT       = Path(__file__).resolve().parents[1]
WAND_ROOT       = REPO_ROOT / "data" / "WAND"
RESULTS_SUBDIR  = "slice_qc"
DEFAULT_SESSION = "ses-06"


# ── Helpers ───────────────────────────────────────────────────────────────────
def find_bold(subject: str, session: str) -> Path:
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
    print(f"  Loading {path.name} ...", flush=True)
    img  = nib.load(str(path))
    data = img.get_fdata(dtype=np.float32)
    print(f"  Shape: {data.shape}  |  voxel size: {img.header.get_zooms()[:3]}")
    return data


def save_fig(fig, out_path: Path):
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  Saved  → {out_path.relative_to(REPO_ROOT)}")


# ── Core computation ──────────────────────────────────────────────────────────
def compute_slicemean(data: np.ndarray) -> np.ndarray:
    """
    Returns slicemean[n_volumes, n_slices]:
    mean signal across all x,y voxels in each slice at each timepoint.
    """
    # data shape: [x, y, z, t] → mean over x and y axes → [z, t] → transpose [t, z]
    return data.mean(axis=(0, 1)).T  # [volumes × slices]


def mean_correct(slicemean: np.ndarray) -> np.ndarray:
    """
    Subtract each slice's mean across time (mean-centre per slice).
    slicemean shape: [volumes × slices]  →  transpose to [slices × volumes],
    correct, return [slices × volumes].
    """
    sm_t = slicemean.T  # [slices × volumes]
    return sm_t - sm_t.mean(axis=1, keepdims=True)


# ── Plot functions ─────────────────────────────────────────────────────────────
def plot_raw(slicemean: np.ndarray, out_dir: Path, subject: str, session: str):
    """Heatmap of raw slice means — [slices × volumes]."""
    fig, ax = plt.subplots(figsize=(14, 5))
    im = ax.imshow(slicemean.T, aspect="auto", cmap="viridis",
                   interpolation="none")
    ax.set_title(f"{subject}  {session}  —  Signal Intensity (raw)", fontsize=12)
    ax.set_xlabel("Volume (timepoint)")
    ax.set_ylabel("Slice")
    fig.colorbar(im, ax=ax, label="Mean signal")
    save_fig(fig, out_dir / "slicemean_raw.png")


def plot_mean(slicemean: np.ndarray, out_dir: Path, subject: str, session: str):
    """Mean signal per slice averaged across all timepoints."""
    mean_per_slice = slicemean.mean(axis=0)  # [slices]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(mean_per_slice, color="steelblue", linewidth=1.5)
    ax.set_title(f"{subject}  {session}  —  Mean Signal per Slice", fontsize=12)
    ax.set_xlabel("Slice")
    ax.set_ylabel("Mean signal")
    ax.grid(True, alpha=0.3)
    save_fig(fig, out_dir / "slicemean_mean.png")


def plot_std(slicemean: np.ndarray, out_dir: Path, subject: str, session: str):
    """Std dev of signal per slice across time."""
    std_per_slice = slicemean.std(axis=0)  # [slices]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(std_per_slice, color="tomato", linewidth=1.5)
    ax.set_title(f"{subject}  {session}  —  Std Dev per Slice (across time)",
                 fontsize=12)
    ax.set_xlabel("Slice")
    ax.set_ylabel("Std dev")
    ax.grid(True, alpha=0.3)
    save_fig(fig, out_dir / "slicemean_std.png")


def plot_corrected(slicemean_norm: np.ndarray, out_dir: Path,
                   subject: str, session: str):
    """Heatmap of slice-mean-corrected signal — [slices × volumes]."""
    fig, ax = plt.subplots(figsize=(14, 5))
    vmax = np.percentile(np.abs(slicemean_norm), 99)
    im = ax.imshow(slicemean_norm, aspect="auto", cmap="RdBu_r",
                   vmin=-vmax, vmax=vmax, interpolation="none")
    ax.set_title(f"{subject}  {session}  —  Signal Intensity (slice-mean corrected)",
                 fontsize=12)
    ax.set_xlabel("Volume (timepoint)")
    ax.set_ylabel("Slice")
    fig.colorbar(im, ax=ax, label="Signal (mean-corrected)")
    save_fig(fig, out_dir / "slicemean_corrected.png")


def plot_fft(slicemean_norm: np.ndarray, out_dir: Path,
             subject: str, session: str):
    """
    FFT of mean-corrected timeseries per slice.
    slicemean_norm: [slices × volumes]
    Shows frequency up to 50 cycles (x-axis = number of cycles in timecourse).
    """
    # FFT along time axis (axis=1), take absolute value
    fft_result = np.abs(np.fft.fft(slicemean_norm, axis=1))

    # Drop DC (index 0) and mirror; keep up to 50 cycles as in MATLAB script
    n_cycles = min(50, fft_result.shape[1] - 1)
    fft_plot = fft_result[:, 1:n_cycles + 1]

    fig, ax = plt.subplots(figsize=(14, 5))
    im = ax.imshow(fft_plot, aspect="auto", cmap="hot",
                   interpolation="none")
    ax.set_title(f"{subject}  {session}  —  FFT of Corrected Signal",
                 fontsize=12)
    ax.set_xlabel("Number of cycles in timecourse")
    ax.set_ylabel("Slice")
    fig.colorbar(im, ax=ax, label="FFT magnitude")
    save_fig(fig, out_dir / "slicemean_fft.png")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Slice-based fMRI QC (Python equivalent of standard MATLAB QC script)."
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

    data = load_bold(bold_path)

    print("\n  Computing slice means ...", flush=True)
    slicemean      = compute_slicemean(data)        # [volumes × slices]
    slicemean_norm = mean_correct(slicemean)        # [slices × volumes]

    np.save(out_dir / "slicemean.npy", slicemean)
    print(f"  Saved  → {(out_dir / 'slicemean.npy').relative_to(REPO_ROOT)}")

    print("\n  [1/5] Raw signal heatmap ...")
    plot_raw(slicemean, out_dir, args.subject, args.session)

    print("  [2/5] Mean per slice ...")
    plot_mean(slicemean, out_dir, args.subject, args.session)

    print("  [3/5] Std dev per slice ...")
    plot_std(slicemean, out_dir, args.subject, args.session)

    print("  [4/5] Slice-mean-corrected heatmap ...")
    plot_corrected(slicemean_norm, out_dir, args.subject, args.session)

    print("  [5/5] FFT of corrected signal ...")
    plot_fft(slicemean_norm, out_dir, args.subject, args.session)

    print(f"\n  Done. All plots saved to:  {out_dir.relative_to(REPO_ROOT)}\n")


if __name__ == "__main__":
    main()
