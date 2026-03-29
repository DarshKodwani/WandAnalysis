#!/usr/bin/env python3
"""Compare MRIQC metric distributions between 3T and 7T sessions.

Default comparison is resting-state BOLD:
  3T -> ses-03
  7T -> ses-06

Example:
  python scripts/compare_3t_7t_mriqc.py
  python scripts/compare_3t_7t_mriqc.py --metric snr
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
MRIQC_ANALYSIS_DIR = REPO_ROOT / "data" / "WAND" / "derivatives" / "mriqc" / "analysis"
DEFAULT_3T_SESSION = "ses-03"
DEFAULT_7T_SESSION = "ses-06"
DEFAULT_TASK = "rest"


def mriqc_tsv_path(session: str, task: str) -> Path:
    return MRIQC_ANALYSIS_DIR / f"{session}_task-{task}_bold.tsv"


def load_metric_table(tsv_path: Path, metric: str) -> pd.DataFrame:
    """Load subject-level metric values from an MRIQC TSV."""
    if not tsv_path.exists():
        raise FileNotFoundError(f"MRIQC TSV not found: {tsv_path}")

    df = pd.read_csv(tsv_path, sep="\t")
    if "bids_name" not in df.columns:
        raise KeyError(f"Missing column 'bids_name' in: {tsv_path.name}")
    if metric not in df.columns:
        raise KeyError(f"Missing column '{metric}' in: {tsv_path.name}")

    out = pd.DataFrame(
        {
            "subject": df["bids_name"].astype(str).str.extract(r"(sub-\d+)")[0],
            "value": pd.to_numeric(df[metric], errors="coerce"),
        }
    )
    out = out.dropna(subset=["subject", "value"]).drop_duplicates(subset=["subject"])  # defensive cleanup
    out = out.sort_values("subject").reset_index(drop=True)
    return out


def summarize(values: np.ndarray) -> dict[str, float]:
    return {
        "n": float(values.size),
        "mean": float(np.mean(values)),
        "median": float(np.median(values)),
        "std": float(np.std(values, ddof=1)) if values.size > 1 else 0.0,
        "min": float(np.min(values)),
        "max": float(np.max(values)),
    }


def stats_text(label_3t: str, stats_3t: dict[str, float], label_7t: str, stats_7t: dict[str, float]) -> str:
    return (
        f"{label_3t}: n={int(stats_3t['n'])}, mean={stats_3t['mean']:.2f}, median={stats_3t['median']:.2f}, sd={stats_3t['std']:.2f}\n"
        f"{label_7t}: n={int(stats_7t['n'])}, mean={stats_7t['mean']:.2f}, median={stats_7t['median']:.2f}, sd={stats_7t['std']:.2f}"
    )


def add_mean_median_lines(ax: plt.Axes, stats_3t: dict[str, float], stats_7t: dict[str, float]) -> None:
    ax.axvline(stats_3t["mean"], color="#1f77b4", linestyle="--", linewidth=1.1, alpha=0.9, label="3T mean")
    ax.axvline(stats_3t["median"], color="#1f77b4", linestyle=":", linewidth=1.2, alpha=0.9, label="3T median")
    ax.axvline(stats_7t["mean"], color="#d62728", linestyle="--", linewidth=1.1, alpha=0.9, label="7T mean")
    ax.axvline(stats_7t["median"], color="#d62728", linestyle=":", linewidth=1.2, alpha=0.9, label="7T median")


def make_plot(
    values_3t: np.ndarray,
    values_7t: np.ndarray,
    paired: pd.DataFrame,
    metric: str,
    session_3t: str,
    session_7t: str,
    out_path: Path,
) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(18, 10))
    stats_3t = summarize(values_3t)
    stats_7t = summarize(values_7t)
    label_3t = f"3T ({session_3t})"
    label_7t = f"7T ({session_7t})"
    summary_block = stats_text(label_3t, stats_3t, label_7t, stats_7t)

    # Panel 1: box + jittered points.
    rng = np.random.default_rng(42)
    axes[0, 0].boxplot(
        [values_3t, values_7t],
        tick_labels=[label_3t, label_7t],
        showmeans=True,
    )
    jitter_3t = 1.0 + (rng.random(values_3t.size) - 0.5) * 0.14
    jitter_7t = 2.0 + (rng.random(values_7t.size) - 0.5) * 0.14
    axes[0, 0].scatter(jitter_3t, values_3t, s=14, alpha=0.45, color="#1f77b4", edgecolors="none")
    axes[0, 0].scatter(jitter_7t, values_7t, s=14, alpha=0.45, color="#d62728", edgecolors="none")
    axes[0, 0].set_title(f"{metric.upper()} Distribution")
    axes[0, 0].set_ylabel(metric.upper())
    axes[0, 0].grid(axis="y", linestyle="--", alpha=0.35)
    axes[0, 0].text(
        0.02,
        0.98,
        summary_block,
        transform=axes[0, 0].transAxes,
        va="top",
        ha="left",
        fontsize=9,
        bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.85, "edgecolor": "0.8"},
    )

    all_values = np.concatenate([values_3t, values_7t])
    bins = np.histogram_bin_edges(all_values, bins=24)

    # Panel 2: non-normalized histogram (participant counts).
    axes[0, 1].hist(values_3t, bins=bins, alpha=0.55, density=False, color="#1f77b4", label=f"3T ({values_3t.size})")
    axes[0, 1].hist(values_7t, bins=bins, alpha=0.55, density=False, color="#d62728", label=f"7T ({values_7t.size})")
    add_mean_median_lines(axes[0, 1], stats_3t, stats_7t)
    axes[0, 1].set_title("Histogram (Participant Counts)")
    axes[0, 1].set_xlabel(metric.upper())
    axes[0, 1].set_ylabel("Number of participants")
    axes[0, 1].legend(frameon=False, fontsize=8)
    axes[0, 1].grid(axis="y", linestyle="--", alpha=0.35)
    axes[0, 1].text(
        0.02,
        0.98,
        summary_block,
        transform=axes[0, 1].transAxes,
        va="top",
        ha="left",
        fontsize=9,
        bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.85, "edgecolor": "0.8"},
    )

    # Panel 3: normalized histogram (density).
    axes[1, 0].hist(values_3t, bins=bins, alpha=0.55, density=True, color="#1f77b4", label=f"3T ({values_3t.size})")
    axes[1, 0].hist(values_7t, bins=bins, alpha=0.55, density=True, color="#d62728", label=f"7T ({values_7t.size})")
    add_mean_median_lines(axes[1, 0], stats_3t, stats_7t)
    axes[1, 0].set_title("Histogram (Density, Normalized)")
    axes[1, 0].set_xlabel(metric.upper())
    axes[1, 0].set_ylabel("Density")
    axes[1, 0].legend(frameon=False, fontsize=8)
    axes[1, 0].grid(axis="y", linestyle="--", alpha=0.35)
    axes[1, 0].text(
        0.02,
        0.98,
        summary_block,
        transform=axes[1, 0].transAxes,
        va="top",
        ha="left",
        fontsize=9,
        bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.85, "edgecolor": "0.8"},
    )

    # Panel 4: paired change for subjects available in both sessions.
    if not paired.empty:
        x = np.array([0.0, 1.0])
        for _, row in paired.iterrows():
            axes[1, 1].plot(x, [row["value_3t"], row["value_7t"]], color="0.7", linewidth=0.9, alpha=0.5)
        axes[1, 1].scatter(np.zeros(len(paired)), paired["value_3t"], s=15, color="#1f77b4", alpha=0.8)
        axes[1, 1].scatter(np.ones(len(paired)), paired["value_7t"], s=15, color="#d62728", alpha=0.8)
        diff = paired["value_7t"] - paired["value_3t"]
        diff_stats = summarize(diff.to_numpy(dtype=float))
        axes[1, 1].set_title(
            f"Paired Subjects (n={len(paired)})\n"
            f"Median delta (7T-3T): {diff_stats['median']:.2f} | "
            f"Mean delta (7T-3T): {diff_stats['mean']:.2f} | "
            f"SD delta (7T-3T): {diff_stats['std']:.2f}"
        )
        axes[1, 1].set_xticks([0, 1])
        axes[1, 1].set_xticklabels(["3T", "7T"])
        axes[1, 1].set_ylabel(metric.upper())
        axes[1, 1].grid(axis="y", linestyle="--", alpha=0.35)
        axes[1, 1].text(
            0.02,
            0.98,
            summary_block,
            transform=axes[1, 1].transAxes,
            va="top",
            ha="left",
            fontsize=9,
            bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.85, "edgecolor": "0.8"},
        )
    else:
        axes[1, 1].text(0.5, 0.5, "No overlapping subjects\nfor paired comparison.", ha="center", va="center")
        axes[1, 1].set_title("Paired Comparison")
        axes[1, 1].set_axis_off()

    fig.suptitle(
        f"MRIQC {metric.upper()} comparison: 3T ({session_3t}) vs 7T ({session_7t})"
        f"\n"
        f"Mean 3T={stats_3t['mean']:.2f}, Median 3T={stats_3t['median']:.2f}, SD 3T={stats_3t['std']:.2f} | "
        f"Mean 7T={stats_7t['mean']:.2f}, Median 7T={stats_7t['median']:.2f}, SD 7T={stats_7t['std']:.2f} | "
        f"Delta mean (7T-3T)={stats_7t['mean'] - stats_3t['mean']:.2f}",
        fontsize=12,
    )
    fig.tight_layout()
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare MRIQC metric distributions for 3T vs 7T sessions.")
    parser.add_argument("--metric", default="tsnr", choices=["tsnr", "snr"], help="MRIQC metric to compare.")
    parser.add_argument("--session-3t", default=DEFAULT_3T_SESSION, help="3T session label (default: ses-03).")
    parser.add_argument("--session-7t", default=DEFAULT_7T_SESSION, help="7T session label (default: ses-06).")
    parser.add_argument("--task", default=DEFAULT_TASK, help="BOLD task label (default: rest).")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=REPO_ROOT / "results" / "group",
        help="Output directory for plot and summary files.",
    )
    args = parser.parse_args()

    path_3t = mriqc_tsv_path(args.session_3t, args.task)
    path_7t = mriqc_tsv_path(args.session_7t, args.task)

    df_3t = load_metric_table(path_3t, args.metric)
    df_7t = load_metric_table(path_7t, args.metric)
    paired = df_3t.merge(df_7t, on="subject", suffixes=("_3t", "_7t"))

    values_3t = df_3t["value"].to_numpy(dtype=float)
    values_7t = df_7t["value"].to_numpy(dtype=float)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"mriqc_{args.metric}_{args.session_3t}_vs_{args.session_7t}_task-{args.task}"
    fig_path = args.out_dir / f"{stem}.png"
    summary_path = args.out_dir / f"{stem}_summary.tsv"
    paired_path = args.out_dir / f"{stem}_paired.tsv"

    make_plot(values_3t, values_7t, paired, args.metric, args.session_3t, args.session_7t, fig_path)

    summary_rows = [
        {"group": f"3T_{args.session_3t}", **summarize(values_3t)},
        {"group": f"7T_{args.session_7t}", **summarize(values_7t)},
    ]
    if not paired.empty:
        diff = paired["value_7t"] - paired["value_3t"]
        summary_rows.append(
            {
                "group": "paired_delta_7T_minus_3T",
                **summarize(diff.to_numpy(dtype=float)),
            }
        )
    pd.DataFrame(summary_rows).to_csv(summary_path, sep="\t", index=False)
    paired.to_csv(paired_path, sep="\t", index=False)

    print(f"Saved plot:    {fig_path}")
    print(f"Saved summary: {summary_path}")
    print(f"Saved paired:  {paired_path}")
    print(f"3T rows: {len(df_3t)} | 7T rows: {len(df_7t)} | Paired: {len(paired)}")


if __name__ == "__main__":
    main()
