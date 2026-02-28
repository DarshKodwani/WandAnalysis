"""
iqm.py - Image Quality Metrics for 7T resting-state BOLD data.

Computes four no-reference IQMs (following MRIQC conventions) and saves:

  Scalar summaries  →  iqm.json
  ─────────────────────────────────────────────────────────────────────────────
    tsnr_median      Median temporal SNR across brain voxels
    cov_median       Median coefficient of variation across brain voxels
    dvars_median     Median DVARS value across all frames
    dvars_n_spikes   Number of frames where DVARS > 1.5 × median
    gcor             Global correlation (mean pairwise voxel correlation)
    n_voxels_mask    Number of voxels in the brain mask

  Spatial maps  (3D NIfTI + PNG)
  ─────────────────────────────────────────────────────────────────────────────
    tsnr_map.nii.gz  tSNR at every brain voxel
    cov_map.nii.gz   CoV at every brain voxel
    tsnr_map.png     Ortho montage of tSNR map
    cov_map.png      Ortho montage of CoV map

  Temporal timeseries
  ─────────────────────────────────────────────────────────────────────────────
    dvars.tsv        DVARS value per volume (first entry is NaN — no prior frame)
    dvars_plot.png   DVARS timeseries with spike threshold marked

Usage:
    python scripts/iqm.py sub-64927
    python scripts/iqm.py sub-64927 --session ses-06
"""

import argparse
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import nibabel as nib
import numpy as np
from nilearn import plotting

# ── Config ────────────────────────────────────────────────────────────────────
REPO_ROOT       = Path(__file__).resolve().parents[1]
WAND_ROOT       = REPO_ROOT / "data" / "WAND"
RESULTS_SUBDIR  = "iqm"
DEFAULT_SESSION = "ses-06"

# DVARS spike threshold multiplier (frames > SPIKE_FACTOR × median DVARS flagged)
SPIKE_FACTOR = 1.5
# Brain mask threshold: voxels with mean > MASK_PERCENTILE-th percentile × MASK_FRAC
MASK_PERCENTILE = 95
MASK_FRAC       = 0.1


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
    """Load 4D BOLD and return (img, data_float32, affine)."""
    print(f"  Loading {path.name} ...", flush=True)
    img  = nib.load(str(path))
    data = img.get_fdata(dtype=np.float32)
    print(f"  Shape : {data.shape}  |  voxel size : {img.header.get_zooms()[:3]}")
    return img, data, img.affine


def make_brain_mask(data: np.ndarray) -> np.ndarray:
    """
    Simple intensity-based brain mask.

    Voxels whose mean signal across time exceeds MASK_FRAC × the
    MASK_PERCENTILE-th percentile of the whole-volume mean are included.
    This reliably separates brain tissue from air background without
    requiring FSL or ANTs.

    Returns boolean array of shape (x, y, z).
    """
    mean_vol = data.mean(axis=-1)                          # (x, y, z)
    thresh   = MASK_FRAC * np.percentile(mean_vol, MASK_PERCENTILE)
    mask     = mean_vol > thresh
    return mask


# ── Metric computations ───────────────────────────────────────────────────────
def compute_tsnr(data: np.ndarray, mask: np.ndarray):
    """
    Temporal SNR = mean(signal) / std(signal) computed voxel-wise.

    A higher value means the stable signal component is large relative
    to temporal fluctuations.  Reported as the median over brain voxels.

    Returns:
        tsnr_map   : (x, y, z) float32 array — 0 outside mask
        tsnr_median: float scalar
    """
    mean_t = data.mean(axis=-1)                            # (x, y, z)
    std_t  = data.std(axis=-1, ddof=1)

    # Avoid division by zero in background
    std_t_safe = np.where(std_t > 0, std_t, np.inf)
    tsnr_map   = np.where(mask, mean_t / std_t_safe, 0.0).astype(np.float32)
    tsnr_median = float(np.median(tsnr_map[mask]))
    return tsnr_map, tsnr_median


def compute_cov(data: np.ndarray, mask: np.ndarray):
    """
    Coefficient of Variation = std(signal) / mean(signal) computed voxel-wise.

    CoV is the inverse of tSNR.  A lower value means greater temporal
    stability relative to the signal magnitude.  Reported as the median
    over brain voxels (×100 to express as a percentage).

    Returns:
        cov_map   : (x, y, z) float32 array — 0 outside mask
        cov_median: float scalar (percentage)
    """
    mean_t = data.mean(axis=-1)
    std_t  = data.std(axis=-1, ddof=1)

    mean_safe = np.where(mean_t > 0, mean_t, np.inf)
    cov_map   = np.where(mask, 100.0 * std_t / mean_safe, 0.0).astype(np.float32)
    cov_median = float(np.median(cov_map[mask]))
    return cov_map, cov_median


