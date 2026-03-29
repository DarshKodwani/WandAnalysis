# WAND Analysis

[![Lint](https://github.com/DarshKodwani/WandAnalysis/actions/workflows/lint.yml/badge.svg?branch=main)](https://github.com/DarshKodwani/WandAnalysis/actions/workflows/lint.yml?query=branch%3Amain)
[![Tests](https://github.com/DarshKodwani/WandAnalysis/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/DarshKodwani/WandAnalysis/actions/workflows/tests.yml?query=branch%3Amain)
[![Python](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
[![Pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://pre-commit.com/)

Quality-control and metric analysis pipeline for the CUBRIC WAND resting-state fMRI dataset.

This repository is designed for:
- Running reproducible subject-level QC on BOLD data.
- Aggregating image quality metrics across subjects.
- Comparing MRIQC-derived metrics between 3T and 7T sessions.
- Supporting transparent methods development for research papers.

## What This Repo Does

Primary analyses:
- Subject-level spatial QC plots.
- Slice-wise temporal integrity QC.
- Image quality metrics (tSNR, CoV, DVARS, GCOR).
- Group summaries and 3T vs 7T comparisons.

Primary scripts:
- scripts/batch_qc.py: orchestrates end-to-end per-subject workflow.
- scripts/visualise_bold.py: mean/std images, carpet plot, middle-volume mosaic.
- scripts/slice_qc.py: slice mean heatmaps and FFT diagnostics.
- scripts/iqm.py: computes tSNR, CoV, DVARS, GCOR with maps and summary JSON.
- scripts/group_qc.py: group summaries from subject-level outputs.
- scripts/compare_3t_7t_mriqc.py: cross-session MRIQC metric comparisons.

## Quick Start

### Option A: First-time setup script (recommended for new users)

Run once from repo root:

```bash
bash firstTimeSetup.sh
```

This script:
- Installs Miniconda if needed.
- Creates conda environment named wand.
- Installs core dependencies and optional dev tooling.
- Configures GIN access.
- Optionally downloads WAND into data/WAND.

Then in every new shell:

```bash
conda activate wand
```

### Option B: Reproducible environment from file

```bash
conda env create -f environment.yml
conda activate wand
```

## Data Access and Downloading

Common data operations:

```bash
# Download one subject's resting-state functional data
bash scripts/download.sh sub-00395 ses-06 func

# Download an entire session
bash scripts/download.sh sub-00395 ses-06

# Download an entire subject tree
bash scripts/download.sh sub-00395

# Show which annex-backed files are currently downloaded locally
bash scripts/find_downloaded.sh
```

Subject metadata is in data/WAND/participants.tsv.

## Running Analyses

### Batch mode (recommended)

```bash
python scripts/batch_qc.py --all
```

Behavior:
- Discovers valid subjects for ses-06.
- Downloads required BOLD data if missing.
- Runs visualise_bold, slice_qc, iqm.
- Removes raw BOLD content afterward to conserve disk.
- Writes batch logs to logs/.

### Targeted runs

```bash
# One subject through full batch logic
python scripts/batch_qc.py sub-00395

# Subject list file (one subject id per line)
python scripts/batch_qc.py --file subjects.txt
```

### Individual script runs

```bash
python scripts/visualise_bold.py sub-00395
python scripts/slice_qc.py sub-00395
python scripts/iqm.py sub-00395
python scripts/group_qc.py
python scripts/compare_3t_7t_mriqc.py --metric tsnr
python scripts/compare_3t_7t_mriqc.py --metric snr
```

## Output Layout

Subject-level output:
- results/sub-XXXXX/visualise_bold/
- results/sub-XXXXX/slice_qc/
- results/sub-XXXXX/iqm/

Group-level output:
- results/group/

Logs:
- logs/batch_qc_YYYY-MM-DD_HHMMSS.json

## Repository Structure

```text
firstTimeSetup.sh                      # One-time setup + optional WAND download
environment.yml                        # Reproducible conda environment
.pre-commit-config.yaml                # Local quality hooks
.github/workflows/ci.yml               # CI: lint + tests

scripts/
    utils.py                             # Path helpers, BOLD validation/load
    batch_qc.py                          # End-to-end orchestrator
    visualise_bold.py                    # Spatial QC and carpet visualizations
    slice_qc.py                          # Slice-time QC diagnostics
    iqm.py                               # tSNR/CoV/DVARS/GCOR computations
    group_qc.py                          # Group-level tSNR summaries
    compare_3t_7t_mriqc.py               # 3T vs 7T MRIQC comparisons
    download.sh                          # Controlled data retrieval
    find_downloaded.sh                   # Local annex content check
    test_moco_tsnr.py                    # Motion-correction tSNR comparison experiment

data/
    WAND/                                # BIDS + derivatives (annex-backed)

results/
    sub-*/                               # Per-subject analysis outputs
    group/                               # Aggregate comparisons and plots

docs/
    paper/                               # Manuscripts and references
    *.md                                 # Analysis notes and summaries

tests/
    conftest.py                          # Test import path setup
    test_utils.py                        # File/path and I/O helper tests
    test_slice_qc.py                     # Slice QC numerical tests
    test_iqm_metrics.py                  # IQM metric correctness tests
    test_compare_3t_7t_mriqc.py          # MRIQC parsing/statistics tests
    test_cli_smoke.py                    # Script --help smoke tests
```

## Testing and Quality

This is a research codebase, so the goal is confidence and reproducibility rather than heavy software engineering overhead.

What is included:
- Unit-style tests for key numerical and parsing functions.
- CLI smoke tests for script entry points.
- Ruff linting.
- GitHub Actions CI on push and pull request.
- Optional local pre-commit hooks.

Run checks locally:

```bash
ruff check scripts tests
pytest -q
```

Enable local pre-commit hooks:

```bash
pre-commit install
pre-commit run --all-files
```

## CI Workflow

CI is defined in two workflows:
- .github/workflows/lint.yml for Ruff checks.
- .github/workflows/tests.yml for pytest.

Both workflows create the environment from environment.yml.

This gives fast feedback for code changes while staying lightweight for a research team.

## Suggested Contributor Workflow

1. Create or switch to a feature branch.
2. Make changes in scripts and or docs.
3. Run ruff and pytest locally.
4. Commit small, focused changes.
5. Push and open a PR.
6. Confirm CI is green before merge.

## Typical New-User Onboarding Path

1. Clone the repo and run firstTimeSetup.sh.
2. Activate conda environment wand.
3. Confirm data access using scripts/find_downloaded.sh.
4. Run one subject with scripts/batch_qc.py sub-XXXXX.
5. Inspect outputs in results/sub-XXXXX/.
6. Run group scripts when enough subjects are processed.

## Notes for Research Reproducibility

Recommended practice for analyses used in manuscripts:
- Keep scripts deterministic where possible.
- Preserve summary outputs in results/group/ for each analysis milestone.
- Track analysis assumptions in docs/.
- Use branches for major methodological changes.
- Keep CI and tests passing before using outputs in reporting.

## License and Data Access

Code in this repository is for research workflow support.
Dataset access and redistribution follow WAND and GIN policies.
