# WAND Analysis

Analysis of the [WAND fMRI dataset](https://git.cardiff.ac.uk/cubric/wand).

## Goals

1. Pedagogical introduction to fMRI analysis using WAND
2. Scientific analysis motivated by [Cichy et al. (2016), PNAS](https://www.pnas.org/doi/10.1073/pnas.1608282113)

---

## 1. Environment Setup (one-time)

Requires [Miniconda](https://docs.conda.io/projects/miniconda/en/latest/).

```bash
# Clone this repo
git clone https://github.com/DarshKodwani/WandAnalysis && cd WandAnalysis

# Create the wand conda environment (includes git-annex)
bash scripts/setup_env.sh
conda activate wand

# Configure your local data paths
cp configs/paths.example.yaml configs/paths.yaml
# Edit configs/paths.yaml — set wand_raw to where you will clone the WAND GIN repo
```

---

## 2. Accessing the WAND Data

WAND is hosted on [GIN (G-Node)](https://gin.g-node.org/CUBRIC/WAND) — a git-annex
based system that lets you clone the full dataset tree **without downloading large files
upfront**. You only download the files you need, when you need them:

```bash
gin get-content <path-to-file-or-folder>
```

To remove downloaded content and free up space:
```bash
gin remove-content <path-to-file-or-folder>
```

### First-time GIN setup

```bash
# 1. Register at https://gin.g-node.org/user/sign_up

# 2. Install GIN CLI and log in
bash scripts/setup_gin.sh

# 3. Generate an SSH key if you don't have one
ssh-keygen -t ed25519 -C "your@email.com"

# 4. Add your public key at https://gin.g-node.org/user/settings/ssh
cat ~/.ssh/id_ed25519.pub   # copy this to GIN

# 5. Clone the WAND repo (metadata only — fast, no large files downloaded)
cd /path/to/your/data
gin get CUBRIC/WAND

# 6. Update configs/paths.yaml — set wand_raw to the cloned WAND directory
```

### Subject IDs

WAND subject IDs use 5-digit numbers, e.g. `sub-00395`, `sub-01187`. They are **not**
`sub-001` style. Check `data/WAND/participants.tsv` for the full list.

### Downloading a subject's data

```bash
cd /path/to/WAND

# Download one subject's 7T anatomical (ses-03/anat)
gin get-content sub-00395/ses-03/anat/sub-00395_ses-03_T1w.nii.gz

# Or use the helper script (downloads all files for a given modality folder)
bash scripts/fetch_subject.sh sub-00395 anat

# Remove content when done to free space
gin remove-content sub-00395/ses-03/anat/
```

### Session structure

| Session | Scanner | Contents |
|---------|---------|----------|
| `ses-01` | 3T | Structural, diffusion, resting-state fMRI |
| `ses-02` | Connectom (300mT/m) | Advanced diffusion |
| `ses-03` | 7T | High-resolution T1w, T2w, functional, fieldmaps |

---

## 3. Visualising Data

Once a subject's T1w is downloaded, visualise it with:

```bash
conda activate wand

# Display interactively
python scripts/visualise_t1w.py sub-00395

# Save PNGs to results/
python scripts/visualise_t1w.py sub-00395 --save
```

Outputs saved to `results/<subject>_ses-03_T1w_orthogonal.png` and
`results/<subject>_ses-03_T1w_mosaic.png`.

---

## Project Structure

```
WandAnalysis/
├── configs/
│   ├── paths.example.yaml  # Template — copy to paths.yaml and fill in
│   └── paths.yaml          # Your local paths (gitignored)
├── data/                   # Do not commit raw data — clone WAND here
├── manifests/              # Subject lists, run lists
├── notebooks/              # Exploratory analysis
├── results/                # Outputs: figures, stats (large files gitignored)
├── scripts/
│   ├── setup_env.sh        # Create conda environment
│   ├── setup_gin.sh        # Install GIN CLI and authenticate
│   ├── fetch_subject.sh    # Download one subject's data via gin get-content
│   └── visualise_t1w.py    # QC visualisation for T1w scans
└── src/
    └── wand_analysis/      # Python package
```
