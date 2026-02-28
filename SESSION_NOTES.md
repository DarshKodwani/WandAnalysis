# Session Notes — 24 February 2026

## What we did this session

### 1. Results folder restructure
Flipped from `results/<analysis>/<subject>/` → `results/<subject>/<analysis>/`.
- Updated `scripts/visualise_bold.py`, `scripts/slice_qc.py`, `scripts/batch_qc.py`
- Migrated existing outputs for: sub-64927, sub-43766, sub-68443, sub-73378, sub-73512
- Updated image paths in `docs/visualise_bold.md` and `docs/slice_qc.md`

---

### 2. MRIQC investigation
- Looked at https://mriqc.readthedocs.io/en/latest/measures.html
- Conclusion: can't run MRIQC on psychp01 — ANTs, AFNI, FreeSurfer all absent, Singularity is v2.6.1 (too old)
- Decided to implement the key BOLD IQMs ourselves in pure Python

---

### 3. New script: `scripts/iqm.py`
Computes 4 image quality metrics per subject:

| Metric | What it measures | Output |
|---|---|---|
| **tSNR** | mean/std per voxel — signal quality | `tsnr_map.nii.gz`, `tsnr_map.png`, scalar in JSON |
| **CoV** | std/mean ×100% per voxel — noise fraction | `cov_map.nii.gz`, `cov_map.png`, scalar in JSON |
| **DVARS** | RMS frame-to-frame signal change | `dvars.tsv`, `dvars_plot.png`, median + spike count in JSON |
| **GCOR** | Mean pairwise voxel correlation — global noise | scalar in JSON |

Outputs saved to `results/<subject>/iqm/`:
- `iqm.json` — all scalar summaries
- `tsnr_map.nii.gz` + `tsnr_map.png`
- `cov_map.nii.gz` + `cov_map.png`
- `dvars.tsv` + `dvars_plot.png`

Brain mask: intensity threshold — 10% × 95th percentile of mean volume. No FSL/ANTs needed.

Example values for sub-64927: tSNR=17.78, CoV=5.62%, DVARS median=43.30, spikes=6, GCOR=0.0042

Documentation: `docs/iqm.md`

---

### 4. `scripts/batch_qc.py` — major updates

**Per-analysis incremental logic:**
- Old: if any analysis done → skip whole subject
- New: checks each of the 3 analyses independently, runs only what's missing
- Functions: `visualise_bold_done()`, `slice_qc_done()`, `iqm_done()`

**`--all` flag:**
```bash
python scripts/batch_qc.py --all
```
Auto-discovers all subjects in `data/WAND/` that have `ses-06/func/` (153 subjects found). Subjects without that session are silently skipped.

**Run logging:**
- Every run writes a timestamped JSON log to `logs/batch_qc_YYYY-MM-DD_HHMMSS.json`
- Records: run metadata, per-subject status, per-analysis status (ran / already_done / not_run), duration, error messages on failure
- Log path printed at end of every run

---

### 5. Current run in progress
Started via tmux:
```bash
tmux new -s wand_qc
conda activate wand
python scripts/batch_qc.py --all
```
Running all 153 subjects with ses-06/func/. Already completed: sub-64927, sub-43766, sub-68443, sub-73378, sub-73512 (all 3 analyses). Remaining ~148 subjects processing sequentially.

To reattach:
```bash
tmux attach -t wand_qc
```

---

## What to do next (after the batch run finishes)

1. **Check the log** — `ls logs/` and inspect the JSON for any failed subjects
2. **Re-run failures** — `python scripts/batch_qc.py sub-XXXXX` for any that errored

3. **FSL brain mask validation** — test whether BET+FLIRT mask explains the ~35% tSNR gap vs MRIQC:
   - Re-fetch one subject's BOLD (e.g. sub-64927): `python scripts/batch_qc.py sub-64927 --force`
   - Run BET on the MP2RAGE inv-2 structural, register mean BOLD → structural with FLIRT, warp mask to BOLD space
   - Compute tSNR in Python using the FSL mask
   - Three-way comparison: our intensity threshold vs FSL mask vs MRIQC
   - If FSL mask ≈ MRIQC value → mask is the full explanation; confirms MRIQC TSV is the gold standard

4. **Group-level QC script** — build on top of the MRIQC TSV (`data/WAND/derivatives/mriqc/analysis/ses-06_task-rest_bold.tsv`) rather than our iqm.json:
   - 152 subjects, 45 metrics, already computed
   - Key metrics to focus on: `tsnr`, `fd_mean`, `fd_num`, `dvars_std`, `gcor`, `efc`
   - Plot distributions using median ± IQR (not mean ± std)
   - Flag outliers beyond 1.5× IQR
   - Output a group-level exclusion recommendation list

5. **MRIQC** — worth emailing IT to ask for Apptainer (modern Singularity). One container pull and MRIQC runs natively on BIDS data.

---

## Key findings this session

- **FSL 6.0.7 is installed** at `/usr/local/apps/fsl_6.0.7/bin/` — `bet`, `flirt`, `convert_xfm`, `fslmaths` all available. Session notes from before were wrong about this.
- **MRIQC already run by data providers** — `data/WAND/derivatives/mriqc/analysis/ses-06_task-rest_bold.tsv` has 152 subjects × 45 metrics including tSNR, FD, DVARS, GCOR.
- **Our tSNR is systematically ~35% lower than MRIQC's** (median diff = -36.6%, stdev = 11%) — consistent across all 55 subjects compared. Almost certainly due to our loose intensity-threshold brain mask including skull/background voxels. The subject ranking is preserved but absolute values are not reliable.
- **Our iqm.py is largely redundant** given the MRIQC TSV. Visual QC outputs (visualise_bold.py, slice_qc.py) remain valuable — those are not in the derivatives.

---

## Key file locations

| File | Purpose |
|---|---|
| `scripts/visualise_bold.py` | Spatial QC — 4 plots, saves mean/std NIfTI |
| `scripts/slice_qc.py` | Slice-level QC — 5 plots, saves slicemean.npy |
| `scripts/iqm.py` | Image quality metrics — tSNR, CoV, DVARS, GCOR |
| `scripts/batch_qc.py` | Full pipeline — download → QC → drop, with logging |
| `docs/visualise_bold.md` | Documentation for visualise_bold.py |
| `docs/slice_qc.md` | Documentation for slice_qc.py |
| `docs/iqm.md` | Documentation for iqm.py |
| `logs/` | JSON run logs, one per batch_qc.py invocation |
| `results/<subject>/visualise_bold/` | Spatial QC outputs |
| `results/<subject>/slice_qc/` | Slice QC outputs |
| `results/<subject>/iqm/` | IQM outputs |
