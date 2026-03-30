"""Generate dummy results visualizations for the multiverse paper."""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

np.random.seed(42)

# ============================================================
# FIGURE 1: LOCAL METRICS — Step-level sensitivity strip plot
# ============================================================

fig1, axes1 = plt.subplots(1, 9, figsize=(22, 6), sharey=False)
fig1.suptitle("Local Metric Sensitivity by Preprocessing Step\n(dummy data — each dot = one OAT perturbation)",
              fontsize=14, fontweight="bold", y=1.02)

step_names = ["MC", "STC", "SDC", "NORM", "SMOOTH", "FILT", "REG", "PARC", "METRIC"]
step_counts = [6, 7, 6, 7, 6, 6, 10, 9, 7]
metric_labels = [
    "Mean FD (mm)",
    "tSNR",
    "Dice w/ T1w",
    "Dice w/ MNI",
    "tSNR",
    "BOLD var. ratio",
    "QC-FC corr.",
    "Homogeneity",
    "ICC",
]

# Simulate: each step has a default (star) and N perturbations (dots)
# Some steps show high sensitivity, some low
# High-sensitivity steps: REG, SMOOTH, NORM, PARC
sensitivities = {
    "MC":     (0.22, 0.03),   # mean FD, low spread
    "STC":    (45.0, 2.0),    # tSNR, low spread
    "SDC":    (0.82, 0.06),   # Dice, moderate spread
    "NORM":   (0.78, 0.08),   # Dice, high spread
    "SMOOTH": (52.0, 12.0),   # tSNR, very high spread
    "FILT":   (0.65, 0.08),   # var ratio, moderate
    "REG":    (0.15, 0.12),   # QC-FC, very high spread (some negative = good)
    "PARC":   (0.55, 0.10),   # homogeneity, high spread
    "METRIC": (0.42, 0.08),   # ICC, moderate spread
}

eco_colors = {"FSL": "#2980B9", "SPM": "#E74C3C", "fMRIPrep": "#27AE60"}

for idx, (step, n_pert) in enumerate(zip(step_names, step_counts)):
    ax = axes1[idx]
    mean_val, spread = sensitivities[step]

    for eco_i, (eco, color) in enumerate(eco_colors.items()):
        x_base = eco_i
        # Default
        default_val = mean_val + np.random.normal(0, spread * 0.1)
        # Perturbations
        pert_vals = mean_val + np.random.normal(0, spread, n_pert)

        jitter = np.random.uniform(-0.15, 0.15, n_pert)
        ax.scatter(x_base + jitter, pert_vals, c=color, alpha=0.6, s=30, zorder=3)
        ax.scatter(x_base, default_val, c=color, marker="*", s=120, edgecolors="black",
                   linewidth=0.8, zorder=4)

    ax.set_title(step, fontsize=11, fontweight="bold")
    ax.set_ylabel(metric_labels[idx], fontsize=8)
    ax.set_xticks([0, 1, 2])
    ax.set_xticklabels(["FSL", "SPM", "fMRI\nPrep"], fontsize=7)
    ax.grid(axis="y", alpha=0.3)

    # Shade background based on spread (visual cue for sensitivity)
    if spread > 0.09 or (step == "SMOOTH"):
        ax.set_facecolor("#FFF3E0")  # warm = high sensitivity
    else:
        ax.set_facecolor("#E8F5E9")  # cool = low sensitivity

legend_elements = [
    mpatches.Patch(facecolor="#FFF3E0", edgecolor="grey", label="High sensitivity"),
    mpatches.Patch(facecolor="#E8F5E9", edgecolor="grey", label="Low sensitivity"),
    plt.Line2D([0], [0], marker="*", color="grey", markersize=12, linestyle="None", label="Default"),
    plt.Line2D([0], [0], marker="o", color="grey", markersize=6, linestyle="None", label="Perturbation"),
]
fig1.legend(handles=legend_elements, loc="lower center", ncol=4, fontsize=10,
            bbox_to_anchor=(0.5, -0.06))
