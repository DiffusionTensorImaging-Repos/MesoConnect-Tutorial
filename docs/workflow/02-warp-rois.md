---
sidebar_position: 3
title: "2. Warp seed, target and atlas"
---

# 2. Warp the seed, target and tract atlas into diffusion space

Three MNI images per tract pass through the same two transforms: the seed ROI, the target ROI and the atlas's 50% binary map. Nearest-neighbour interpolation is used at both stages because the images are labels. The output is re-binarized with `-thr 0.5 -bin`.

## Commands

```bash
# MNI -> T1 (ANTs, nonlinear)
antsApplyTransforms -d 3 -i "$ATLAS_MNI" -r "$T1" -o "$d/${TRACT}_atlas_t1.nii.gz" \
  -t "$OUT/$s/reg/mni2t1_1Warp.nii.gz" -t "$OUT/$s/reg/mni2t1_0GenericAffine.mat" -n NearestNeighbor

# T1 -> diffusion (FLIRT, linear); use -usesqform instead of -init if T1 and DWI share a grid
flirt -in "$d/${TRACT}_atlas_t1.nii.gz" -ref "$PROJECT/dwi/$s/nodif_brain_mask.nii.gz" \
  -applyxfm -init "$PROJECT/xfm/$s/str2diff.mat" -out "$d/${TRACT}_atlas_diff.nii.gz" -interp nearestneighbour
fslmaths "$d/${TRACT}_atlas_diff.nii.gz" -thr 0.5 -bin "$d/${TRACT}_atlas_diff.nii.gz"
```

Two successive nearest-neighbour resamplings of a binary mask have negligible effect. To obtain the probabilistic map in native space, warp it with linear interpolation and threshold afterwards.

Script: [`02_warp_rois.sh`](pathname:///MesoConnect-Tutorial/scripts/02_warp_rois.sh). Seconds per subject.

## Audit

The script prints voxel counts for the seed, target and atlas and the seed–target overlap, which must be zero. Subjects whose counts fall more than two standard deviations from the group mean should be inspected. Example dataset, VTA → hippocampus:

| ROI | min | mean | max | SD |
|---|---|---|---|---|
| VTA (L / R) | 32 / 34 | 44 / 44 | 56 / 56 | 5.5 / 5.2 |
| Hippocampus (L / R) | 308 / 332 | 395 / 407 | 497 / 493 | 33 / 34 |
| Atlas thr50 (L / R) | 107 / 99 | 126 / 123 | 146 / 149 | 9.9 / 10.6 |

The full audit on the example dataset also checked file completeness, dimensions against the diffusion reference, binariness, laterality (left ROIs in the left hemisphere), and a registration cross-correlation with a flag below 0.60. Two subjects scored 0.59 and passed visual inspection.

## Inspection

Overlay each warped ROI on the mean b0 for every subject. Three views are useful: whole-brain for gross placement, a crop around the ROI at 5× magnification for voxel-level placement, and an FSLeyes ortho render for the record.

Expected placement:

- **VTA**: ventral midbrain, anterior to the red nucleus, near the midline, a small number of voxels. Placement in the cerebral peduncle, pons or outside the brainstem indicates a failed registration.
- **Hippocampus**: along the medial temporal lobe following the floor of the lateral ventricle. Overlap with the ventricle or placement in white matter indicates an error.
- **Tract atlas**: a narrow corridor from the VTA through the midbrain to the target. Scattered voxels or very large extent indicates a threshold or registration problem.

Whole-brain and magnified views of a left VTA and left hippocampus from the example dataset:

![VTA whole brain](/img/roi_qc_wholebrain_left_VTA.png)
![VTA zoomed](/img/roi_qc_zoomed_left_VTA.png)
![Hippocampus zoomed](/img/roi_qc_zoomed_left_HPC.png)
![Atlas zoomed](/img/roi_qc_zoomed_left_tract_atlas.png)

Ortho render with VTA in yellow, hippocampus in red and atlas in green:

![Ortho left](/img/roi_qc_fsleyes_ortho_left.png)

Failure signs: an ROI in ventricle, white matter or cortex; an ROI with zero voxels; a left ROI on the right. Any of these returns that subject to step 1.

For the anterior hippocampus tract the same warp is repeated with the anterior atlas file; the seed and target are shared.

![Anterior atlas warped](/img/anterior_step21a_atlas.png)
