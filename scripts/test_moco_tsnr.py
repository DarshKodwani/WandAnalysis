"""
test_moco_tsnr.py  —  Temporary experiment script.

Applies FSL mcflirt motion correction to the raw ses-06 resting-state BOLD
for one subject, then measures tSNR using three masking strategies:

  1. Simple intensity threshold  (our current pipeline)
  2. nilearn compute_epi_mask    (what MRIQC uses internally)
  3. Both masks on raw data      (baselines without motion correction)

Goal: isolate how much of the MRIQC tSNR gap is explained by
      (a) motion correction alone, and (b) the choice of brain mask.

Usage
─────
    conda run -n wand python scripts/test_moco_tsnr.py sub-01187
    conda run -n wand python scripts/test_moco_tsnr.py sub-01187 --keep
"""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd
from nilearn.masking import compute_epi_mask

# ── Paths ─────────────────────────────────────────────────────────────────────
REPO_ROOT   = Path(__file__).resolve().parents[1]
WAND_ROOT   = REPO_ROOT / "data" / "WAND"
MRIQC_TSV   = WAND_ROOT / "derivatives" / "mriqc" / "analysis" / "ses-06_task-rest_bold.tsv"
MCFLIRT_BIN = Path("/usr/local/apps/fsl_6.0.7/bin/mcflirt")
SESSION     = "ses-06"


# ── Helpers ───────────────────────────────────────────────────────────────────

def find_bold(subject: str) -> Path:
    path = WAND_ROOT / subject / SESSION / "func" / \
           f"{subject}_{SESSION}_task-rest_bold.nii.gz"
    if not path.exists():
        sys.exit(f"ERROR: BOLD file not found:\n  {path}")
    if path.stat().st_size < 1024 * 1024:
        sys.exit(
            f"ERROR: {path.name} looks like a git-annex pointer "
            f"({path.stat().st_size} bytes).\n"
            f"Download it first with:\n"
            f"  bash scripts/download.sh {subject} {SESSION} func {path.name}"
        )
    return path


def get_mriqc_tsnr(subject: str) -> tuple[float, int]:
    """Return (tsnr, dummy_trs) from the MRIQC TSV for this subject."""
    df = pd.read_csv(MRIQC_TSV, sep="\t")
    row = df[df["bids_name"].str.startswith(subject)]
    if row.empty:
        sys.exit(f"ERROR: {subject} not found in MRIQC TSV.")
    return float(row.iloc[0]["tsnr"]), int(row.iloc[0]["dummy_trs"])


def make_brain_mask_simple(data: np.ndarray) -> np.ndarray:
    """Intensity-based brain mask (same as iqm.py)."""
    mean_vol = data.mean(axis=-1)
    thresh   = 0.1 * np.percentile(mean_vol, 95)
    return mean_vol > thresh


def make_brain_mask_nilearn(img: nib.Nifti1Image) -> np.ndarray:
    """
    EPI brain mask using nilearn.masking.compute_epi_mask.
    This is the same function MRIQC calls internally for functional data.
    Returns a boolean array of shape (x, y, z).
    """
    mask_img = compute_epi_mask(img)
    return mask_img.get_fdata().astype(bool)


def compute_tsnr(data: np.ndarray, mask: np.ndarray) -> float:
    """Median tSNR across brain voxels (same formula as iqm.py)."""
    mean_t    = data.mean(axis=-1)
    std_t     = data.std(axis=-1, ddof=1)
    std_safe  = np.where(std_t > 0, std_t, np.inf)
    tsnr_map  = np.where(mask, mean_t / std_safe, 0.0)
    return float(np.median(tsnr_map[mask]))