fig1.tight_layout()
fig1.savefig(
    "/MRIWork/MRIWork06/nr/darsh_kodwani/WandAnalysis/docs/paper/"
    "when_is_a_result_robust_marginalization_over_reasonable_analysis_choices_in_fmri/"
    "dummy_local_metrics.png", dpi=150, bbox_inches="tight", facecolor="white")


# ============================================================
# FIGURE 2: GLOBAL METRICS — "Money Plot" / Specification Curve
# ============================================================

fig2, axes2 = plt.subplots(5, 1, figsize=(18, 14), sharex=True,
                            gridspec_kw={"height_ratios": [3, 3, 3, 3, 1.5]})
fig2.suptitle("Global Metric Specification Curve — The Money Plot\n"
              "(all 195 pipelines sorted by FC matrix correlation; dummy data)",
              fontsize=14, fontweight="bold", y=1.01)

n_pipelines = 195

# Simulate 4 global metrics for 195 pipelines
# Create ecosystem labels
eco_labels = []
eco_colors_arr = []
for eco, color in [("FSL", "#2980B9"), ("SPM", "#E74C3C"), ("fMRIPrep", "#27AE60")]:
    eco_labels.extend([eco] * 65)
    eco_colors_arr.extend([color] * 65)

# FC matrix correlation with default (sorted — this is the sorting axis)
fc_corr = np.concatenate([
    np.random.beta(8, 1.5, 65),   # FSL: mostly high, some dips
    np.random.beta(7, 2, 65),     # SPM
    np.random.beta(9, 1.2, 65),   # fMRIPrep
])

sort_idx = np.argsort(fc_corr)[::-1]
fc_corr_sorted = fc_corr[sort_idx]
eco_colors_sorted = [eco_colors_arr[i] for i in sort_idx]
eco_labels_sorted = [eco_labels[i] for i in sort_idx]

# Fingerprinting accuracy — generally correlated with FC corr but noisy
fingerprint = 0.3 + 0.5 * fc_corr + np.random.normal(0, 0.06, n_pipelines)
fingerprint = np.clip(fingerprint, 0, 1)
fingerprint_sorted = fingerprint[sort_idx]

# 3T/7T discriminability — less correlated
discrimin = 0.7 + 0.15 * np.random.randn(n_pipelines)
discrimin = np.clip(discrimin, 0.3, 1.0)
# Make some REG and SMOOTH perturbations drop discriminability
for i in range(n_pipelines):
    if np.random.random() < 0.15:
        discrimin[i] -= 0.2
discrimin_sorted = discrimin[sort_idx]

# Network modularity
modularity = 0.35 + 0.1 * np.random.randn(n_pipelines)
modularity = np.clip(modularity, 0.1, 0.6)
modularity_sorted = modularity[sort_idx]

x = np.arange(n_pipelines)

metric_data = [
    (fc_corr_sorted, "FC Matrix Corr.\nwith Default", (0.4, 1.0)),
    (fingerprint_sorted, "Fingerprinting\nAccuracy", (0.0, 1.0)),
    (discrimin_sorted, "3T/7T\nDiscriminability", (0.2, 1.0)),
    (modularity_sorted, "Network\nModularity (Q)", (0.05, 0.65)),
]

for ax_idx, (data, ylabel, ylim) in enumerate(metric_data):
    ax = axes2[ax_idx]
    ax.bar(x, data, color=eco_colors_sorted, width=1.0, alpha=0.7)
    ax.set_ylabel(ylabel, fontsize=10, fontweight="bold")
    ax.set_ylim(ylim)
    ax.grid(axis="y", alpha=0.3)

    # Reference line for defaults
    if ax_idx == 0:
        ax.axhline(y=1.0, color="grey", linestyle="--", linewidth=0.8, alpha=0.5)

# Bottom panel: step indicator (which step was perturbed)
ax_bottom = axes2[4]
step_abbrevs = ["MC", "STC", "SDC", "NORM", "SM", "FILT", "REG", "PARC", "MET"]
step_palette = plt.cm.Set1(np.linspace(0, 1, 9))

# Assign each pipeline to a step (3 defaults + 64 perturbations each)
step_assignments = []
for eco in range(3):
    step_assignments.append(-1)  # default
    for step_i, count in enumerate(step_counts):
        step_assignments.extend([step_i] * count)

