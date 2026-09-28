---
sidebar_position: 3
title: "Tract families and regions of interest"
---

# Tract families and regions of interest

The atlas contains seven bilateral pathways (Table 1). Each is processed with the same nine-step workflow; only the seed, target and atlas file change. The exclusion masks used during atlas construction are already reflected in each atlas map. They are listed here so that users can anticipate where a reconstruction may leak when the corridor is dilated too far. Throughout, the ventral tegmental area is abbreviated VTA, the nucleus accumbens NAc, the ventral pallidum VP, and a region of interest ROI.

**Table 1**

*Pathways in the MesoConnect Atlas*

| Pathway | Grouping | File stem (left / right) | Seed | Target | Notes |
|---|---|---|---|---|---|
| VTA → posterior hippocampus | Motivated memory | `left_vta_posterior_hpc`, `right_vta_posterior_hpc` | VTA | posterior hippocampus | The example dataset's primary tract. A ventral secondary bundle occurs in some participants (see Step 6). |
| VTA → anterior hippocampus | Motivated memory | `left_vta_anterior_hpc`, `right_vta_anterior_hpc` | VTA | anterior hippocampus | Shares its course with the posterior pathway for roughly the first 60 to 80 of 100 nodes. |
| VTA → amygdala | Motivated salience and learning | `left_vta_amygdala`, `right_vta_amygdala` | VTA | amygdala | Fornix and hippocampus exclusions. |
| Inferior VTA → NAc | Motivated salience and learning | `left_inferior_vta_nac`, `right_inferior_vta_nac` | VTA | NAc | Inferior and superior divisions are separated by different anterior-commissure exclusions. |
| Superior VTA → NAc | Motivated salience and learning | `left_superior_vta_nac`, `right_superior_vta_nac` | VTA | NAc | As above. |
| Hippocampus → NAc → VP | Regulation of motivated behaviour | `left_hpc_nac_vp`, `right_hpc_nac_vp` | hippocampus | VP, with the NAc as a required waypoint | Frequently reconstructs as two bundles; see Step 6. |
| VP → VTA | Regulation of motivated behaviour | `left_vp_vta`, `right_vp_vta` | VP | VTA | |

*Note.* File stems are those of the atlas package (`<stem>_mni152_1mm_thr50.nii.gz` and `<stem>_mni152_1mm_overlap_prop.nii.gz`). The atlas-generation settings of each pathway are on the [construction page](construction); the number of contributing participants is listed there as well.

## Regions of interest

Seeds and targets are derived from published atlases, thresholded and binarized in Montreal Neurological Institute (MNI) 1 mm space (Table 2). The atlas package does not redistribute them; the [downloads page](downloads) gives their sources and provides the VTA and hippocampus regions used in the example dataset.

**Table 2**

*Sources and Preparation of the Regions of Interest*

| Region | Source | Preparation |
|---|---|---|
| VTA | 7 T probabilistic VTA atlas (Trutti et al., 2021), 25% threshold | Used unmodified; the VTA is subtracted from the red-nucleus, lateral-hypothalamus and mammillary-body exclusion masks. |
| Hippocampus | Harvard–Oxford subcortical atlas (Frazier et al., 2005; Makris et al., 2006), 50% threshold | Anterior and posterior divisions for the two VTA → hippocampus pathways. |
| Amygdala | Harvard–Oxford subcortical atlas | Hippocampus subtracted; divided by hemisphere masks. |
| Nucleus accumbens | Harvard–Oxford subcortical atlas | Ventral pallidum subtracted. |
| Ventral pallidum | Subcortical atlas (Pauli et al., 2018) | Divided by hemisphere masks. |
| SN/VTA (alternative) | Functional–anatomical SN/VTA masks (Murty et al., 2014) | Comparison resource for the dopaminergic midbrain; not the VTA region used for the atlas. |

*Note.* SN = substantia nigra.

## Exclusion masks used during atlas construction

The corridor workflow does not require these masks. They are listed so that users know what the atlas already excludes and can reintroduce any of them as an additional `-exclude` argument if a reconstruction enters a specific structure.

- Thalamus; cortical gray matter with cerebellum (single mask); inferior brainstem.
- Dorsal striatum: caudate and putamen, with accumbens and ventral pallidum subtracted.
- Lateral hypothalamus and mammillary bodies, with the VTA subtracted.
- Red nucleus, with the VTA subtracted.
- Fornix body, with hippocampus and amygdala subtracted (VTA → hippocampus and VTA → amygdala).
- Ipsilateral off-target regions of the circuit, per pathway (for example the ventral pallidum and striatum for VTA → hippocampus, the hippocampus for VTA → NAc).
- Contralateral hemisphere and contralateral target, enforcing ipsilateral tracking.
- Two anterior-commissure exclusion masks, one per division, defining the superior and inferior VTA → NAc pathways.

The ROI preparation script (`prepare_rois.sh`) and the tractography commands with these masks are in the atlas repository's [`analysis-code` folder](https://github.com/blelliott23/MesoConnect/tree/main/analysis-code).
