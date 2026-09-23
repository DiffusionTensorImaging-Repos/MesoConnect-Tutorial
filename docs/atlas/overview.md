---
sidebar_position: 1
title: "Atlas overview"
---

# Atlas overview

The MesoConnect Atlas comprises group probabilistic maps of mesolimbic tracts connecting the ventral tegmental area (VTA), hippocampus, nucleus accumbens, ventral pallidum and amygdala. The maps were generated from Human Connectome Project (HCP) 7 T diffusion data (Vu et al., 2015) using probabilistic tractography (Tournier et al., 2010) with tract-specific exclusion masks, streamline cleaning and group-level probabilistic mapping, and are distributed in Montreal Neurological Institute (MNI) space on the FSL MNI152 1 mm grid (182 × 218 × 182 voxels).

The atlas represents plausible streamline trajectories. It does not establish monosynaptic connectivity, fibre directionality or neurotransmitter identity, and several components of the hippocampal–VTA circuit are polysynaptic.

## File types

Each tract is distributed as three files (Table 1).

**Table 1**

*Atlas File Types*

| Suffix | Contents | Typical use |
|---|---|---|
| `*_GroupMean_OverlapProp.nii.gz` | Probabilistic map. Each voxel holds the proportion of contributing participants whose binarized tract included it (range 0 to 1). | Visualization, threshold selection, probability-weighted extraction |
| `*_GroupMean_thr50.nii.gz` | Binary map of voxels present in at least 50% of participants. | Corridor construction, whole-tract extraction |
| `*_GroupOverlapCount.nii.gz` | Count map. Each voxel holds the number of participants whose tract included it. | Reporting participant overlap |

The 50% threshold is the default for corridor construction. Higher thresholds (75%, 90%) reduce the map toward a single central trajectory and no longer represent between-participant variation. The 25% threshold retains greater extent and is appropriate when a warped 50% core is short or discontinuous.

## Modes of use

1. *Corridor-constrained tractography.* The warped and dilated atlas defines the region within which participant-level tractography may travel. Streamlines are estimated from the participant's own data. This mode supports along-tract analysis and is the subject of the workflow section.
2. *Whole-tract extraction.* A scalar map is averaged within the warped atlas mask. This mode is suitable for descriptive summaries; spatial variation along the tract is not retained. See the [appendix](../appendix/whole-tract).
3. *Atlas-guided synthetic streamlines.* A centerline scaffold constructed inside the warped atlas is sampled at 100 nodes. This mode is suitable when participant-level tractography fails in a subset of the sample. The scaffold is a sampling coordinate system rather than a reconstruction. See the [appendix](../appendix/synthetic-streamlines).

## Coordinate spaces and interpolation

Atlas space is FSL MNI152 1 mm space unless stated otherwise. Native space refers to a participant's T1, diffusion or NODDI grid (NODDI: neurite orientation dispersion and density imaging; Zhang et al., 2012). Releases in MNI 2 mm and MNI152NLin2009cAsym space are planned.

Probabilistic maps are warped with linear interpolation and thresholded in native space. Binary maps are warped with nearest-neighbour interpolation. Spline interpolation is not appropriate for label images. In registration software the moving image is the image being transformed (here the atlas) and the fixed image defines the target grid (the participant); flag names differ between packages. Warped masks should be overlaid on the participant's image and inspected before use.

## Interpretive limits

A group atlas warped to native space does not substitute for participant-level tractography when the research question depends on individual anatomy. Dilation increases sensitivity at the cost of specificity, and the smallest dilation that supports reliable tracking should be used. Whole-tract averages are summary descriptors. Synthetic streamlines are sampling scaffolds and should be described as such in reports.
