---
sidebar_position: 1
title: "Workflow overview"
---

# Workflow overview

Nine steps, run one tract at a time. Steps 1 and 2 are per subject and are reused across tracts. Steps 3 to 9 repeat for each tract by re-sourcing the configuration with a different seed, target and atlas file.

```mermaid
flowchart TD
  A[Preprocessed DWI and T1<br/>TUBRIC or QSIPrep] --> B[1 Register MNI to T1<br/>ANTs SyN]
  B --> C[2 Warp seed, target, atlas<br/>nearest-neighbour, binarize]
  C --> D[3 Corridor mask<br/>dilate, add seed and target, invert]
  D --> E[4 Cutoff selection<br/>sweep on pilot subjects, inspect]
  E --> F[5 Tractography<br/>tckgen through the corridor]
  F --> G[6 Bundle cleaning<br/>pyAFQ Mahalanobis; QuickBundles if needed]
  G --> H[7 Visual QC<br/>TDI overlays, automatic flags]
  H --> I[8 Node profiles<br/>orient, 100 nodes, FA and NODDI]
  I --> J[9 Node-wise statistics<br/>Freedman–Lane cluster FWE]
  J --> K[Explorer]
```

## Inputs per subject

| Input | Source | Path used by the scripts |
|---|---|---|
| Skull-stripped T1 | preprocessing | `$PROJECT/anat/<subj>/<subj>_T1w_brain.nii.gz` |
| Normalized white-matter FOD (`.mif`) | MRtrix MSMT-CSD and `mtnormalise` | `$PROJECT/dwi/<subj>/wm_fod_norm.mif` |
| Diffusion brain mask | preprocessing | `$PROJECT/dwi/<subj>/nodif_brain_mask.nii.gz` |
| T1 → diffusion matrix (only if the grids differ) | FLIRT | `$PROJECT/xfm/<subj>/str2diff.mat` |
| Scalar maps to profile | DTIFIT, AMICO NODDI | `$PROJECT/dwi/<subj>/fa.nii.gz`, `$PROJECT/noddi/<subj>/fit_*.nii.gz` |

If the T1 is already on the diffusion grid (as in HCP data), omit the matrix and the warp script resamples directly.

## Outputs

```
$OUT/<subj>/
  reg/          mni2t1_0GenericAffine.mat, mni2t1_1Warp.nii.gz, mni2t1_1InverseWarp.nii.gz
  rois/         <tract>_{seed,target,atlas}_{t1,diff}.nii.gz
                <tract>_atlas_dilated.nii.gz  <tract>_inclusion_zone.nii.gz  <tract>_exclusion_mask.nii.gz
  tckgen/<tract>/
                <tract>_pilot_<cutoff>.tck          (step 4)
                <tract>_<cutoff>.tck  <tract>_<cutoff>_cleaned.tck
$OUT/qc/<tract>/               per-subject overlay PNGs and flags
$OUT/qc/<tract>_cutoff_pilot/  side-by-side cutoff panels, cutoff_summary.csv
$OUT/nodewise/                 <tract>_nodewise_all_subjects.csv  (Subject, Tract, Node, FA, NDI, ODI, FWF)
```

Keep a manifest per analysis recording atlas version and threshold, dilation, interpolation, transform files, cutoff, scalar maps, covariates and software versions.

## Running the scripts

Every script sources `00_config.sh`. Edit that file once for the project, then change `TRACT`, `SEED_MNI`, `TARGET_MNI` and `ATLAS_MNI` for each tract.

```bash
cd scripts
nano 00_config.sh
bash 01_register_mni_to_t1.sh
bash 02_warp_rois.sh
bash 03_build_corridor_mask.sh
bash 04_tune_cutoff.sh "s001 s002 s003 s004 s005" "0.1 0.08 0.06 0.01"
python 04b_compare_cutoffs.py "s001 s002 s003 s004 s005" "0.1 0.08 0.06 0.01"
bash 05_tractography.sh
python 06_clean_bundles.py
python 07_visual_qc.py
python 08_node_profiles.py
```

Steps 1 and 5 take hours on a full sample and should run under `tmux` or a job scheduler. The parallelism limits in the scripts were set for a shared 48-core node; lower them on a workstation.
