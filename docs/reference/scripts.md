---
sidebar_position: 4
title: "Scripts"
---

# Scripts

Each script appears in full on the workflow page for its step. Table 1 lists the set in run order. All scripts read a single configuration file, `00_config.sh`, which is edited once per project. The shell scripts source it themselves; the Python and R scripts read the exported settings, so `source 00_config.sh` is run once in the shell before they are called. Each shell script writes a log to `$OUT/logs/`. Every script skips participants whose output already exists (`FORCE=1` recomputes) and reports missing inputs by participant.

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

The scripts generalize those used to process the example dataset, in which every step completed for all 57 participants. Table 2 records how each generalized script has been checked. Steps 0b to 5, and the two Python scripts that call `tckmap`, have not yet been run on imaging data in their generalized form; that run will be recorded here with the software versions used.

**Table 2**

*Checks Performed on the Generalized Scripts (Version 0.1)*

| Scripts | Check | Result |
|---|---|---|
| `09a_tract_models.py` | Run on the analysis files of the example dataset | Reproduces the reported whole-tract and quartile estimates, interaction tests included, to three decimals |
| `06_clean_bundles.py` | Run on synthetic bundles with planted outlier streamlines (pyAFQ 3.3, DIPY 1.12) | Outliers removed; resumes; covariate table written |
| `08_node_profiles.py` | Run on synthetic bundles, including bundles stored in reverse order | Node 0 at the seed end in every case; no missing values |
| `08a_noddi_fit.py` | Run on a synthetic multi-shell dataset (AMICO 2.1.1), white-matter and gray-matter diffusivity | All maps written; resumes. Multi-threaded fitting was unstable on macOS with Python 3.13 and stable with `NODDI_NTHREADS=1`; the example dataset was fitted with 12 threads on Linux |
| `08b_build_analysis_csv.py`, `09b_nodewise_permutation.R`, `09c_stack_for_explorer.py` | Run in sequence on the synthetic profiles with a planted association | Association recovered; null outcome null; Explorer file written |
| `00b` to `05` (shell) | Syntax check; run against stand-in executables to exercise logging, concurrency, resumption, missing-input handling and audit tables | Control flow correct; commands not yet executed on imaging data |
| `04b_compare_cutoffs.py`, `07_visual_qc.py` | Syntax check | Not yet run; both call `tckmap` |

The example dataset's own per-step scripts, with its cluster paths and participant list, are in the [SDN-IMPACT-DTI repository](https://github.com/DiffusionTensorImaging-Repos/SDN-IMPACT-DTI), Steps 20 to 30 of the ReadMe.
