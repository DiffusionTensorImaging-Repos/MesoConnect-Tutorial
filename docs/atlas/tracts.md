---
sidebar_position: 2
title: "Tract families and regions of interest"
---

# Tract families and regions of interest

The atlas contains ten tract families. Each is processed with the same nine-step workflow; the seed, target and atlas file differ per family. The exclusion masks used during atlas construction are already reflected in each atlas corridor and are listed here so that users can anticipate where a reconstruction may leak when the corridor is dilated too far.

## Families

**Table 1.** *Tract families in the MesoConnect Atlas.*

| Family | Files (left / right) | Seed | Target | Construction notes |
|---|---|---|---|---|
| VTA → posterior (body) hippocampus | `l_vta_l_hipp`, `r_vta_r_hipp` | VTA | hippocampus | Exclusions: fornix, optic tract and nerve, amygdala, ventral pallidum, accumbens, dorsal striatum, thalamus, cortex and cerebellum, brainstem inferior to the VTA, red nucleus, contralateral hemisphere. A ventral secondary bundle occurs in some participants (see bundle cleaning). |
| VTA → anterior hippocampus | `anterior_l_vta_l_hipp`, `anterior_r_vta_r_hipp` | VTA | hippocampus | Shares its course with the posterior tract for approximately the first 60 to 80 of 100 nodes. Same exclusions. |
| VTA → amygdala | `l_vta_l_amygdala`, `r_vta_r_amygdala` | VTA | amygdala (hippocampus subtracted) | Optic tract exclusion is required. Fornix excluded. |
| Superior VTA → nucleus accumbens | `superior_l_vta_l_accumbens`, `superior_r_vta_r_accumbens` | VTA | accumbens (ventral pallidum subtracted) | Superior and inferior divisions are defined by anterior-commissure inclusion and exclusion masks. |
| Inferior VTA → nucleus accumbens | `inferior_l_vta_l_accumbens`, `inferior_r_vta_r_accumbens` | VTA | accumbens | As above. |
| Ventral pallidum → VTA | `l_vp_l_vta`, `r_vp_r_vta` | ventral pallidum | VTA | Ventral pallidum divided by hemisphere masks. |
| Hippocampus → nucleus accumbens | `l_hipp_l_accumbens`, `r_hipp_r_accumbens` | hippocampus | accumbens | Cutoff 0.08 at 7 T during construction. A QuickBundles division into two clusters was frequently required before cleaning. |
| Hippocampus → ventral pallidum | `l_hipp_l_vp`, `r_hipp_r_vp` | hippocampus | ventral pallidum | As above. |
| Precommissural fornix | TractSeg fornix ∩ hippocampus–accumbens overlap | | | Derived map, not a corridor target. Currently on an HCP 1.05 mm grid; resample before use. |
| Postcommissural fornix | TractSeg fornix minus hippocampus–accumbens overlap | | | As above. |

The example dataset covers the first two families. The [downloads page](downloads) lists the files packaged with this site.

## Regions of interest

Seeds and targets are derived from published atlases, thresholded and binarized in MNI 1 mm space (Table 2). Where a source cannot be redistributed, the region should be rebuilt from the source and the source cited.

**Table 2.** *Region-of-interest sources and preparation.*

| Region | Source | File stem | Preparation |
|---|---|---|---|
| VTA | Trutti et al. (2021) 7 T probabilistic VTA atlas, 25% threshold | `left_VTA_0.25_bin`, `right_VTA_0.25_bin` | Red nucleus subtracted where overlapping. The VTA is also subtracted from the lateral hypothalamus and mammillary body exclusion masks. |
| Hippocampus | Harvard–Oxford subcortical atlas (Frazier et al., 2005; Makris et al., 2006), 50% threshold | `HPC_L_0.5_bin`, `HPC_R_0.5_bin` | |
| Amygdala | Harvard–Oxford subcortical atlas, 50% threshold | `amygdala_0.5_bin` → `left_amygdala_bin`, `right_amygdala_bin` | Hippocampus subtracted; divided by hemisphere masks. |
| Nucleus accumbens (limbic striatum) | Tziortzi et al. (2014) connectivity-based striatal parcellation, or FSL accumbens | `left_accumbens_bin`, `right_accumbens_bin` | Ventral pallidum subtracted. |
| Ventral pallidum | Pauli et al. (2018) subcortical atlas | `ventral_pallidum_bin` → `left_`, `right_` | Divided by hemisphere masks. |
| SN/VTA (alternative) | Murty et al. (2014) functional–anatomical SN/VTA masks | | Comparison resource for the dopaminergic midbrain. |

## Exclusion masks used during atlas construction

The corridor workflow does not require these masks. They are listed so that users know what the atlas already excludes and can reintroduce any of them as an additional `-exclude` argument if a reconstruction enters a specific structure.

- Thalamus; cortical gray matter with cerebellum (single mask); brainstem inferior to the VTA.
- Dorsal striatum: caudate and putamen, with accumbens and ventral pallidum subtracted.
- Lateral hypothalamus and mammillary bodies, with the VTA subtracted.
- Red nucleus, with the VTA subtracted.
- Fornix body, with hippocampus and amygdala subtracted (VTA → hippocampus and VTA → amygdala).
- Optic tract and optic nerve, per hemisphere (VTA → hippocampus and VTA → amygdala).
- Contralateral hemisphere, enforcing ipsilateral tracking.
- Anterior commissure inclusion and exclusion masks, defining the superior and inferior VTA → accumbens divisions.

The region-tidying operations (subtractions and hemisphere divisions) are contained in the reference pipeline script linked from the [scripts page](../reference/scripts).
