"""Generate a workflow diagram comparing the three ecosystem default pipelines."""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# --- Data ---
steps = [
    "1. Motion Correction\n(MC)",
    "2. Slice-Timing\nCorrection (STC)",
    "3. Distortion\nCorrection (SDC)",
    "4. Spatial\nNormalisation (NORM)",
    "5. Spatial\nSmoothing (SMOOTH)",
    "6. Temporal\nFiltering (FILT)",
    "7. Nuisance\nRegression (REG)",
    "8. Parcellation\n(PARC)",
    "9. Connectivity\nMetric (METRIC)",
]

fsl_tools = [
    "MCFLIRT\nref=mid, normcorr",
    "slicetimer\nsinc, ref=mid slice",
    "FUGUE (3T)\nTOPUP (7T)",
    "FLIRT + FNIRT\n→ MNI152 2mm",
    "SUSAN\n6 mm FWHM",
    "Butterworth\n0.01–0.1 Hz",
    "8P\n(6P + WM/CSF)",
    "Schaefer 200\nmean extraction",
    "Pearson\n+ Fisher-z",
]

spm_tools = [
    "SPM Realign\nref=first, LSQ",
    "SPM STC\nFourier, ref=mid",
    "SPM FieldMap\n/ VDM",
    "DARTEL\n→ MNI152",
    "Gaussian\n8 mm FWHM",
    "Butterworth\n0.01–0.1 Hz",
    "24P Friston\n+ WM/CSF",
    "AAL3\nmean extraction",
    "Pearson\n+ Fisher-z",
]

fmriprep_tools = [
    "MCFLIRT\nref=mid, normcorr",
    "Fourier\nref=0.5 (mid-TR)",
    "TOPUP (7T)\nSyN-SDC (3T)",
    "ANTs SyN\n→ MNI152NLin2009c",
    "None\n(0 mm)",
    "None\n(user applies)",
    "aCompCor\n+ ICA-AROMA",
    "Schaefer 200\nmean extraction",
    "Pearson\n+ Fisher-z",
]

# --- Layout ---
n_steps = len(steps)
fig, ax = plt.subplots(figsize=(18, 22))
ax.set_xlim(-0.5, 16.5)
ax.set_ylim(-1, n_steps * 2.6 + 2.5)
ax.invert_yaxis()
ax.set_aspect("equal")
ax.axis("off")

# Colours
col_step = "#2C3E50"       # dark blue-grey for step labels
col_fsl = "#2980B9"        # blue
col_spm = "#E74C3C"        # red
col_fmriprep = "#27AE60"   # green
col_fsl_bg = "#D6EAF8"
col_spm_bg = "#FADBD8"
col_fmriprep_bg = "#D5F5E3"
col_arrow = "#7F8C8D"

# Column x-centres
x_step = 1.8
x_fsl = 6.0
x_spm = 9.8
x_fmriprep = 13.6
box_w = 3.2
box_h = 1.8

# --- Title ---
ax.text(8.25, -0.3, "Three-Ecosystem Default Pipelines", fontsize=20,
        fontweight="bold", ha="center", va="center", color=col_step)
ax.text(8.25, 0.3, "9-step path from raw BOLD to FC matrix", fontsize=13,
        ha="center", va="center", color="#555555", style="italic")

# --- Input box ---
y_input = 1.0
for xc, label, bg, ec in [
    (x_fsl, "FSL", col_fsl_bg, col_fsl),
    (x_spm, "SPM", col_spm_bg, col_spm),
    (x_fmriprep, "fMRIPrep", col_fmriprep_bg, col_fmriprep),
]:
    ax.text(xc, y_input - 0.1, label, fontsize=14, fontweight="bold",
            ha="center", va="center", color=ec)

# Raw BOLD input
rect = mpatches.FancyBboxPatch(
    (x_step - box_w / 2, y_input - 0.45), box_w, 0.9,
    boxstyle="round,pad=0.12", facecolor="#F8F9F9", edgecolor=col_step,
    linewidth=1.5)
ax.add_patch(rect)
ax.text(x_step, y_input, "Raw 4-D BOLD", fontsize=11, fontweight="bold",
        ha="center", va="center", color=col_step)

# --- Draw rows ---
y_start = 2.2
spacing = 2.3

