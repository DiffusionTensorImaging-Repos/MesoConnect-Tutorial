---
sidebar_position: 2
title: "Tract families and ROIs"
---

# Tract families and ROIs

The atlas has ten tract families. Every one runs through the same nine-step workflow; what changes is the seed, the target, the atlas file, and which exclusions mattered when the atlas itself was built (those are already baked into the atlas corridor, but knowing them tells you where a reconstruction is likely to wander if the corridor is too loose).

## Families

| Family | Files (L / R) | Seed | Target | Notes from atlas construction |
|---|---|---|---|---|
| VTA → posterior (body) hippocampus | `l_vta_l_hipp`, `r_vta_r_hipp` | VTA | hippocampus | Excluded fornix, optic tract and nerve, amygdala, ventral pallidum, accumbens, dorsal striatum, thalamus, cortex and cerebellum, brainstem below the VTA, red nucleus, contralateral hemisphere. A ventral secondary bundle appears in some subjects; see cleaning. |
| VTA → anterior hippocampus | `anterior_l_vta_l_hipp`, `anterior_r_vta_r_hipp` | VTA | hippocampus | Shares its course with the posterior tract for roughly the first 60 to 80 of 100 nodes, then diverges toward the anterior hippocampus. Same exclusions. |
| VTA → amygdala | `l_vta_l_amygdala`, `r_vta_r_amygdala` | VTA | amygdala (hippocampus subtracted) | The optic tract exclusion is essential; without it streamlines route through it. Fornix excluded. |
| Superior VTA → nucleus accumbens | `superior_l_vta_l_accumbens`, `superior_r_vta_r_accumbens` | VTA | accumbens (ventral pallidum subtracted) | Superior and inferior splits are defined by anterior-commissure inclusion and exclusion masks; use them. |
| Inferior VTA → nucleus accumbens | `inferior_l_vta_l_accumbens`, `inferior_r_vta_r_accumbens` | VTA | accumbens | As above. |
| Ventral pallidum → VTA | `l_vp_l_vta`, `r_vp_r_vta` | ventral pallidum | VTA | Ventral pallidum split into hemispheres with the hemisphere masks. |
| Hippocampus → nucleus accumbens | `l_hipp_l_accumbens`, `r_hipp_r_accumbens` | hippocampus | accumbens | Cutoff 0.08 at 7 T in atlas construction; QuickBundles split into two clusters was often needed before cleaning. |
| Hippocampus → ventral pallidum | `l_hipp_l_vp`, `r_hipp_r_vp` | hippocampus | ventral pallidum | As above. |
| Precommissural fornix | TractSeg fornix ∩ hippocampus–accumbens overlap | | | Derived, not a corridor target. Currently in an HCP 1.05 mm grid; resample before use. |
| Postcommissural fornix | TractSeg fornix minus hippocampus–accumbens overlap | | | As above. |

The worked example on this site is the first two rows. The [downloads page](downloads) lists which files are packaged here now and which are pending from the full release.

## ROI sources

Seeds and targets are public atlases thresholded and binarized in MNI 1 mm space. If redistribution of a source is restricted, rebuild the ROI from the source and cite it.

| ROI | Source | File stem | Preparation |
|---|---|---|---|
| VTA | Trutti 7 T VTA atlas, 25% threshold | `left_VTA_0.25_bin`, `right_VTA_0.25_bin` | Red nucleus subtracted where they overlap; also subtracted from lateral hypothalamus and mammillary body exclusions. |
| Hippocampus | Harvard–Oxford, 50% threshold | `HPC_L_0.5_bin`, `HPC_R_0.5_bin` | |
| Amygdala | Harvard–Oxford, 50% | `amygdala_0.5_bin` → `left_amygdala_bin`, `right_amygdala_bin` | Hippocampus subtracted; split by hemisphere masks. |
| Nucleus accumbens (limbic striatum) | Tziortzi connectivity-based striatal parcellation (or FSL accumbens) | `left_accumbens_bin`, `right_accumbens_bin` | Ventral pallidum subtracted. |
| Ventral pallidum | Pauli subcortical atlas | `ventral_pallidum_bin` → `left_`, `right_` | Split by hemisphere masks. |
| SN/VTA (alternative) | Murty functional–anatomical SN/VTA masks | | Comparison resource for the dopaminergic midbrain. |

## Exclusion masks used to build the atlas

You do not need these to run the corridor workflow; the corridor replaces them. They are listed so you know what the atlas already rules out, and so you can add one back as an extra `-exclude` if a corridor reconstruction leaks somewhere specific.

- Thalamus; cortical gray matter and cerebellum (one mask); brainstem inferior to the VTA.
- Dorsal striatum: caudate plus putamen, with accumbens and ventral pallidum subtracted.
- Lateral hypothalamus and mammillary bodies, with the VTA subtracted.
- Red nucleus, with the VTA subtracted.
- Fornix body, with hippocampus and amygdala subtracted (VTA → hippocampus and VTA → amygdala).
- Optic tract and optic nerve, per hemisphere (VTA → hippocampus and VTA → amygdala).
- Contralateral hemisphere, to enforce ipsilateral tracking.
- Anterior commissure inclusion and exclusion, for the superior and inferior VTA → accumbens split.

The ROI tidying that produced these (subtractions, hemisphere splits) is in the reference pipeline script linked from the [scripts page](../reference/scripts).
