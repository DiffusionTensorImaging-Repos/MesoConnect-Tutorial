---
sidebar_position: 1
title: "Every parameter"
---

# Every parameter in one place

| Step | Parameter | Atlas construction (7 T) | 3 T example | Notes |
|---|---|---|---|---|
| Atlas | threshold | 50% | 50% | 25% fallback for a short or broken core. |
| Registration | tool | `antsRegistrationSyNQuick.sh` | same | Skull-stripped subject vs `MNI152_T1_1mm_brain`. |
| Warp | interpolation | nearest-neighbour | same | Linear for probabilistic maps, then threshold. |
| Corridor | dilation | 1 to 2 voxels | 2 | 4 if registration is uncertain. |
| Tracking | algorithm | iFOD2 (default) | same | |
| Tracking | `-cutoff` | 0.06 (VTA → hipp), 0.08 (hipp → NAcc) | 0.01 | MRtrix default 0.05. Pilot it. |
| Tracking | `-select` | 2500 | 2500 | |
| Tracking | `-seeds` | 25,000,000 | 25,000,000 | |
| Tracking | `-minlength` / `-maxlength` | 35 / 65 mm | 35 / 65 mm | Per tract family. |
| Tracking | `-seed_unidirectional`, `-stop` | on | on | |
| Tracking | ACT, backtrack, angle, step size | off / default | off / default | ACT failed with these masks. |
| Cleaning | `n_points`, `clean_rounds` | 100, 5 | same | |
| Cleaning | `distance_threshold`, `length_threshold` | 3, 2 | same | Mahalanobis SD, length SD. |
| Cleaning | QuickBundles threshold | 5 mm | not needed | For two-bundle tracts. |
| QC flags | voxels, density | | under 50, over 5000, max under 5 | |
| Profiles | nodes | 100 | 100 | Trim 0 to 4 and 95 to 99 if you decide to. |
| Profiles | weighting | Gaussian (Mahalanobis) | same | |
| NODDI | dPar white matter / gray matter | 1.7e-3 / 1.1e-3 | same | Refit for gray-matter ROIs. |
| NODDI | maps | modulated NDI, ODI; plain FWF | same | |
| Stats | permutations | 5000 | 5000 | Freedman–Lane. |
| Stats | cluster rule | extent ≥ 95th pct of null max | same | α = .05 per node. |
| Stats | covariates | | ICV, length, count, motion, age | Count is collinear with NDI; decide a priori. |