step_sorted = [step_assignments[i] for i in sort_idx]

for i, s in enumerate(step_sorted):
    if s == -1:
        ax_bottom.bar(i, 1, color="black", width=1.0)
    else:
        ax_bottom.bar(i, 1, color=step_palette[s], width=1.0, alpha=0.8)

ax_bottom.set_yticks([])
ax_bottom.set_ylabel("Perturbed\nStep", fontsize=10, fontweight="bold")
ax_bottom.set_xlabel("Pipeline (sorted by FC matrix correlation with default)", fontsize=11)

# Step legend
step_patches = [mpatches.Patch(color=step_palette[i], label=step_abbrevs[i]) for i in range(9)]
step_patches.insert(0, mpatches.Patch(facecolor="black", label="DEFAULT"))
ax_bottom.legend(handles=step_patches, loc="upper center", bbox_to_anchor=(0.5, -0.4),
                 ncol=10, fontsize=9)

# Ecosystem legend on top
eco_patches = [
    mpatches.Patch(facecolor="#2980B9", alpha=0.7, label="FSL"),
    mpatches.Patch(facecolor="#E74C3C", alpha=0.7, label="SPM"),
    mpatches.Patch(facecolor="#27AE60", alpha=0.7, label="fMRIPrep"),
]
axes2[0].legend(handles=eco_patches, loc="upper right", fontsize=10)

fig2.tight_layout()
fig2.savefig(
    "/MRIWork/MRIWork06/nr/darsh_kodwani/WandAnalysis/docs/paper/"
    "when_is_a_result_robust_marginalization_over_reasonable_analysis_choices_in_fmri/"
    "dummy_money_plot.png", dpi=150, bbox_inches="tight", facecolor="white")


# ============================================================
# FIGURE 3: VARIANCE DECOMPOSITION — Stacked bar chart
# ============================================================

fig3, ax3 = plt.subplots(figsize=(12, 5))
fig3.suptitle("Variance Decomposition of FC Matrix Edges\n(dummy data — ANOVA partition per step)",
              fontsize=14, fontweight="bold")

# For each step, show how much variance comes from pipeline, subject, interaction, field strength
step_labels_full = [
    "Motion\nCorrection", "Slice-Timing\nCorrection", "Distortion\nCorrection",
    "Spatial\nNormalisation", "Spatial\nSmoothing", "Temporal\nFiltering",
    "Nuisance\nRegression", "Parcellation", "Connectivity\nMetric"
]

# Dummy variance fractions (should sum to 1 per step)
# High-sensitivity steps have more pipeline variance
var_pipeline = np.array([0.08, 0.04, 0.12, 0.18, 0.25, 0.10, 0.30, 0.20, 0.15])
var_subject = np.array([0.55, 0.60, 0.50, 0.45, 0.35, 0.52, 0.30, 0.40, 0.48])
var_interaction = np.array([0.05, 0.03, 0.08, 0.07, 0.10, 0.06, 0.12, 0.08, 0.07])
var_field = np.array([0.12, 0.08, 0.15, 0.10, 0.05, 0.07, 0.08, 0.07, 0.10])
var_residual = 1 - var_pipeline - var_subject - var_interaction - var_field

x_pos = np.arange(9)
width = 0.65

bars1 = ax3.bar(x_pos, var_pipeline, width, label="Pipeline", color="#E74C3C")
bars2 = ax3.bar(x_pos, var_subject, width, bottom=var_pipeline, label="Subject", color="#3498DB")
bars3 = ax3.bar(x_pos, var_interaction, width,
                bottom=var_pipeline + var_subject, label="Pipeline × Subject", color="#F39C12")
bars4 = ax3.bar(x_pos, var_field, width,
                bottom=var_pipeline + var_subject + var_interaction, label="Field Strength", color="#9B59B6")
bars5 = ax3.bar(x_pos, var_residual, width,
                bottom=var_pipeline + var_subject + var_interaction + var_field,
                label="Residual", color="#BDC3C7")

