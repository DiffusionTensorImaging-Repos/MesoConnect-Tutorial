---
sidebar_position: 1
title: "Whole-tract extraction"
---

# Whole-tract extraction

An atlas map is warped into a subject and a scalar map is averaged inside it. This is suitable for descriptive summaries, replication checks and visualization. It is not recommended as a primary endpoint because spatial variation along the tract is lost.

## Steps

1. Choose the map: the 50% binary for a conservative core, or the probabilistic map for probability-weighted extraction.
2. Warp to T1 with the step-1 transforms. Binary maps: nearest-neighbour. Probabilistic maps: linear, then threshold in subject space.

```bash
antsApplyTransforms -d 3 -i "$ATLAS_PROB" -r "$T1" -o prob_in_T1.nii.gz \
  -t mni2t1_1Warp.nii.gz -t mni2t1_0GenericAffine.mat -n Linear
fslmaths prob_in_T1.nii.gz -thr 0.50 -bin prob50_in_T1_bin.nii.gz
```

3. Move the mask to the scalar grid. If the T1 and scalar map are header-aligned and differ only in grid, resample with `flirt -in mask -ref scalar -applyxfm -usesqform -interp nearestneighbour`. Otherwise apply the T1 → diffusion matrix.
4. Extract.

```bash
fslstats mask_on_scalar_grid.nii.gz -V                   # voxel count, mm3
fslstats "$NDI" -k mask_on_scalar_grid.nii.gz -M -S       # mean, SD
```

## Reporting

For multi-shell data with a NODDI fit, NDI is generally preferred to FA as a whole-tract summary. It remains a model-derived quantity sensitive to partial volume, registration and mask edges. Report it with covariates for age, sex, motion, intracranial volume and whole-white-matter NDI, and describe it as a summary measure.