for i in range(n_steps):
    y = y_start + i * spacing

    # Step label box
    rect = mpatches.FancyBboxPatch(
        (x_step - box_w / 2, y - box_h / 2), box_w, box_h,
        boxstyle="round,pad=0.12", facecolor="#F8F9F9", edgecolor=col_step,
        linewidth=1.5)
    ax.add_patch(rect)
    ax.text(x_step, y, steps[i], fontsize=9.5, fontweight="bold",
            ha="center", va="center", color=col_step, linespacing=1.3)

    # Ecosystem boxes
    for xc, tool, bg, ec in [
        (x_fsl, fsl_tools[i], col_fsl_bg, col_fsl),
        (x_spm, spm_tools[i], col_spm_bg, col_spm),
        (x_fmriprep, fmriprep_tools[i], col_fmriprep_bg, col_fmriprep),
    ]:
        rect = mpatches.FancyBboxPatch(
            (xc - box_w / 2, y - box_h / 2), box_w, box_h,
            boxstyle="round,pad=0.12", facecolor=bg, edgecolor=ec,
            linewidth=1.5)
        ax.add_patch(rect)
        ax.text(xc, y, tool, fontsize=9, ha="center", va="center",
                color="#222222", linespacing=1.3)

    # Vertical arrows between rows
    if i < n_steps - 1:
        y_bot = y + box_h / 2
        y_top_next = y + spacing - box_h / 2
        for xc in [x_step, x_fsl, x_spm, x_fmriprep]:
            ax.annotate(
                "", xy=(xc, y_top_next), xytext=(xc, y_bot),
                arrowprops=dict(arrowstyle="-|>", color=col_arrow,
                                lw=1.2, shrinkA=2, shrinkB=2))

# --- Output box ---
y_output = y_start + (n_steps - 1) * spacing + box_h / 2 + 0.7

# Arrow from last row to output
for xc in [x_step, x_fsl, x_spm, x_fmriprep]:
    ax.annotate(
        "", xy=(xc, y_output - 0.45),
        xytext=(xc, y_start + (n_steps - 1) * spacing + box_h / 2),
        arrowprops=dict(arrowstyle="-|>", color=col_arrow,
                        lw=1.2, shrinkA=2, shrinkB=2))

rect = mpatches.FancyBboxPatch(
    (x_step - box_w / 2, y_output - 0.45), box_w, 0.9,
    boxstyle="round,pad=0.12", facecolor="#F8F9F9", edgecolor=col_step,
    linewidth=1.5)
ax.add_patch(rect)
ax.text(x_step, y_output, "P × P FC Matrix", fontsize=11, fontweight="bold",
        ha="center", va="center", color=col_step)

# Ecosystem output labels
for xc, label, bg, ec in [
    (x_fsl, "FSL.DEFAULT\nFC Matrix", col_fsl_bg, col_fsl),
    (x_spm, "SPM.DEFAULT\nFC Matrix", col_spm_bg, col_spm),
    (x_fmriprep, "FMRIPREP.DEFAULT\nFC Matrix", col_fmriprep_bg, col_fmriprep),
]:
    rect = mpatches.FancyBboxPatch(
        (xc - box_w / 2, y_output - 0.45), box_w, 0.9,
        boxstyle="round,pad=0.12", facecolor=bg, edgecolor=ec,
        linewidth=1.5)
    ax.add_patch(rect)
    ax.text(xc, y_output, label, fontsize=9, fontweight="bold",
            ha="center", va="center", color="#222222", linespacing=1.3)

# No annotation box — keep layout clean

plt.tight_layout()
plt.savefig(
    "/MRIWork/MRIWork06/nr/darsh_kodwani/WandAnalysis/docs/paper/"
    "when_is_a_result_robust_marginalization_over_reasonable_analysis_choices_in_fmri/"
    "workflow_diagram.png",
    dpi=200, bbox_inches="tight", facecolor="white")
plt.savefig(
    "/MRIWork/MRIWork06/nr/darsh_kodwani/WandAnalysis/docs/paper/"
    "when_is_a_result_robust_marginalization_over_reasonable_analysis_choices_in_fmri/"
    "workflow_diagram.pdf",
    bbox_inches="tight", facecolor="white")
print("Done — saved workflow_diagram.png and workflow_diagram.pdf")
