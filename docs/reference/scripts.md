---
sidebar_position: 4
title: "Scripts"
---

# Scripts

All scripts read a single configuration file. The set is downloaded, `00_config.sh` is edited, and the scripts are run in order. Each step script writes a log to `$OUT/logs/`, skips participants whose output already exists (set `FORCE=1` to recompute), and reports missing inputs by participant.

**Table 1.** *Scripts distributed with this site.*

| File | Step | Language |
|---|---|---|
| [00_config.sh](pathname:///MesoConnect-Tutorial/scripts/00_config.sh) | Project paths, tract definition, parameters | bash |
| [00b_fod_estimation.sh](pathname:///MesoConnect-Tutorial/scripts/00b_fod_estimation.sh) | 0, FOD estimation when preprocessing ended at the tensor | bash, MRtrix3 |
| [01_register_mni_to_t1.sh](pathname:///MesoConnect-Tutorial/scripts/01_register_mni_to_t1.sh) | 1 | bash, ANTs |
| [02_warp_rois.sh](pathname:///MesoConnect-Tutorial/scripts/02_warp_rois.sh) | 2 | bash, ANTs, FSL |
| [03_build_corridor_mask.sh](pathname:///MesoConnect-Tutorial/scripts/03_build_corridor_mask.sh) | 3 | bash, FSL |
| [04_tune_cutoff.sh](pathname:///MesoConnect-Tutorial/scripts/04_tune_cutoff.sh) | 4 | bash, MRtrix3 |
| [04b_compare_cutoffs.py](pathname:///MesoConnect-Tutorial/scripts/04b_compare_cutoffs.py) | 4, comparison figures and Dice | Python |
| [05_tractography.sh](pathname:///MesoConnect-Tutorial/scripts/05_tractography.sh) | 5 | bash, MRtrix3 |
| [06_clean_bundles.py](pathname:///MesoConnect-Tutorial/scripts/06_clean_bundles.py) | 6 | Python, pyAFQ, DIPY |
| [07_visual_qc.py](pathname:///MesoConnect-Tutorial/scripts/07_visual_qc.py) | 7 | Python |
| [08a_noddi_fit.py](pathname:///MesoConnect-Tutorial/scripts/08a_noddi_fit.py) | 8, NODDI fit | Python, AMICO |
| [08_node_profiles.py](pathname:///MesoConnect-Tutorial/scripts/08_node_profiles.py) | 8 | Python, DIPY |
| [08b_build_analysis_csv.py](pathname:///MesoConnect-Tutorial/scripts/08b_build_analysis_csv.py) | 8, wide analysis file for inference | Python |
| [permutation_one.R](pathname:///MesoConnect-Tutorial/scripts/permutation_one.R) | 9 | R |
| [09_stack_for_explorer.py](pathname:///MesoConnect-Tutorial/scripts/09_stack_for_explorer.py) | 9, Explorer input | Python |
| [final_models.py](pathname:///MesoConnect-Tutorial/scripts/final_models.py) | Whole-tract, quartile and subregion models for the example dataset | Python, statsmodels |

```bash
mkdir -p mesoconnect_scripts && cd mesoconnect_scripts
for f in 00_config.sh 00b_fod_estimation.sh 01_register_mni_to_t1.sh 02_warp_rois.sh 03_build_corridor_mask.sh 04_tune_cutoff.sh \
         04b_compare_cutoffs.py 05_tractography.sh 06_clean_bundles.py 07_visual_qc.py 08a_noddi_fit.py 08_node_profiles.py 08b_build_analysis_csv.py \
         09_stack_for_explorer.py permutation_one.R final_models.py; do
  curl -sSLO "https://diffusiontensorimaging-repos.github.io/MesoConnect-Tutorial/scripts/$f"
done
```

The example dataset's own per-step scripts, with its cluster paths and participant list, are in the [SDN-IMPACT-DTI repository](https://github.com/DiffusionTensorImaging-Repos/SDN-IMPACT-DTI), Steps 20 to 30 of the ReadMe.
