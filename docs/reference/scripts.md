---
sidebar_position: 4
title: "Scripts"
---

# Scripts

All scripts read one configuration file. Download the set, edit `00_config.sh`, and run in order.

| File | Step | Language |
|---|---|---|
| [00_config.sh](pathname:///MesoConnect-Tutorial/scripts/00_config.sh) | project paths, tract definition, parameters | bash |
| [01_register_mni_to_t1.sh](pathname:///MesoConnect-Tutorial/scripts/01_register_mni_to_t1.sh) | 1 | bash, ANTs |
| [02_warp_rois.sh](pathname:///MesoConnect-Tutorial/scripts/02_warp_rois.sh) | 2 | bash, ANTs, FSL |
| [03_build_corridor_mask.sh](pathname:///MesoConnect-Tutorial/scripts/03_build_corridor_mask.sh) | 3 | bash, FSL |
| [04_tune_cutoff.sh](pathname:///MesoConnect-Tutorial/scripts/04_tune_cutoff.sh) | 4 | bash, MRtrix |
| [04b_compare_cutoffs.py](pathname:///MesoConnect-Tutorial/scripts/04b_compare_cutoffs.py) | 4, figures and Dice | python |
| [05_tractography.sh](pathname:///MesoConnect-Tutorial/scripts/05_tractography.sh) | 5 | bash, MRtrix |
| [06_clean_bundles.py](pathname:///MesoConnect-Tutorial/scripts/06_clean_bundles.py) | 6 | python, pyAFQ, DIPY |
| [07_visual_qc.py](pathname:///MesoConnect-Tutorial/scripts/07_visual_qc.py) | 7 | python |
| [08_node_profiles.py](pathname:///MesoConnect-Tutorial/scripts/08_node_profiles.py) | 8 | python, DIPY |
| [permutation_one.R](pathname:///MesoConnect-Tutorial/scripts/permutation_one.R) | 9 | R |
| [09_stack_for_explorer.py](pathname:///MesoConnect-Tutorial/scripts/09_stack_for_explorer.py) | 9, Explorer input | python |
| [final_models.py](pathname:///MesoConnect-Tutorial/scripts/final_models.py) | whole-tract, quartile and subregion models for the example dataset | python, statsmodels |

```bash
mkdir -p mesoconnect_scripts && cd mesoconnect_scripts
for f in 00_config.sh 01_register_mni_to_t1.sh 02_warp_rois.sh 03_build_corridor_mask.sh 04_tune_cutoff.sh \
         04b_compare_cutoffs.py 05_tractography.sh 06_clean_bundles.py 07_visual_qc.py 08_node_profiles.py \
         09_stack_for_explorer.py permutation_one.R final_models.py; do
  curl -sSLO "https://diffusiontensorimaging-repos.github.io/MesoConnect-Tutorial/scripts/$f"
done
```

The example dataset's own per-step scripts, with its cluster paths and subject list, are in the [SDN-IMPACT-DTI repository](https://github.com/DiffusionTensorImaging-Repos/SDN-IMPACT-DTI), Steps 20 to 30 of the ReadMe.
