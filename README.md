# WAND Analysis

Analysis scripts and environment setup for the WAND 7T neuroimaging dataset.

---

## Getting started

You only need to do this once.

**1. Run the setup script**

From the folder containing this README:

```bash
bash firstTimeSetup.sh
```

This will:
- Install Miniconda (if not already on your machine)
- Create a `wand` conda environment with all required packages
- Ask if you want to set up access to the WAND raw data — type `y`
- Set up the connection to the WAND dataset automatically (no account needed)
- Ask where you want the raw data to live on your machine (e.g. `/data/WAND`) — press Enter for the default

**2. Activate the environment**

In any new terminal, always start with:

```bash
conda activate wand
```

---

## Downloading subject data

Once setup is complete, use the fetch script to download data for a subject:

```bash
# Download all data for a subject
bash scripts/fetch_subject.sh sub-00395

# Download one modality only (anat, func, dwi, etc.)
bash scripts/fetch_subject.sh sub-00395 anat
```

See `data/WAND/participants.tsv` for the full list of subject IDs.

---

## Running the analysis scripts

Make sure the `wand` environment is active (`conda activate wand`), then:

```bash
# Visualise BOLD data for a subject
python scripts/visualise_bold.py sub-00395
```

Results are saved to the `results/` folder.

---

## Folder structure

```
firstTimeSetup.sh       # Run this first
scripts/                # Analysis and setup scripts
data/WAND/              # Raw WAND dataset (metadata only until you fetch subjects)
configs/                # Local path configuration (paths.yaml, created on first setup)
results/                # Analysis outputs
```
