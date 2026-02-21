# WAND Analysis

Analysis of the [WAND fMRI dataset](https://git.cardiff.ac.uk/cubric/wand).

## Goals

1. Pedagogical introduction to fMRI analysis using WAND
2. Scientific analysis motivated by [Cichy et al. (2016), PNAS](https://www.pnas.org/doi/10.1073/pnas.1608282113)

## Setup

```bash
# 1. Clone this repo
git clone <this-repo> && cd WandAnalysis

# 2. Create virtual environment and install package
bash scripts/setup_env.sh
source .venv/bin/activate

# 3. Configure local paths
cp configs/paths.example.yaml configs/paths.yaml
# Edit configs/paths.yaml with your local data paths
```

## Fetching Data

Download a single subject (requires datalad):

```bash
bash scripts/fetch_subject.sh sub-001
```

## Project Structure

```
WandAnalysis/
├── configs/        # Path and study config (paths.yaml is gitignored)
├── data/           # Do not commit raw data here
├── manifests/      # Subject lists, run lists
├── notebooks/      # Exploratory analysis
├── results/        # Outputs (figures, stats)
├── scripts/        # Bash scripts for setup and data fetching
└── src/
    └── wand_analysis/  # Python package
```
