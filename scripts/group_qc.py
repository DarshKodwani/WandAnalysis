"""
group_qc.py - Group-level QC analysis across all WAND subjects.

Loads the per-subject iqm.json files from results/ and the official MRIQC
TSV from the WAND derivatives folder, then produces summary plots to help
identify the best subjects for fMRI analysis.

Current plots
─────────────
  tsnr_histogram.png          Histogram of our raw tSNR across all subjects.
  tsnr_histogram_mriqc.png    Histogram of MRIQC tSNR (motion-corrected data).
  tsnr_comparison.png         Side-by-side comparison of both distributions.

Usage
─────
    python scripts/group_qc.py              # all subjects
    python scripts/group_qc.py --show       # also open plots interactively
"""

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# ── Paths ─────────────────────────────────────────────────────────────────────
REPO_ROOT   = Path(__file__).resolve().parents[1]
RESULTS_DIR = REPO_ROOT / "results"
OUT_DIR     = RESULTS_DIR / "group"
MRIQC_TSV   = REPO_ROOT / "data" / "WAND" / "derivatives" / "mriqc" / "analysis" / "ses-06_task-rest_bold.tsv"


# ── Data loading ──────────────────────────────────────────────────────────────

def load_all_iqm() -> list[dict]:
    """Read every iqm.json under results/ and return a list of dicts."""
    records = []
    for iqm_path in sorted(RESULTS_DIR.glob("sub-*/iqm/iqm.json")):
        with open(iqm_path) as f:
            records.append(json.load(f))
    if not records:
        raise FileNotFoundError(
            f"No iqm.json files found under {RESULTS_DIR}. "
            "Have you run batch_qc.py first?"
        )
    return records


# ── MRIQC data loading ───────────────────────────────────────────────────────

def load_mriqc_tsnr() -> tuple[np.ndarray, list[str]]:
    """Read tSNR values from the official MRIQC TSV for ses-06 resting-state BOLD."""
    if not MRIQC_TSV.exists():
        raise FileNotFoundError(f"MRIQC TSV not found: {MRIQC_TSV}")
    df = pd.read_csv(MRIQC_TSV, sep="\t")
    # extract subject IDs (strip session/task suffix)
    subjects = df["bids_name"].str.split("_ses").str[0].tolist()
    tsnr = df["tsnr"].values.astype(float)
    return tsnr, subjects


# ── Plots ─────────────────────────────────────────────────────────────────────

def plot_tsnr_histogram(records: list[dict], out_dir: Path, show: bool = False):
    """Histogram of our raw (no motion correction) tSNR across all subjects."""
    tsnr_values = np.array([r["tsnr_median"] for r in records])
    fig, ax = plt.subplots(figsize=(10, 5))
    fig.suptitle("Temporal SNR (tSNR) — our pipeline (raw BOLD)",
                 fontsize=14, fontweight="bold")
    _tsnr_hist_ax(ax, tsnr_values,
                  title="Our pipeline  (raw BOLD, no motion correction)",
                  subtitle="Median tSNR  [raw]")
    fig.tight_layout()
    out_path = out_dir / "tsnr_histogram.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"Saved: {out_path}")
    if show:
        plt.show()
    plt.close(fig)


def _tsnr_hist_ax(ax, tsnr_values, title, subtitle):
    """Shared helper: draw a colour-coded tSNR histogram on a given Axes."""
    n = len(tsnr_values)
    q25, q50, q75 = np.percentile(tsnr_values, [25, 50, 75])
    mean_val = tsnr_values.mean()

    counts, bin_edges, patches = ax.hist(
        tsnr_values, bins=20,
        color="#4C72B0", edgecolor="white", linewidth=0.6, zorder=2,
    )
    for patch, left_edge in zip(patches, bin_edges[:-1]):
        if left_edge >= q75:
            patch.set_facecolor("#2ca02c")
        elif left_edge >= q50:
            patch.set_facecolor("#4C72B0")
        elif left_edge >= q25:
            patch.set_facecolor("#ff7f0e")
        else:
            patch.set_facecolor("#d62728")

    for val, label, ls in [
        (q25, f"Q1={q25:.1f}", "--"),
        (q50, f"Median={q50:.1f}", "-"),
        (q75, f"Q3={q75:.1f}", "--"),
    ]:
        ax.axvline(val, color="black", linestyle=ls, linewidth=1.1, alpha=0.7, zorder=3)
        ax.text(val, ax.get_ylim()[1] * 0.97, label,
                ha="center", va="top", fontsize=7.5, rotation=90, color="black", alpha=0.8)

    ax.axvline(mean_val, color="#9467bd", linestyle=":", linewidth=1.3, zorder=3)
    ax.text(mean_val, ax.get_ylim()[1] * 0.80, f"Mean={mean_val:.1f}",
            ha="center", va="top", fontsize=7.5, color="#9467bd")

    ax.set_title(
        f"{title}\n"
        f"n={n}  min={tsnr_values.min():.1f}  max={tsnr_values.max():.1f}  "
        f"mean={mean_val:.1f}  median={q50:.1f}  SD={tsnr_values.std():.1f}",
        fontsize=9,
    )
    ax.set_xlabel(subtitle, fontsize=11)
    ax.set_ylabel("Number of subjects", fontsize=10)
    ax.set_xlim(left=0)
    ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
    ax.grid(axis="y", linestyle="--", alpha=0.4, zorder=1)
    ax.set_axisbelow(True)

    from matplotlib.patches import Patch
    ax.legend(handles=[
        Patch(facecolor="#2ca02c", label=f"Top quartile  (≥{q75:.1f})"),
        Patch(facecolor="#4C72B0", label=f"Upper-middle  ({q50:.1f}–{q75:.1f})"),
        Patch(facecolor="#ff7f0e", label=f"Lower-middle  ({q25:.1f}–{q50:.1f})"),
        Patch(facecolor="#d62728", label=f"Bottom quartile  (<{q25:.1f})"),
    ], fontsize=7.5, loc="upper right")


