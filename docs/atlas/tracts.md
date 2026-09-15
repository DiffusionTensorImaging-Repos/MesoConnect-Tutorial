---
sidebar_position: 2
title: "Tract families and ROIs"
---

# Tract families and ROIs

The atlas contains ten tract families. All of them run through the same nine-step workflow. The seed, target and atlas file differ per family, as do the exclusion masks that were used to build the atlas. Those exclusions are already reflected in the atlas corridor; they are listed so that users know where a reconstruction is likely to leak if the corridor is dilated too far.

## Families

| Family | Files (left / right) | Seed | Target | Construction notes |
|---|---|---|---|---|
| VTA → posterior (body) hippocampus | `l_vta_l_hipp`, `r_vta_r_hipp` | VTA | hippocampus | Exclusions: fornix, optic tract and nerve, amygdala, ventral pallidum, accumbens, dorsal striatum, thalamus, cortex and cerebellum, brainstem below the VTA, red nucleus, contralateral hemisphere. A ventral secondary bundle appears in some subjects (see cleaning). |
| VTA → anterior hippocampus | `anterior_l_vta_l_hipp`, `anterior_r_vta_r_hipp` | VTA | hippocampus | Shares its course with the posterior tract for roughly the first 60 to 80 of 100 nodes. Same exclusions. |
| VTA → amygdala | `l_vta_l_amygdala`, `r_vta_r_amygdala` | VTA | amygdala (hippocampus subtracted) | Optic tract exclusion is required; without it streamlines enter the optic tract. Fornix excluded. |
| Superior VTA → nucleus accumbens | `superior_l_vta_l_accumbens`, `superior_r_vta_r_accumbens` | VTA | accumbens (ventral pallidum subtracted) | The superior and inferior divisions are defined by anterior-commissure inclusion and exclusion masks. |
| Inferior VTA → nucleus accumbens | `inferior_l_vta_l_accumbens`, `inferior_r_vta_r_accumbens` | VTA | accumbens | As above. |
| Ventral pallidum → VTA | `l_vp_l_vta`, `r_vp_r_vta` | ventral pallidum | VTA | Ventral pallidum split by hemisphere masks. |
| Hippocampus → nucleus accumbens | `l_hipp_l_accumbens`, `r_hipp_r_accumbens` | hippocampus | accumbens | Cutoff 0.08 at 7 T during construction. A QuickBundles split into two clusters was often required before cleaning. |
| Hippocampus → ventral pallidum | `l_hipp_l_vp`, `r_hipp_r_vp` | hippocampus | ventral pallidum | As above. |
| Precommissural fornix | TractSeg fornix ∩ hippocampus–accumbens overlap | | | Derived map, not a corridor target. Currently on an HCP 1.05 mm grid; resample before use. |
| Postcommissural fornix | TractSeg fornix minus hippocampus–accumbens overlap | | | As above. |

The example dataset on this site covers the first two rows. The [downloads page](downloads) lists which files are packaged now.

## ROI sources

Seeds and targets are public atlases thresholded and binarized in MNI 1 mm space. Where a source cannot be redistributed, rebuild the ROI from the source and cite it.

| ROI | Source | File stem | Preparation |
|---|---|---|---|
| VTA | Trutti et al. 7 T VTA atlas, 25% threshold | `left_VTA_0.25_bin`, `right_VTA_0.25_bin` | Red nucleus subtracted where they overlap. The VTA is also subtracted from the lateral hypothalamus and mammillary body exclusion masks. |
| Hippocampus | Harvard–Oxford, 50% threshold | `HPC_L_0.5_bin`, `HPC_R_0.5_bin` | |
| Amygdala | Harvard–Oxford, 50% threshold | `amygdala_0.5_bin` → `left_amygdala_bin`, `right_amygdala_bin` | Hippocampus subtracted; split by hemisphere masks. |
| Nucleus accumbens (limbic striatum) | Tziortzi et al. connectivity-based striatal parcellation, or FSL accumbens | `left_accumbens_bin`, `right_accumbens_bin` | Ventral pallidum subtracted. |
| Ventral pallidum | Pauli et al. subcortical atlas | `ventral_pallidum_bin` → `left_`, `right_` | Split by hemisphere masks. |
| SN/VTA (alternative) | Murty et al. functional–anatomical SN/VTA masks | | Comparison resource for the dopaminergic midbrain. |

## Exclusion masks used during atlas construction

These are not required for the corridor workflow. They are listed so that users know what the atlas already excludes, and so that any one of them can be added back as an extra `-exclude` if a reconstruction leaks into a specific structure.

- Thalamus; cortical gray matter with cerebellum (one mask); brainstem inferior to the VTA.
- Dorsal striatum: caudate and putamen, with accumbens and ventral pallidum subtracted.
- Lateral hypothalamus and mammillary bodies, with the VTA subtracted.
- Red nucleus, with the VTA subtracted.
- Fornix body, with hippocampus and amygdala subtracted (VTA → hippocampus and VTA → amygdala).
- Optic tract and optic nerve, per hemisphere (VTA → hippocampus and VTA → amygdala).
- Contralateral hemisphere, to enforce ipsilateral tracking.
- Anterior commissure inclusion and exclusion masks, for the superior and inferior VTA → accumbens division.

The ROI tidying commands (subtractions, hemisphere splits) are in the reference pipeline script linked from the [scripts page](../reference/scripts).