def run_mcflirt(bold_path: Path, work_dir: Path, n_vols: int) -> Path:
    """
    Run FSL mcflirt on bold_path.
    Realigns to the middle volume (matching MRIQC's default).
    Returns the path to the motion-corrected NIfTI.
    """
    ref_vol   = n_vols // 2
    out_stem  = work_dir / "bold_mcf"

    cmd = [
        str(MCFLIRT_BIN),
        "-in",   str(bold_path),
        "-out",  str(out_stem),
        "-refvol", str(ref_vol),
        "-plots",           # save motion parameters
        "-rmsabs",          # save abs RMS displacement
        "-rmsrel",          # save rel RMS displacement
    ]
    print(f"\n  Running: {' '.join(cmd)}\n")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stderr)
        sys.exit(f"ERROR: mcflirt failed (return code {result.returncode})")

    corrected = Path(str(out_stem) + ".nii.gz")
    if not corrected.exists():
        sys.exit(f"ERROR: expected mcflirt output not found: {corrected}")
    return corrected


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Test whether mcflirt motion correction reproduces MRIQC tSNR."
    )
    parser.add_argument("subject", help="Subject ID, e.g. sub-01187")
    parser.add_argument("--keep",  action="store_true",
                        help="Keep the mcflirt working directory instead of deleting it.")
    args = parser.parse_args()

    subject = args.subject

    # ── Step 0: ground truth from MRIQC ──────────────────────────────────────
    print(f"\n{'─'*60}")
    print(f"  Subject      : {subject}")
    print(f"  Session      : {SESSION}")
    mriqc_tsnr, dummy_trs = get_mriqc_tsnr(subject)
    print(f"  MRIQC tSNR   : {mriqc_tsnr:.2f}  (target to match)")
    print(f"  Dummy TRs    : {dummy_trs}  (will be dropped)")
    print(f"{'─'*60}")

    # ── Step 1: load raw BOLD ─────────────────────────────────────────────────
    bold_path = find_bold(subject)
    print(f"\n[1/5] Loading raw BOLD …")
    print(f"  {bold_path.relative_to(REPO_ROOT)}")
    img  = nib.load(str(bold_path))
    data = img.get_fdata(dtype=np.float32)
    n_vols = data.shape[-1]
    print(f"  Shape: {data.shape}  ({n_vols} volumes)")

    # ── Step 2: compute raw tSNR with both masks (baselines) ─────────────────
    print(f"\n[2/5] Computing raw tSNR baselines (no motion correction) …")
    mask_raw_simple   = make_brain_mask_simple(data)
    tsnr_raw_simple   = compute_tsnr(data, mask_raw_simple)
    mask_raw_nilearn  = make_brain_mask_nilearn(img)
    tsnr_raw_nilearn  = compute_tsnr(data, mask_raw_nilearn)
    print(f"  Raw tSNR (simple mask)  : {tsnr_raw_simple:.2f}")
    print(f"  Raw tSNR (nilearn mask) : {tsnr_raw_nilearn:.2f}")

    # ── Step 3: drop dummy TRs ────────────────────────────────────────────────
    print(f"\n[3/5] Dropping {dummy_trs} dummy TR(s) …")
    data_nodummy = data[..., dummy_trs:]
    img_nodummy  = nib.Nifti1Image(data_nodummy, img.affine, img.header)
    print(f"  Volumes after dropping dummies: {data_nodummy.shape[-1]}")

    # ── Step 4: mcflirt on dummy-stripped data ────────────────────────────────
    print(f"\n[4/5] Running mcflirt …")
    work_dir = Path(tempfile.mkdtemp(prefix=f"moco_{subject}_"))
    print(f"  Working dir  : {work_dir}")

    # Write dummy-stripped NIfTI to disk for mcflirt
    stripped_path = work_dir / "bold_stripped.nii.gz"
    nib.save(img_nodummy, str(stripped_path))

    try:
        corrected_path = run_mcflirt(stripped_path, work_dir, data_nodummy.shape[-1])

        # ── Step 5: compute tSNR on corrected data with both masks ────────────
        print(f"\n[5/5] Computing tSNR on motion-corrected data …")
        corr_img  = nib.load(str(corrected_path))
        corr_data = corr_img.get_fdata(dtype=np.float32)

        mask_corr_simple  = make_brain_mask_simple(corr_data)
        tsnr_corr_simple  = compute_tsnr(corr_data, mask_corr_simple)
        print(f"  Corrected tSNR (simple mask)  : {tsnr_corr_simple:.2f}")

        mask_corr_nilearn = make_brain_mask_nilearn(corr_img)
        tsnr_corr_nilearn = compute_tsnr(corr_data, mask_corr_nilearn)
        print(f"  Corrected tSNR (nilearn mask) : {tsnr_corr_nilearn:.2f}")

        # ── Results table ─────────────────────────────────────────────────────
        def gap(val):
            d = val - mriqc_tsnr
            return f"{d:>+6.2f}  ({d/mriqc_tsnr*100:>+5.1f}%)"

        def verdict(val):
            pct = abs((val - mriqc_tsnr) / mriqc_tsnr * 100)
            if pct <= 5:   return "✓ MATCH  (<5%)"
            if pct <= 15:  return "~ CLOSE  (<15%)"
            return              "✗ GAP    (>15%)"

        W = 65
        print(f"\n{'═'*W}")
        print(f"  RESULTS — {subject}")
        print(f"{'─'*W}")
        print(f"  {'Condition':<38} {'tSNR':>6}   {'vs MRIQC':>14}   {'Verdict'}")
        print(f"{'─'*W}")
        rows = [
            ("Raw,  simple intensity mask  (our current)", tsnr_raw_simple),
            ("Raw,  nilearn EPI mask",                    tsnr_raw_nilearn),
            ("Moco, simple intensity mask",               tsnr_corr_simple),
            ("Moco, nilearn EPI mask       (MRIQC-like)", tsnr_corr_nilearn),
            ("MRIQC tSNR  ← TARGET",                     mriqc_tsnr),
        ]
        for label, val in rows:
            if label.startswith("MRIQC"):
                print(f"{'─'*W}")
                print(f"  {label:<38} {val:>6.2f}")
            else:
                print(f"  {label:<38} {val:>6.2f}   {gap(val)}   {verdict(val)}")
        print(f"{'═'*W}\n")

    finally:
        if not args.keep:
            shutil.rmtree(work_dir, ignore_errors=True)
            print(f"  (Cleaned up working dir {work_dir})")
        else:
            print(f"  (Working dir kept at {work_dir})")


if __name__ == "__main__":
    main()