ax3.set_xticks(x_pos)
ax3.set_xticklabels(step_labels_full, fontsize=9, ha="center")
ax3.set_ylabel("Fraction of Total Variance", fontsize=12)
ax3.set_ylim(0, 1)
ax3.legend(loc="upper right", fontsize=10)
ax3.grid(axis="y", alpha=0.3)

# Annotate pipeline % on each bar
for i, v in enumerate(var_pipeline):
    ax3.text(i, v / 2, f"{v:.0%}", ha="center", va="center", fontsize=8,
             fontweight="bold", color="white")

fig3.tight_layout()
fig3.savefig(
    "/MRIWork/MRIWork06/nr/darsh_kodwani/WandAnalysis/docs/paper/"
    "when_is_a_result_robust_marginalization_over_reasonable_analysis_choices_in_fmri/"
    "dummy_variance_decomposition.png", dpi=150, bbox_inches="tight", facecolor="white")


# ============================================================
# FIGURE 4: LOCAL-WIN / GLOBAL-LOSS PARADOX scatter
# ============================================================

fig4, ax4 = plt.subplots(figsize=(10, 7))
fig4.suptitle("Local-Win / Global-Loss Paradox\n(dummy data — each dot = one pipeline variant)",
              fontsize=14, fontweight="bold")

# x = local metric improvement (positive = improved local metric)
# y = global metric change (positive = improved FC outcome)
n = 192  # exclude 3 defaults

local_improvement = np.random.randn(n) * 0.5
global_change = 0.3 * local_improvement + np.random.randn(n) * 0.3

# Create some paradox cases (high local improvement, negative global change)
paradox_mask = (local_improvement > 0.8) & (global_change < -0.1)
# Force some into this region
for i in range(n):
    if np.random.random() < 0.08:
        local_improvement[i] = np.random.uniform(0.5, 1.5)
        global_change[i] = np.random.uniform(-0.8, -0.1)

# Assign step colours
step_for_variant = []
for eco in range(3):
    for step_i, count in enumerate(step_counts):
        step_for_variant.extend([step_i] * count)

step_colors = [step_palette[s] for s in step_for_variant]

scatter = ax4.scatter(local_improvement, global_change, c=step_colors,
                      alpha=0.6, s=40, edgecolors="white", linewidth=0.3)

# Quadrant lines
ax4.axhline(0, color="grey", linestyle="-", linewidth=0.8)
ax4.axvline(0, color="grey", linestyle="-", linewidth=0.8)

# Quadrant labels
ax4.text(1.5, 0.8, "✓ Local win\n✓ Global win", fontsize=10, ha="center",
         color="#27AE60", fontweight="bold", alpha=0.7)
ax4.text(-1.5, 0.8, "✗ Local loss\n✓ Global win", fontsize=10, ha="center",
         color="#F39C12", fontweight="bold", alpha=0.7)
ax4.text(1.5, -0.8, "✓ Local win\n✗ Global loss\n(PARADOX)", fontsize=10, ha="center",
         color="#E74C3C", fontweight="bold", alpha=0.7)
ax4.text(-1.5, -0.8, "✗ Local loss\n✗ Global loss", fontsize=10, ha="center",
         color="#7F8C8D", fontweight="bold", alpha=0.7)

# Shade paradox quadrant
ax4.fill_between([0, 2.5], -1.5, 0, alpha=0.06, color="red")

ax4.set_xlabel("Local metric improvement (z-scored)", fontsize=12)
ax4.set_ylabel("Global metric change (Δ FC matrix correlation)", fontsize=12)
ax4.set_xlim(-2.5, 2.5)
ax4.set_ylim(-1.5, 1.5)

# Step legend
step_patches_full = [mpatches.Patch(color=step_palette[i], label=step_abbrevs[i]) for i in range(9)]
ax4.legend(handles=step_patches_full, loc="lower left", fontsize=9, title="Perturbed Step")

fig4.tight_layout()
fig4.savefig(
    "/MRIWork/MRIWork06/nr/darsh_kodwani/WandAnalysis/docs/paper/"
    "when_is_a_result_robust_marginalization_over_reasonable_analysis_choices_in_fmri/"
    "dummy_paradox_scatter.png", dpi=150, bbox_inches="tight", facecolor="white")

print("Done — saved 4 dummy figures.")