def compute_dvars(data: np.ndarray, mask: np.ndarray):
    """
    DVARS = RMS of the frame-to-frame signal difference across brain voxels.

    Following Power et al. (2012).  Signal is first scaled so that the
    grand mean across brain voxels equals 1000 (standard convention),
    making DVARS units comparable across subjects and sessions.

    Returns:
        dvars       : 1-D array of length n_vols (first entry is NaN)
        dvars_median: float — median of non-NaN values
        n_spikes    : int   — frames where DVARS > SPIKE_FACTOR × median
    """
    brain      = data[mask]                                # (n_voxels, n_vols)
    grand_mean = brain.mean()
    if grand_mean > 0:
        brain = brain * (1000.0 / grand_mean)

    diff      = np.diff(brain, axis=-1)                   # (n_voxels, n_vols-1)
    dvars_val = np.sqrt((diff ** 2).mean(axis=0))         # (n_vols-1,)
    dvars     = np.concatenate([[np.nan], dvars_val])     # prepend NaN for vol 0

    dvars_median  = float(np.nanmedian(dvars))
    spike_thresh  = SPIKE_FACTOR * dvars_median
    n_spikes      = int(np.sum(dvars_val > spike_thresh))
    return dvars, dvars_median, n_spikes


def compute_gcor(data: np.ndarray, mask: np.ndarray) -> float:
    """
    Global Correlation (GCOR) — following Saad et al. (2013).

    Each brain-voxel timeseries is demeaned and normalised to unit
    variance.  The mean of all such timeseries is computed; GCOR is the
    variance of that mean timeseries — equivalent to the average of all
    pairwise inter-voxel correlations.

    A high GCOR (> ~0.1) suggests widespread correlated noise
    (e.g. global signal drift, respiratory artefact).

    Returns:
        gcor: float in range [0, 1]
    """
    brain = data[mask].astype(np.float64)                 # (n_voxels, n_vols)

    # Demean and normalise each voxel timeseries to zero mean, unit variance
    brain -= brain.mean(axis=-1, keepdims=True)
    std    = brain.std(axis=-1, ddof=1, keepdims=True)
    std[std == 0] = 1.0                                   # avoid divide-by-zero
    brain /= std

    g_u  = brain.mean(axis=0)                             # mean unit-variance TS
    gcor = float(g_u.var(ddof=1))                        # variance = mean r
    return gcor


# ── Plotting ──────────────────────────────────────────────────────────────────
def plot_map(nii_path: Path, out_path: Path, title: str, cmap: str,
             affine, subject: str, session: str):
    """Ortho montage of a 3D NIfTI map."""
    img = nib.load(str(nii_path))
    fig, axes = plt.subplots(1, 3, figsize=(15, 4), facecolor="black")
    fig.suptitle(f"{title}  |  {subject}  {session}", color="white", fontsize=12)

    display = plotting.plot_stat_map(
        img, display_mode="ortho", colorbar=True, cmap=cmap,
        figure=fig, axes=axes[1],
        title="", black_bg=True, annotate=False
    )
    # Remove the empty side axes
    axes[0].set_visible(False)
    axes[2].set_visible(False)

    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="black")
    plt.close(fig)
    print(f"  Saved  → {out_path.relative_to(REPO_ROOT)}")


def plot_tsnr(nii_path: Path, out_path: Path, subject: str, session: str):
    """Ortho montage of tSNR map with a warm colourmap."""
    img = nib.load(str(nii_path))

    fig = plt.figure(figsize=(11, 3.5), facecolor="black")
    display = plotting.plot_stat_map(
        img, display_mode="ortho", colorbar=True, cmap="hot",
        figure=fig, title=f"tSNR map  |  {subject}  {session}",
        black_bg=True, annotate=True
    )
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="black")
    plt.close(fig)
    print(f"  Saved  → {out_path.relative_to(REPO_ROOT)}")


def plot_cov(nii_path: Path, out_path: Path, subject: str, session: str):
    """Ortho montage of CoV map (%) with a cool colourmap."""
    img = nib.load(str(nii_path))

    fig = plt.figure(figsize=(11, 3.5), facecolor="black")
    display = plotting.plot_stat_map(
        img, display_mode="ortho", colorbar=True, cmap="cool",
        figure=fig, title=f"CoV map (%)  |  {subject}  {session}",
        black_bg=True, annotate=True
    )
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="black")
    plt.close(fig)
    print(f"  Saved  → {out_path.relative_to(REPO_ROOT)}")