def plot_mriqc_tsnr_histogram(tsnr_values, out_dir: Path, show: bool = False):
    """Standalone histogram of MRIQC tSNR values."""
    fig, ax = plt.subplots(figsize=(10, 5))
    fig.suptitle("Temporal SNR (tSNR) — MRIQC / motion-corrected data",
                 fontsize=14, fontweight="bold")
    _tsnr_hist_ax(ax, tsnr_values,
                  title="MRIQC tSNR  (ses-06 resting-state BOLD)",
                  subtitle="Median tSNR  [MRIQC]")
    fig.tight_layout()
    out_path = out_dir / "tsnr_histogram_mriqc.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"Saved: {out_path}")
    if show:
        plt.show()
    plt.close(fig)


def plot_tsnr_comparison(raw_values, mriqc_values, out_dir: Path, show: bool = False):
    """Side-by-side comparison of raw vs MRIQC tSNR distributions."""
    fig, axes = plt.subplots(1, 2, figsize=(18, 5), sharey=False)
    fig.suptitle(
        "Temporal SNR comparison: Raw (no motion correction)  vs  MRIQC (motion-corrected)",
        fontsize=13, fontweight="bold",
    )

    _tsnr_hist_ax(axes[0], raw_values,
                  title="Our pipeline  (raw BOLD)",
                  subtitle="Median tSNR  [raw]")
    _tsnr_hist_ax(axes[1], mriqc_values,
                  title="MRIQC  (motion-corrected BOLD)",
                  subtitle="Median tSNR  [MRIQC]")

    # align x-axes for fair visual comparison
    xmax = max(axes[0].get_xlim()[1], axes[1].get_xlim()[1])
    axes[0].set_xlim(0, xmax)
    axes[1].set_xlim(0, xmax)

    # annotate the mean shift
    delta = mriqc_values.mean() - raw_values.mean()
    fig.text(0.5, -0.01,
             f"Mean tSNR improvement with motion correction: +{delta:.1f} "
             f"({delta / raw_values.mean() * 100:.0f}%)",
             ha="center", fontsize=10, color="#2ca02c", fontweight="bold")

    fig.tight_layout()
    out_path = out_dir / "tsnr_comparison.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"Saved: {out_path}")
    if show:
        plt.show()
    plt.close(fig)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Group-level QC analysis for WAND subjects.")
    parser.add_argument("--show", action="store_true", help="Open plots interactively after saving.")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── our raw IQMs ──────────────────────────────────────────────────────────
    print("Loading our IQM data …")
    records = load_all_iqm()
    raw_tsnr = np.array([r["tsnr_median"] for r in records])
    print(f"  Found {len(records)} subjects.")

    print("Plotting raw tSNR histogram …")
    plot_tsnr_histogram(records, OUT_DIR, show=args.show)

    # ── MRIQC tSNR ────────────────────────────────────────────────────────────
    print("Loading MRIQC tSNR data …")
    mriqc_tsnr, mriqc_subs = load_mriqc_tsnr()
    print(f"  Found {len(mriqc_tsnr)} subjects in MRIQC TSV.")

    print("Plotting MRIQC tSNR histogram …")
    plot_mriqc_tsnr_histogram(mriqc_tsnr, OUT_DIR, show=args.show)

    # ── comparison ────────────────────────────────────────────────────────────
    print("Plotting comparison …")
    plot_tsnr_comparison(raw_tsnr, mriqc_tsnr, OUT_DIR, show=args.show)

    print("Done. Outputs in:", OUT_DIR)


if __name__ == "__main__":
    main()
