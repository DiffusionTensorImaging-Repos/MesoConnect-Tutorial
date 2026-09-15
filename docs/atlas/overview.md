---
sidebar_position: 1
title: "Atlas overview"
---

# Atlas overview

The MesoConnect Atlas consists of group probabilistic maps of mesolimbic tracts generated from Human Connectome Project 7 T diffusion data using anatomically constrained probabilistic tractography, tract-specific exclusion masks, streamline cleaning and group-level probabilistic mapping. It is distributed in FSL MNI152 1 mm space (182 × 218 × 182 voxels).

The atlas describes plausible streamline trajectories. It does not establish monosynaptic connections, fibre directionality or neurotransmitter identity, and several components of the hippocampal–VTA loop are polysynaptic.

## File types

| Suffix | Contents | Typical use |
|---|---|---|
| `*_GroupMean_OverlapProp.nii.gz` | Probabilistic map. Each voxel holds the proportion of contributing subjects whose binarized tract included it (0 to 1). | Visualization, threshold selection, probability-weighted extraction. |
| `*_GroupMean_thr50.nii.gz` | Binary map of voxels present in at least 50% of subjects. | Corridor construction, whole-tract extraction, any step that needs a binary mask. |
| `*_GroupOverlapCount.nii.gz` | Count map. Each voxel holds the number of subjects whose tract included it. | Reporting subject overlap. Not intended for warping to individual subjects. |

The 50% threshold is the default for corridor construction. Higher thresholds (75%, 90%) reduce the map toward a single central streamline and no longer represent between-subject variation. The 25% threshold retains more extent and is appropriate when a warped 50% core is short or discontinuous.

## Uses

1. **Corridor-constrained tractography** (the workflow on this site). The warped, dilated atlas defines where subject tractography may travel. The streamlines are the subject's own. This is the method that supports node-wise analysis.
2. **Whole-tract extraction** ([appendix](../appendix/whole-tract)). A scalar map is averaged inside the warped atlas mask. Suitable for descriptive summaries. Spatial variation along the tract is lost.
3. **Atlas-guided synthetic streamlines** ([appendix](../appendix/synthetic-streamlines)). A centerline scaffold built inside the warped atlas is sampled at 100 nodes. Suitable when subject tractography fails in some participants. The scaffold is a coordinate system rather than a reconstruction, and the approach is less established.

## Spaces and interpolation

- Atlas space is FSL MNI152 1 mm unless stated otherwise. Native space refers to a subject's T1, diffusion or NODDI grid. Releases in MNI 2 mm and MNI152NLin2009cAsym are planned.
- Probabilistic maps are warped with linear interpolation and thresholded in native space. Binary maps are warped with nearest-neighbour interpolation. Spline interpolation is not appropriate for labels.
- In registration software the moving image is the one being transformed (here the atlas) and the fixed image is the target grid (the subject). The flag names vary between tools.
- Warped masks should be overlaid on the subject image and inspected before use.

## Interpretive limits

- A group atlas warped to native space does not substitute for subject-specific tractography when the research question depends on individual anatomy.
- Dilation increases sensitivity and reduces specificity. Use the smallest dilation that produces reliable tracking.
- Whole-tract averages are summary descriptors.
- Synthetic streamlines are sampling scaffolds and should be described as such.