def plot_dvars(dvars: np.ndarray, dvars_median: float, n_spikes: int,
               out_path: Path, subject: str, session: str):
    """DVARS timeseries with spike threshold line and flagged frames."""
    spike_thresh = SPIKE_FACTOR * dvars_median
    n_vols       = len(dvars)
    t            = np.arange(n_vols)

    fig, ax = plt.subplots(figsize=(14, 4), facecolor="black")
    ax.set_facecolor("black")

    # Shade spike frames
    spike_frames = np.where(dvars > spike_thresh)[0]
    for sf in spike_frames:
        ax.axvspan(sf - 0.5, sf + 0.5, color="red", alpha=0.3, linewidth=0)

    ax.plot(t, dvars, color="#00bfff", linewidth=0.9, label="DVARS")
    ax.axhline(dvars_median,  color="lime",   linewidth=1.2, linestyle="--",
               label=f"Median ({dvars_median:.1f})")
    ax.axhline(spike_thresh, color="orange", linewidth=1.2, linestyle=":",
               label=f"Spike threshold ×{SPIKE_FACTOR} ({spike_thresh:.1f})")

    ax.set_xlabel("Volume", color="white")
    ax.set_ylabel("DVARS", color="white")
    ax.tick_params(colors="white")
    for spine in ax.spines.values():
        spine.set_edgecolor("#444444")
    ax.set_title(
        f"DVARS  |  {subject}  {session}"
        f"  —  median={dvars_median:.1f},  spikes={n_spikes}",
        color="white", fontsize=11
    )
    ax.legend(facecolor="#222222", edgecolor="#444444",
              labelcolor="white", fontsize=9)

    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="black")
    plt.close(fig)
    print(f"  Saved  → {out_path.relative_to(REPO_ROOT)}")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Compute Image Quality Metrics (IQMs) for a 7T resting-state BOLD scan."
    )
    parser.add_argument("subject", help="Subject ID, e.g. sub-64927")
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

    # ── Brain mask ────────────────────────────────────────────────────────────
    print("  Building brain mask ...", flush=True)
    mask = make_brain_mask(data)
    n_voxels = int(mask.sum())
    print(f"  Mask    : {n_voxels:,} voxels")

    # ── tSNR ──────────────────────────────────────────────────────────────────
    print("\n  [1/4] Computing tSNR ...", flush=True)
    tsnr_map, tsnr_median = compute_tsnr(data, mask)
    tsnr_nii = nib.Nifti1Image(tsnr_map, affine, img.header)
    nib.save(tsnr_nii, str(out_dir / "tsnr_map.nii.gz"))
    print(f"  Saved  → {(out_dir / 'tsnr_map.nii.gz').relative_to(REPO_ROOT)}")
    print(f"  tSNR median = {tsnr_median:.2f}")
    plot_tsnr(out_dir / "tsnr_map.nii.gz", out_dir / "tsnr_map.png",
              args.subject, args.session)

    # ── CoV ───────────────────────────────────────────────────────────────────
    print("\n  [2/4] Computing CoV ...", flush=True)
    cov_map, cov_median = compute_cov(data, mask)
    cov_nii = nib.Nifti1Image(cov_map, affine, img.header)
    nib.save(cov_nii, str(out_dir / "cov_map.nii.gz"))
    print(f"  Saved  → {(out_dir / 'cov_map.nii.gz').relative_to(REPO_ROOT)}")
    print(f"  CoV median = {cov_median:.2f}%")
    plot_cov(out_dir / "cov_map.nii.gz", out_dir / "cov_map.png",
             args.subject, args.session)

    # ── DVARS ─────────────────────────────────────────────────────────────────
    print("\n  [3/4] Computing DVARS ...", flush=True)
    dvars, dvars_median, n_spikes = compute_dvars(data, mask)
    tsv_path = out_dir / "dvars.tsv"
    np.savetxt(str(tsv_path), dvars, fmt="%.4f", header="dvars", comments="")
    print(f"  Saved  → {tsv_path.relative_to(REPO_ROOT)}")
    print(f"  DVARS median = {dvars_median:.2f},  spikes = {n_spikes}")
    plot_dvars(dvars, dvars_median, n_spikes,
               out_dir / "dvars_plot.png", args.subject, args.session)

    # ── GCOR ──────────────────────────────────────────────────────────────────
    print("\n  [4/4] Computing GCOR ...", flush=True)
    gcor = compute_gcor(data, mask)
    print(f"  GCOR = {gcor:.4f}")

    # ── Save JSON summary ─────────────────────────────────────────────────────
    iqm = {
        "subject":        args.subject,
        "session":        args.session,
        "n_voxels_mask":  n_voxels,
        "tsnr_median":    round(tsnr_median, 4),
        "cov_median":     round(cov_median, 4),
        "dvars_median":   round(dvars_median, 4),
        "dvars_n_spikes": n_spikes,
        "dvars_spike_threshold_factor": SPIKE_FACTOR,
        "gcor":           round(gcor, 6),
    }
    json_path = out_dir / "iqm.json"
    with open(json_path, "w") as f:
        json.dump(iqm, f, indent=2)
    print(f"\n  Saved  → {json_path.relative_to(REPO_ROOT)}")

    print(f"\n  ── IQM Summary ──────────────────────────────────────")
    print(f"  tSNR (median)  : {tsnr_median:>8.2f}")
    print(f"  CoV  (median)  : {cov_median:>8.2f} %")
    print(f"  DVARS (median) : {dvars_median:>8.2f}")
    print(f"  DVARS spikes   : {n_spikes:>8d}")
    print(f"  GCOR           : {gcor:>8.4f}")
    print(f"  ─────────────────────────────────────────────────────\n")
    print(f"  Done. All outputs saved to:  {out_dir.relative_to(REPO_ROOT)}\n")


if __name__ == "__main__":
    main()
