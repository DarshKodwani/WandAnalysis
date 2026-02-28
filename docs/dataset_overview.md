# WAND Dataset Overview

## What is WAND?

The **Welsh Advanced Neuroimaging Database (WAND)** is a large multi-modal neuroimaging dataset of healthy human brains, produced by [CUBRIC](https://www.cardiff.ac.uk/cardiff-university-brain-research-imaging-centre) (Cardiff University Brain Research Imaging Centre). It is publicly available via [GIN](https://gin.g-node.org/CUBRIC/WAND).

The dataset is unusual in its breadth — most neuroimaging studies use one or two scan types per subject. WAND collects eight distinct types of measurements from the same ~100+ individuals across 8 sessions, spanning three different scanners and imaging modalities. The goal is to understand the healthy brain at multiple spatial and temporal scales simultaneously.

**Subjects:** ~100 healthy adults  
**Organisation:** [BIDS](https://bids-specification.readthedocs.io/) (Brain Imaging Data Structure) — `data/WAND/sub-XXXXX/ses-XX/`  
**Storage:** Files managed via git-annex — large NIfTIs are pointers by default; downloaded on demand

---

## Session overview

| Session | Scanner | Primary modality | What it measures |
|---|---|---|---|
| ses-01 | MEG system | MEG | Brain electrophysiology: timing of neural activity |
| ses-02 | 3T Connectom (300 mT/m gradients) | DWI + qMRI | White matter microstructure |
| ses-03 | 3T standard | fMRI + ASL | Functional activity + cerebral blood flow |
| ses-04 | 7T | Structural MRI + MRS | Ultra-high-res anatomy + brain chemistry |
| ses-05 | 7T | Structural MRI + MRS | Repeat / additional MRS |
| ses-06 | 7T | fMRI (resting state) | Functional connectivity at 7T ← **our focus** |
| ses-07 | 3T standard | fMRI + ASL | Functional activity + blood flow (repeat) |
| ses-08 | TMS + MRI | TMS | Brain stimulation effects |

---

## ses-01 — MEG (Magnetoencephalography)

### What it is
MEG measures the tiny magnetic fields produced by electrical currents in neurons — not the blood-flow proxy that fMRI uses, but the actual electrical activity. A subject sits inside a helmet containing ~300 SQUID sensors (superconducting quantum interference devices), which are so sensitive they can detect fields a billion times weaker than the Earth's magnetic field.

### What it measures
Neural oscillations at millisecond timescale. Where fMRI has ~1–2 second time resolution, MEG has ~1 millisecond. You can see specific frequency bands (alpha: 8–12 Hz, beta: 13–30 Hz, gamma: >30 Hz) and ask what the brain is doing moment-to-moment during a task.

### Tasks in WAND ses-01
- **task-auditorymotor** — auditory-motor integration task
- **task-mmn** — Mismatch Negativity: passive auditory oddball paradigm, probes automatic change detection
- **task-resting** — resting state (eyes open/closed)
- **task-simon** — Simon task: tests response conflict (compatible vs incompatible stimulus-response mappings)
- **task-visual** — visual stimulation task

### File format
CTF MEG system. Each task is a `.ds` directory containing:
- `.meg4` — raw sensor timeseries (~1 GB per run)
- `.res4` — dataset header (metadata, channel info)
- `.acq` — acquisition parameters
- `MarkerFile.mrk` — event/trigger markers
- `headshape.pos` — digitised head shape (for co-registration to MRI)

### Practical use
MEG resting-state data can be analysed for power spectra, source localisation (beamforming), and functional connectivity in source space. The headshape file is used to co-register MEG sensor positions with the structural MRI, allowing you to infer where in the brain activity is coming from.

---

## ses-02 — Connectom DWI + Quantitative MRI

### Scanner
The 3T Connectom scanner has gradient coils 6× stronger than a clinical scanner (300 mT/m vs ~40–80 mT/m). This matters for diffusion MRI — stronger gradients let you probe smaller spatial scales of water diffusion, allowing measurement of axon diameters rather than just white matter tract orientation.

### T1w (Anatomical)

**What it is:** Standard structural MRI. T1 contrast means that white matter appears bright, grey matter appears mid-grey, and CSF appears dark. Gives high anatomical detail at ~1 mm resolution.

**What it measures:** Brain anatomy. Used mainly as a reference image for registering other scans.

**Practical use:** Brain extraction (BET), registration target, grey/white matter segmentation.

**File sizes:** ~15–30 MB (compressed NIfTI, 3D)

### VFA — Variable Flip Angle (mcDESPOT)

**What it is:** A quantitative T1 mapping technique. Multiple SPGR (Spoiled Gradient Recalled Echo) images are acquired at different flip angles. Rather than just giving you a "T1-weighted" image, VFA lets you compute the actual T1 relaxation time in ms at every voxel. The `acq-spgr`, `acq-spgrIR`, and `acq-ssfp` variants are part of the mcDESPOT framework for simultaneous T1 and T2 mapping.

**What it measures:** T1 and T2 relaxation times — physical tissue properties that reflect the water content, lipid content, and myelin density of each voxel.

**Practical use:** Myelin water fraction maps — a tissue-level marker of myelination. Used to study white matter integrity without needing diffusion MRI.

**File sizes:** ~15 MB per flip angle × several acquisitions

### QMT — Quantitative Magnetization Transfer

**What it is:** MT (Magnetisation Transfer) exploits the exchange between free water protons and protons bound to macromolecules (proteins, myelin). You apply an off-resonance RF pulse to partially saturate the bound pool, then measure how much that saturation transfers to the free water signal. By varying the flip angle (`flip-`) and MT offset frequency (`mt-`), you can fit a two-pool model.

**What it measures:** Properties of the bound proton pool, specifically the pool size ratio (PSR) — a sensitive marker of myelin content and axonal density, more specific than DTI-based metrics.

**Practical use:** Sensitive to early myelin changes in neurological conditions; used in MS research and for mapping myeloarchitecture.

**File sizes:** ~8–15 MB per volume × many acquisitions (the QMT protocol is large)

### DWI — Diffusion Weighted Imaging (AxCaliber + CHARMED)

**What it is:** DWI measures how water molecules diffuse through tissue. In white matter, diffusion is restricted by axon membranes and myelin sheaths, so the direction and rate of diffusion encodes information about tissue microstructure. The Connectom's strong gradients allow very high b-values (up to b=8000+ s/mm²), probing restricted diffusion within axons.

- **AxCaliber** (4 protocols, different gradient timings `t_bdelta`) — designed to estimate the axon diameter distribution by varying the diffusion time. Different delta values probe different spatial scales.
- **CHARMED** (Composite Hindered and Restricted Model of Diffusion) — combines hindered (extra-axonal) and restricted (intra-axonal) diffusion components to estimate axonal density and diameter.

**What it measures:** Axon diameter, axonal density at individual voxels ("microstructural imaging"). This is only feasible on the Connectom — conventional 3T scanners don't have strong enough gradients.

**Practical use:** White matter pathway characterisation beyond DTI (which only gives orientation and anisotropy). Potentially links microstructure to behaviour.

**File sizes:** DWI files are very large (~500 MB – 2 GB per protocol) — most are annex pointers in this clone unless explicitly downloaded. `.bval` and `.bvec` files (small text files) encode the b-values and gradient directions.

---

## ses-03 — 3T fMRI + ASL

### T1w / T2w (Anatomicals)

As described above. ses-03 includes both T1w and T2w. T2w gives bright CSF and is useful for detecting lesions and segmenting hippocampal subfields.

### BOLD fMRI — Blood Oxygen Level Dependent

**What it is:** The workhorse of functional neuroimaging. Oxygenated haemoglobin has different magnetic properties to deoxygenated haemoglobin (deoxyHb is paramagnetic). When a brain region becomes more active, local blood flow increases, washing in more oxyHb — this small signal change (~0.5–5%) is what fMRI detects.

**What it measures:** Proxy for neural activity — specifically, a haemodynamic response to neural events with ~2–6 second lag and ~1–2 second temporal resolution. 

**Tasks in ses-03:**
- `task-rest` — Resting-state fMRI: subject lies still. Used to map functional connectivity (correlated spontaneous fluctuations between regions).
- `task-categorylocaliser` — Localises category-selective cortex (faces, objects, scenes, bodies)
- `task-dotback` — Working memory / cognitive control task
- `task-reversallearning` — Reward learning paradigm

**Practical use:** Functional connectivity analysis, task activation maps, prediction of behaviour from brain activity patterns.

**File sizes (3T):** ~300–500 MB for a 10-minute resting-state run (4D: ~64³ voxels × 400 timepoints)

### ASL — Arterial Spin Labelling

**What it is:** ASL is a non-invasive alternative to PET for measuring cerebral blood flow (CBF). Radio-frequency pulses magnetically "label" (invert) water protons in arterial blood flowing into the brain. After a delay, those labelled protons arrive at tissue and alter the local MRI signal. Subtracting label images from control images gives a perfusion map.

**What it measures:** Absolute cerebral blood flow in ml/100g tissue/min — a physiological measurement, not just a signal change. Unlike BOLD which only gives relative changes, ASL gives you a quantitative CBF value.

**Files:**
- `cbf` — derived CBF map (output of ASL modelling)
- `m0scan` — equilibrium magnetisation reference image (needed to convert ASL signal to absolute CBF)
- `perf` folder — raw ASL data (label/control image pairs)
- `angio` — time-of-flight MR angiography (maps major blood vessels)

**Practical use:** CBF is elevated in regions with higher metabolic demand at rest (e.g. default mode network). Used to study vascular contributions to brain function and pathology.

**File sizes:** ~50–200 MB (3D volumes; much smaller than BOLD)

### fmap — Field Maps

**What it is:** EPI (Echo-Planar Imaging, the sequence used for BOLD and DWI) is fast but geometrically distorted — the brain appears stretched or compressed in the phase-encode direction due to B0 field inhomogeneities near air-tissue interfaces (sinuses, ear canals). Field maps measure this distortion directly so it can be corrected.

**Types:**
- `magnitude1`, `magnitude2`, `phasediff` — gradient-echo field map with two echo times. The phase difference between echoes encodes the B0 offset at each voxel.
- `dir-AP_epi`, `dir-PA_epi` — EPI field maps acquired in opposite phase-encode directions (anteroposterior vs posteroanterior). The geometric distortion flips between them, and TOPUP (FSL) uses this to estimate the true distortion field.

**File sizes:** ~5–20 MB each (3D)

---

## ses-04 — 7T Structural + MRS

### T1w at 7T

7T provides higher SNR and better grey/white matter contrast than 3T. However, B1 field inhomogeneity is severe — the RF transmit field becomes non-uniform across the brain at 7T, meaning some regions appear much brighter than others. This is why ses-04 uses the VFA approach and TB1map correction rather than a simple T1w sequence.

### TB1map — Transmit B1 Field Map

**What it is:** Measures the actual flip angle achieved at each voxel, which differs from the nominal flip angle due to B1 inhomogeneity at 7T. Without this correction, quantitative T1/T2 values would be spatially biased.

**What it measures:** B1+ (transmit field) efficiency at each voxel — essentially a correction map.

**Practical use:** Required for any quantitative MRI analysis at 7T (T1 mapping, qMT, etc.).

### MRS — Magnetic Resonance Spectroscopy

**What it is:** Instead of imaging (mapping signal across space), spectroscopy measures the chemical composition of a small region of interest — typically a 2×2×2 cm voxel. Different brain metabolites resonate at slightly different frequencies, producing a spectrum with identifiable peaks.

**Key metabolites:**
| Metabolite | Abbreviation | What it tells you |
|---|---|---|
| N-acetylaspartate | NAA | Neuronal integrity / density |
| Choline | Cho | Cell membrane turnover |
| Creatine | Cr | Energy metabolism (reference marker) |
| Glutamate / Glutamine | Glu/Gln | Excitatory neurotransmitter |
| GABA | GABA | Inhibitory neurotransmitter |
| Myo-inositol | mI | Glial cell marker |

**What it measures:** Absolute (or relative) concentrations of these metabolites in a specific brain region. Used to ask "how much GABA is in motor cortex?" rather than "what is activated?"

**File format:** `.mat` files (MATLAB) — not standard NIfTI. The spectra are 1D signals in frequency space, not images.

**Practical use:** MRS GABA levels correlate with BOLD signal variability, learning rates, and inhibitory function. Combining MRS with fMRI allows you to relate neurochemistry to functional connectivity.

**File sizes:** Small (~1–5 MB per voxel, but the raw FID data can be larger)

---

## ses-05 — 7T Additional Structural + MRS

Very similar to ses-04 — a second 7T session. Contains T1w and additional MRS measurements. Likely used to increase SNR via averaging or to target different brain regions for spectroscopy.

---

## ses-06 — 7T Resting-State fMRI ← Our Focus

This is the session we are analysing. Resting-state fMRI at 7T.

### MP2RAGE — Magnetization Prepared 2 Rapid Gradient Echoes

**What it is:** The 7T replacement for a standard T1w. At 7T, a conventional T1w image is severely affected by B1 inhomogeneity — the image is bright in the centre and dark at the periphery, making it hard to use for brain extraction or quantitative analysis. MP2RAGE acquires two inversion recovery images at different inversion times and combines them into a "UNI" (uniform) image that cancels out B1 effects.

**Files:** Two inversion images (`inv-1`, `inv-2`), each with magnitude and phase parts. 4 files minimum. The `acq-PSIR` variant (Phase-Sensitive Inversion Recovery) improves contrast using the phase information.

**What it measures:** Quantitative T1 map (once processed) + anatomically clean T1w contrast.

**Practical use:** Brain extraction at 7T (BET), registration target for BOLD, quantitative T1 relaxometry.

**File sizes:** ~15 MB (mag) + ~37 MB (phase) per inversion = ~100 MB total

### MEGRE — Multi-Echo Gradient Recalled Echo

**What it is:** A gradient-echo sequence acquired at 7 different echo times (TE). Signal decays with T2* (T2-star) relaxation — tissue-dependent, affected by iron content, myelin, and B0 inhomogeneity. By fitting the signal decay across the 7 echoes, you can compute a T2* map at every voxel.

**What it measures:** T2* relaxation time — sensitive to iron deposition (elevated in basal ganglia), myelin content, and local B0 distortions. Also used to derive the B0 field map via the phase images.

**Practical use:** Iron mapping, QSM (Quantitative Susceptibility Mapping), additional structural reference at 7T.

**File sizes:** ~17 MB (mag) + ~35 MB (phase) per echo × 7 echoes = ~350 MB total

### BOLD resting-state at 7T

**What it is:** Same principle as ses-03, but at 7T. The higher field strength gives ~2× the SNR of 3T, allowing finer spatial resolution or shorter acquisition times. The BOLD signal itself also benefits slightly from increased T2* contrast.

**Parameters:** 1.5 mm isotropic, TR = 1.5 s, ~400 volumes (~10 minutes), whole-brain coverage

**Alongside the BOLD:**
- `sbref` — Single Band Reference: a single high-SNR volume acquired with the same geometry but without simultaneous multi-slice acceleration. Used as a registration target and for distortion correction.
- `physio` — continuous cardiac and respiratory signals recorded during the scan. Used for RETROICOR physiological noise correction.

**File sizes:** ~705 MB (the full 4D BOLD), ~2 MB (sbref)

### fmap at 7T

Same types as ses-03 — AP/PA EPI, magnitude/phasediff, plus the `TB1map`. At 7T the B1 inhomogeneity makes the TB1map particularly important.

---

## ses-07 — 3T Functional + ASL (Longitudinal Repeat)

Essentially a repeat of ses-03 (3T fMRI + ASL), likely acquired at a different time point for test-retest reliability or longitudinal analysis. Contains:

- `bold` — functional tasks
- `cbf`, `m0scan`, `perf` — ASL perfusion
- `angio` — vascular imaging
- `T2starw` — T2*-weighted image (different from MEGRE — a single TE image used as anatomical reference)
- `fmap` — distortion correction

---

## ses-08 — TMS

**What it is:** TMS (Transcranial Magnetic Stimulation) uses brief, intense magnetic pulses delivered via a coil held against the scalp to non-invasively stimulate or suppress specific cortical regions. It is used to establish causal links (not just correlations) between brain regions and behaviour — if you disrupt motor cortex and hand performance suffers, that proves the causal role.

**WAND combination:** TMS is combined with concurrent measurements to examine how stimulation of one region affects activity elsewhere in the brain.

**File format:** `.mat` files (MATLAB) — not NIfTI. Stored in a `tms/` folder.

**File sizes:** Small (behavioural responses, timing files)

---

## Derivatives

Pre-computed outputs provided by the WAND team:

| Folder | Contents |
|---|---|
| `derivatives/hd-bet/` | T1w brain-extracted images + binary masks (ses-02 to ses-05), generated by HD-BET (deep learning BET) |
| `derivatives/mriqc/` | MRIQC quality metrics: T1w, T2w, and BOLD IQMs for all sessions; the `analysis/` subfolder has TSV tables ready to use |
| `derivatives/eddy_qc/` | DWI quality control outputs from FSL eddy (ses-02), including b0 brain masks |

---

## Summary: what we're actually using

Our scripts (`visualise_bold.py`, `slice_qc.py`, `iqm.py`, `batch_qc.py`) operate exclusively on **ses-06** resting-state BOLD data. Of the full WAND dataset, we download and process:

```
sub-XXXXX/ses-06/func/sub-XXXXX_ses-06_task-rest_bold.nii.gz  ← 4D BOLD (~700 MB)
sub-XXXXX/ses-06/func/sub-XXXXX_ses-06_task-rest_sbref.nii.gz ← reference volume (~2 MB)
```

Everything else in the dataset — the MEG, DWI, ASL, MRS, TMS — is untouched by our analysis. The MRIQC derivatives (`derivatives/mriqc/analysis/ses-06_task-rest_bold.tsv`) provide pre-computed QC metrics for 152 subjects and are used as a comparison benchmark for our own IQM outputs.
