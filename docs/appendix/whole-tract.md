---
sidebar_position: 1
title: "Whole-tract extraction"
---

# Whole-tract extraction

Warp an atlas map into a subject and average a scalar inside it. Appropriate for description, quick replication and visualization. Not the recommended primary endpoint: it collapses variation along the tract, and that variation is usually where the effect is.

## Steps

1. Choose the map: the 50% binary for a conservative core, or the probabilistic map for probability-weighted extraction.
2. Warp to T1 with the step-1 inverse transforms. Binary: nearest-neighbour. Probabilistic: linear, then threshold in subject space.

```bash
antsApplyTransforms -d 3 -i "$ATLAS_PROB" -r "$T1" -o prob_in_T1.nii.gz \
  -t mni2t1_1Warp.nii.gz -t mni2t1_0GenericAffine.mat -n Linear
fslmaths prob_in_T1.nii.gz -thr 0.50 -bin prob50_in_T1_bin.nii.gz
```

3. Move to the scalar grid. If T1 and the scalar are header-aligned and only the grid differs, resample: `flirt -in mask -ref scalar -applyxfm -usesqform -interp nearestneighbour`. Otherwise apply your T1 → diffusion matrix.
4. Extract.

```bash
fslstats mask_on_scalar_grid.nii.gz -V                   # voxels, mm3
fslstats "$NDI" -k mask_on_scalar_grid.nii.gz -M -S       # mean, SD
```

## Reporting

NDI is generally preferable to FA for whole-tract summaries when you have multi-shell data and a NODDI fit, but it is still model-derived and sensitive to partial volume, registration and mask edges. Report it with age, sex, motion, intracranial volume and a whole-white-matter NDI covariate. Say that it is a summary descriptor.
