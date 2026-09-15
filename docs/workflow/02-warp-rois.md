---
sidebar_position: 3
title: "2. Warp seed, target and atlas"
---

# 2. Warp the seed, target and tract atlas into diffusion space

Three MNI images per tract go through the same two transforms: the seed ROI, the target ROI and the atlas's 50% binary map. Nearest-neighbour interpolation at both stages, because these are labels, and a `-thr 0.5 -bin` at the end as a safety step.

## Commands

```bash
# MNI -> T1 (ANTs, nonlinear)
antsApplyTransforms -d 3 -i "$ATLAS_MNI" -r "$T1" -o "$d/${TRACT}_atlas_t1.nii.gz" \
  -t "$OUT/$s/reg/mni2t1_1Warp.nii.gz" -t "$OUT/$s/reg/mni2t1_0GenericAffine.mat" -n NearestNeighbor

# T1 -> diffusion (FLIRT, linear); or -usesqform if T1 and DWI share a grid
flirt -in "$d/${TRACT}_atlas_t1.nii.gz" -ref "$PROJECT/dwi/$s/nodif_brain_mask.nii.gz" \
  -applyxfm -init "$PROJECT/xfm/$s/str2diff.mat" -out "$d/${TRACT}_atlas_diff.nii.gz" -interp nearestneighbour
fslmaths "$d/${TRACT}_atlas_diff.nii.gz" -thr 0.5 -bin "$d/${TRACT}_atlas_diff.nii.gz"
```

Two separate resamplings of a binary mask with nearest-neighbour cost almost nothing. Do not be tempted to warp the probabilistic map with nearest-neighbour; if you want the probabilistic map in native space, warp it with linear interpolation and threshold there.

Script: [`02_warp_rois.sh`](pathname:///MesoConnect-Tutorial/scripts/02_warp_rois.sh). Seconds per subject.

## Audit

The script prints voxel counts for seed, target and atlas and the seed ∩ target overlap, which must be zero. Flag any subject whose count is more than two standard deviations from the group mean. The example dataset, VTA → hippocampus:

| ROI | min | mean | max | SD |
|---|---|---|---|---|
| VTA (L / R) | 32 / 34 | 44 / 44 | 56 / 56 | 5.5 / 5.2 |
| Hippocampus (L / R) | 308 / 332 | 395 / 407 | 497 / 493 | 33 / 34 |
| Atlas thr50 (L / R) | 107 / 99 | 126 / 123 | 146 / 149 | 9.9 / 10.6 |

A VTA of 30 to 55 voxels at 2 mm is a handful of voxels. That is why the next check is visual.

The full audit run on the example added: file completeness, dimension match against the diffusion reference, binariness, laterality (left ROIs in the left hemisphere), and a registration cross-correlation with subjects under 0.60 flagged. Two subjects sat at 0.59 and passed visual inspection; the flag is a prompt to look, not a verdict.

## Look at it

For every subject, overlay each warped ROI on the mean b0. Three views work well: whole-brain for gross placement, a zoomed crop around the ROI at 5× to see individual voxels, and an FSLeyes ortho render for the record.

What correct looks like:

- **VTA**: ventral midbrain, just anterior to the red nucleus, near the midline, a few voxels. In the cerebral peduncle, the pons or outside the brainstem means the registration failed for that subject.
- **Hippocampus**: tracing the medial temporal lobe along the floor of the lateral ventricle. Overlapping the ventricle or sitting in white matter is wrong.
- **Tract atlas**: a thin corridor from the VTA up through the midbrain to the target. Scattered voxels or half the brain means the threshold or the registration is off.

Whole-brain and zoomed views of a left VTA and left hippocampus from the example dataset:

![VTA whole brain](/img/roi_qc_wholebrain_left_VTA.png)
![VTA zoomed](/img/roi_qc_zoomed_left_VTA.png)
![Hippocampus zoomed](/img/roi_qc_zoomed_left_HPC.png)
![Atlas zoomed](/img/roi_qc_zoomed_left_tract_atlas.png)

Ortho render with VTA in yellow, hippocampus in red, atlas in green:

![Ortho left](/img/roi_qc_fsleyes_ortho_left.png)

Red flags: an ROI in ventricle, white matter or cortex; an ROI with zero voxels; a left ROI on the right. Any of these sends that subject back to step 1.

For the anterior hippocampus tract the same warp is repeated with the anterior atlas file; the seed and target are shared.

![Anterior atlas warped](/img/anterior_step21a_atlas.png)
