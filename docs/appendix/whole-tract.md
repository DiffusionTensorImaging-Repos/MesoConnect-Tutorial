---
sidebar_position: 1
title: "Whole-tract extraction"
---

# Whole-tract extraction

In this approach an atlas map is warped into a participant and a scalar map is averaged within it. It is suitable for descriptive summaries, replication checks and visualization. It is not recommended as a primary endpoint because spatial variation along the tract is not retained.

## Procedure

The 50% binary map provides a conservative core; the probabilistic map supports probability-weighted extraction. The map is warped to T1 space with the step-1 transforms, using nearest-neighbour interpolation for binary maps and linear interpolation followed by thresholding for probabilistic maps.

```bash
antsApplyTransforms -d 3 -i "$ATLAS_PROB" -r "$T1" -o prob_in_T1.nii.gz \
  -t mni2t1_1Warp.nii.gz -t mni2t1_0GenericAffine.mat -n Linear
fslmaths prob_in_T1.nii.gz -thr 0.50 -bin prob50_in_T1_bin.nii.gz
```

The mask is then moved to the scalar map's grid. When the T1 and the scalar map are header-aligned and differ only in grid, the mask is resampled (`flirt -in mask -ref scalar -applyxfm -usesqform -interp nearestneighbour`); otherwise the T1 → diffusion transform is applied. Voxel count, volume and the mean and standard deviation of the scalar within the mask are then extracted.

```bash
fslstats mask_on_scalar_grid.nii.gz -V                   # voxel count, mm3
fslstats "$NDI" -k mask_on_scalar_grid.nii.gz -M -S       # mean, SD
```

## Reporting

For multi-shell data with a NODDI fit, NDI is generally preferred to FA as a whole-tract summary. It remains a model-derived quantity sensitive to partial volume, registration and mask boundaries, and should be reported with covariates for age, sex, motion, intracranial volume and whole-white-matter NDI and described as a summary measure.
