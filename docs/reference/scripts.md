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

The scripts generalize those used to process the example dataset, in which every step completed for all 57 participants. The generalized set was run from Step 0b to Step 8b on three participants of that dataset (one tract, left posterior ventral tegmental area → hippocampus), starting from the preprocessed diffusion data and the skull-stripped T1 image, and its outputs were compared with those the example dataset's own scripts had produced for the same participants (Table 2). The group-level scripts, which need a full sample, were checked against the example dataset's stored results (Table 3). The run used MRtrix3 3.0.7, FSL 6.0.5.1, ANTs 2.3.5, Python 3.8.10, DIPY 1.8.0, pyAFQ 1.3.5, AMICO 2.1.1 and bash 5.0 on Linux, with four threads and one participant at a time; it took under an hour.

**Table 2**

*Generalized Scripts Compared With the Example Dataset's Outputs, Three Participants*

| Output | Agreement |
|---|---|
| Warped seed, target and atlas (Dice overlap) | .93 to .99 |
| Corridor (Dice overlap) | .98 to .99 |
| Pilot sweep, 0.06 versus 0.01: streamlines generated to reach 1,000 | 0.39 and 3.0 million versus 0.31 and 0.43 million; Dice between cutoffs .68 and .65 (.66 in the example dataset) |
| Tractography at 0.01 | 2,500 streamlines in all three; 0.8 to 1.3 million streamlines generated |
| Cleaned bundle, streamline count | 864, 886, 705 versus 857, 824, 733 |
| Cleaned bundle, mean length | within 0.4 mm |
| Quality-control overlays | No flags; bundles follow the expected arc |
| NODDI maps | Identical, voxel for voxel |
| Along-tract profiles (correlation across the 100 nodes) | FA .98; NDI .99 to 1.00; ODI .99; FWF .94 to 1.00 |

*Note.* Tractography is stochastic, so streamline counts and profiles are not expected to match exactly. NODDI = neurite orientation dispersion and density imaging; FA = fractional anisotropy; NDI = neurite density index; ODI = orientation dispersion index; FWF = free-water fraction.

**Table 3**

*Checks of the Group-Level Scripts*

| Script | Check | Result |
|---|---|---|
| `09a_tract_models.py` | Run on the analysis files of the example dataset | Reproduces the reported whole-tract and quartile estimates and interaction tests to three decimals |
| `09b_nodewise_permutation.R` | Run on an analysis file of the example dataset | Node-wise *t* values identical to the stored results; same clusters; identical output with one, three and four cores |
| `09c_stack_for_explorer.py` | Run on the outputs of `09b` | Explorer file written and loaded |
| `08b_build_analysis_csv.py` | Run in the three-participant test | Analysis files written for all four metrics |

Two defects surfaced during validation and are fixed in the distributed scripts: on bash 5.0 to 5.2 the shell steps stalled at the end of their first participant loop, and the mean streamline length was read from the wrong line of the `tckstats` output. The scripts were also reviewed independently; the defects found are recorded in the repository history.

The example dataset's own per-step scripts, with its cluster paths and participant list, are in the [SDN-IMPACT-DTI repository](https://github.com/DiffusionTensorImaging-Repos/SDN-IMPACT-DTI), Steps 20 to 30 of the ReadMe.
