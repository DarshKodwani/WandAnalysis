# WAND Analysis

Analysis scripts for the WAND 7T resting-state fMRI dataset (CUBRIC).

---

## Getting started

Run once from the folder containing this README:

```bash
bash firstTimeSetup.sh
```

This installs Miniconda (if needed), creates the `wand` conda environment with all dependencies, and configures read-only access to the WAND dataset via the bundled deploy key. No GIN account required.

Then in any new terminal:

```bash
conda activate wand
```

---

## Downloading data

```bash
# Download one subject's func folder
bash scripts/download.sh sub-00395 ses-06 func

# Download a wider scope (session, or whole subject)
bash scripts/download.sh sub-00395 ses-06
bash scripts/download.sh sub-00395

# Check what's currently downloaded (and how much disk it's using)
bash scripts/find_downloaded.sh
```

Subject IDs are in `data/WAND/participants.tsv`.

---

## Running the QC pipeline

**Batch mode (recommended)** — processes all subjects one at a time, downloads each subject's BOLD file, runs all three analyses, then frees the disk space before moving to the next:

```bash
python scripts/batch_qc.py --all
```

**Single subject:**

```bash
python scripts/batch_qc.py sub-00395
```

**Run individual scripts directly:**

```bash
python scripts/visualise_bold.py sub-00395
python scripts/slice_qc.py sub-00395
python scripts/iqm.py sub-00395
```

Results are saved to `results/<subject>/`.  
Batch run logs are saved to `logs/`.

---

## Folder structure

```
firstTimeSetup.sh           # One-time environment + GIN key setup
scripts/
    utils.py                # Shared constants and helpers (imported by all scripts)
    batch_qc.py             # Batch pipeline: download → analyse → free disk → next
    visualise_bold.py       # Mean/std/carpet/mosaic plots
    slice_qc.py             # Slice-mean QC (equivalent to standard MATLAB script)
    iqm.py                  # Image quality metrics (tSNR, CoV, DVARS, GCOR)
    download.sh             # Manual data download helper
    find_downloaded.sh      # Show what raw data is currently on disk
data/WAND/                  # WAND dataset (git-annex; pointer files until downloaded)
results/                    # Analysis outputs, organised by subject
logs/                       # JSON logs from batch_qc.py runs
```
