---
sidebar_position: 4
title: "Scripts"
---

# Scripts

Each script appears in full on the workflow page for its step. Table 1 lists the set in run order. All scripts read a single configuration file, `00_config.sh`, which is edited once per project. The shell scripts source it themselves; the Python and R scripts read the exported settings, so `source 00_config.sh` is run in the shell before they are called, and again after every edit to the file. Each shell script writes a log to `$OUT/logs/`. Steps 0b, 1, 2, 3, 5, 6, 7 and 8a skip participants whose output already exists (`FORCE=1` recomputes); Steps 4, 8, 8b and 9 recompute on every run. Missing inputs are reported by participant.

**Table 1**

*Scripts, in Run Order*

| File | Step | Requires |
|---|---|---|
| `00_config.sh` | Project paths, tract definition, parameters, covariate list | bash |
| `00b_fod_estimation.sh` | 0b. Fibre orientation distributions, when preprocessing ended at the tensor | MRtrix3 |
| `01_register_mni_to_t1.sh` | 1. Registration | ANTs |
| `02_warp_rois.sh` | 2. Warping of seed, target and atlas | ANTs, FSL |
| `03_build_corridor_mask.sh` | 3. Corridor and exclusion mask | FSL |
| `04_tune_cutoff.sh` | 4. Pilot sweep of the cutoff | MRtrix3 |
| `04b_compare_cutoffs.py` | 4. Side-by-side images, Dice overlap, summary table | Python, MRtrix3 |
| `05_tractography.sh` | 5. Tractography | MRtrix3 |
| `06_clean_bundles.py` | 6. Cleaning; streamline count and length of the cleaned bundle | Python, pyAFQ, DIPY |
| `07_visual_qc.py` | 7. Overlay images and flags | Python, MRtrix3 |
| `08a_noddi_fit.py` | 8. NODDI fit | Python, AMICO |
| `08_node_profiles.py` | 8. Along-tract profiles | Python, DIPY |
| `08b_build_analysis_csv.py` | 8. Analysis files for Step 9 | Python |
| `09a_tract_models.py` | 9. Whole-tract and quartile models | Python, statsmodels |
| `09b_nodewise_permutation.R` | 9. Node-wise permutation test | R |
| `09c_stack_for_explorer.py` | 9. Explorer input | Python |

*Note.* NODDI = neurite orientation dispersion and density imaging.

The complete set can be retrieved with the following command.

```bash
mkdir -p mesoconnect_scripts && cd mesoconnect_scripts
base="https://diffusiontensorimaging-repos.github.io/MesoConnect-Tutorial/scripts"
for f in 00_config.sh 00b_fod_estimation.sh 01_register_mni_to_t1.sh 02_warp_rois.sh \
         03_build_corridor_mask.sh 04_tune_cutoff.sh 04b_compare_cutoffs.py \
         05_tractography.sh 06_clean_bundles.py 07_visual_qc.py 08a_noddi_fit.py \
         08_node_profiles.py 08b_build_analysis_csv.py 09a_tract_models.py \
         09b_nodewise_permutation.R 09c_stack_for_explorer.py; do
  curl -sSLO "$base/$f"
done
```

## Validation status

The scripts generalize those used to process the example dataset. Before release they were run from Step 0b to Step 8b on three participants of that dataset and compared with the outputs the dataset's own scripts had produced: warped regions and corridors overlapped at Dice ≥ .93, cleaned streamline counts and lengths agreed within the run-to-run variability of tractography, NODDI maps were identical, and along-tract profiles correlated at *r* ≥ .94 across nodes. The group-level scripts reproduce that dataset's whole-tract, quartile and node-wise results. The run used MRtrix3 3.0.7, FSL 6.0.5.1, ANTs 2.3.5, Python 3.8, DIPY 1.8.0, pyAFQ 1.3.5, AMICO 2.1.1 and R 4 on Linux.

The scripts from which these were generalized are in the [SDN-IMPACT-DTI repository](https://github.com/DiffusionTensorImaging-Repos/SDN-IMPACT-DTI).
