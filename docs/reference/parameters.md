---
sidebar_position: 1
title: "Parameters"
---

# Parameters

**Table 1.** *Consolidated parameters for atlas construction (7 T) and the example dataset (3 T).*

| Step | Parameter | Atlas construction (7 T) | Example dataset (3 T) | Notes |
|---|---|---|---|---|
| Atlas | threshold | 50% | 50% | 25% when a warped core is short or discontinuous |
| Registration | tool | `antsRegistrationSyNQuick.sh` | same | Skull-stripped participant image against `MNI152_T1_1mm_brain` |
| Warping | interpolation | nearest-neighbour | same | Linear for probabilistic maps, then threshold |
| Corridor | dilation | 1 to 2 voxels | 2 | 4 when registration is uncertain |
| Tractography | algorithm | iFOD2 (default) | same | |
| Tractography | `-cutoff` | 0.06 (VTA → hippocampus); 0.08 (hippocampus → accumbens) | 0.01 | MRtrix3 default 0.05; determined by pilot |
| Tractography | `-select` | 2500 | 2500 | |
| Tractography | `-seeds` | 25,000,000 | 25,000,000 | |
| Tractography | `-minlength`, `-maxlength` | 35, 65 mm | 35, 65 mm | Per tract family |
| Tractography | `-seed_unidirectional`, `-stop` | on | on | |
| Tractography | ACT, backtrack, angle, step size | off / default | off / default | ACT did not reconstruct with these masks |
| Cleaning | `n_points`, `clean_rounds` | 100, 5 | same | |
| Cleaning | `distance_threshold`, `length_threshold` | 3, 2 | same | Mahalanobis SD; length SD |
| Cleaning | QuickBundles threshold | 5 mm | not used | For two-bundle tracts |
| Quality control | flags | | voxels < 50 or > 5,000; maximum density < 5 | |
| Profiling | nodes | 100 | 100 | End nodes 0 to 4 and 95 to 99 may be trimmed |
| Profiling | weighting | Gaussian (Mahalanobis) | same | |
| NODDI | intrinsic parallel diffusivity, white / gray matter | 1.7 / 1.1 × 10⁻³ mm²/s | same | Refit for gray-matter regions |
| NODDI | maps | modulated NDI and ODI; FWF | same | |
| Inference, whole tract | model | | mixed model with subregion term; LRT for interaction | one value per participant per tract |
| Inference, quartiles | segments and correction | | nodes 0–24, 25–49, 50–74, 75–99; FDR or max-statistic permutation | seed-end vs target-end contrast for uniformity |
| Inference, nodes | permutations | 5,000 | 5,000 | Freedman–Lane |
| Inference, nodes | cluster criterion | extent ≥ 95th percentile of null maximum | same | α = .05 per node |
| Inference | covariates | | ICV, length, count, motion, age | Count is collinear with NDI; decide in advance |
