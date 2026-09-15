---
sidebar_position: 1
title: "What the atlas is"
---

# What the atlas is

The MesoConnect Atlas is a set of group probabilistic maps of mesolimbic tracts, generated from Human Connectome Project 7 T diffusion data with anatomically constrained probabilistic tractography, tract-specific exclusion masks, streamline cleaning and group-level probabilistic mapping. It is distributed in **FSL MNI152 1 mm space** (182 × 218 × 182 voxels).

It is a structural connectivity resource, not evidence of monosynaptic connection. Tractography estimates plausible streamline trajectories, not synapses, directionality or neurotransmitter identity. Several components of the hippocampal to VTA loop are polysynaptic. Treat the atlas as an anatomically constrained scaffold for measurement.

## Three files per tract

| Suffix | What it is | Use it for |
|---|---|---|
| `*_GroupMean_OverlapProp.nii.gz` | Probabilistic map. Each voxel is the proportion of contributing subjects whose binarized tract included it (0 to 1). | Visualization, choosing a threshold, probability-weighted extraction. |
| `*_GroupMean_thr50.nii.gz` | Binary map, voxels present in at least 50% of subjects. | The corridor workflow, whole-tract extraction, any place a binary mask is needed. |
| `*_GroupOverlapCount.nii.gz` | Count map, number of subjects whose tract included the voxel. | Reporting overlap; do not warp for subject-level analysis. |

The 50% threshold is a deliberate trade-off. Tighter thresholds (75%, 90%) collapse toward a single centroid streamline and stop representing individual variation; looser ones (25%) retain more extent and can help if a warped core is short or discontinuous. For a corridor that is then dilated, 50% is the default and 25% is the fallback.

## Three ways to use it

1. **Corridor-constrained tractography** (this tutorial). Warp the atlas, dilate it, and use it to constrain subject tractography. Streamlines come from the subject's data; the atlas only says where they may go. Most defensible, and the only route that gives subject-specific bundles for node-wise work.
2. **Whole-tract extraction** ([appendix](../appendix/whole-tract)). Warp the atlas and average a scalar map inside it. Fast and useful for description, but it collapses the spatial variation along the tract that usually carries the effect.
3. **Atlas-guided synthetic streamlines** ([appendix](../appendix/synthetic-streamlines)). Build a centerline scaffold inside the warped atlas and sample 100 nodes along it. Useful when tractography fails in some subjects, but reviewers unfamiliar with it may push back, and the scaffold is a coordinate system, not a reconstruction.

## Spaces and interpolation

- Atlas space is FSL MNI152 1 mm unless stated otherwise. Native space means a subject's T1, diffusion or NODDI grid. Releases in MNI 2 mm and MNI152NLin2009cAsym are planned for users of DSI Studio and related tools.
- Warp **probabilistic** maps with linear interpolation and threshold afterwards in native space. Warp **binary** maps with nearest-neighbour. Never use spline interpolation on labels.
- Moving image means the thing being transformed (the atlas); fixed image means the target grid (the subject). Registration tools disagree on which flag is which; check.
- Always overlay a warped mask on the subject image before using it for anything.

## Limits worth stating in a methods section

- A group atlas warped to native space does not replace subject-specific tractography when the question depends on individual anatomy.
- Dilation increases sensitivity and reduces specificity. Use the smallest dilation that tracks reliably.
- Whole-tract averages are summary descriptors, not the strongest test.
- Synthetic streamlines are sampling scaffolds and should never be described as newly reconstructed bundles.
