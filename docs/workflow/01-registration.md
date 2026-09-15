---
sidebar_position: 2
title: "1. Register MNI to T1"
---

# 1. Register the MNI template to each subject's T1

The atlas and ROIs are in MNI space. Tractography runs in each subject's diffusion space. Two transforms are needed: a nonlinear MNI → T1 warp (this step, ANTs SyN) and a linear T1 → diffusion matrix from preprocessing (applied in step 2).

A nonlinear warp is required. An affine transform accounts for rotation, scaling and shear but not for individual differences in the size and position of structures. Positional errors of a few millimetres in the midbrain move the VTA ROI out of the VTA.

## Command

`antsRegistrationSyNQuick.sh` with the subject's skull-stripped T1 as the fixed image and the MNI brain as the moving image. Coverage should match: registering a skull-stripped subject to a full-head template biases the result. Use `MNI152_T1_1mm_brain.nii.gz`.

```bash
antsRegistrationSyNQuick.sh -d 3 \
  -f "$PROJECT/anat/$s/${s}_T1w_brain.nii.gz" \
  -m "$FSLDIR/data/standard/MNI152_T1_1mm_brain.nii.gz" \
  -o "$OUT/$s/reg/mni2t1_" -n 4
```

Outputs: `mni2t1_0GenericAffine.mat`, `mni2t1_1Warp.nii.gz` (MNI → T1, used in step 2), `mni2t1_1InverseWarp.nii.gz` (T1 → MNI, for sending subject results back to atlas space) and `mni2t1_Warped.nii.gz` (the template in subject space, for inspection).

If the T1 is not skull-stripped, strip it first. Atlas construction used SynthStrip; the example dataset used ANTs brain extraction. If the T1 is already aligned to the diffusion grid, this warp is the only transform required.

Script: [`01_register_mni_to_t1.sh`](pathname:///MesoConnect-Tutorial/scripts/01_register_mni_to_t1.sh). Approximately 10 to 15 minutes per subject with four threads; the script runs four subjects concurrently.

## Audit

The script ends with a per-subject table of the three transform files. In the example dataset all 57 subjects produced all three.

## Inspection

Open `mni2t1_Warped.nii.gz` over the subject T1 and toggle between them. Ventricles, corpus callosum and brainstem outline should align. A registration that is globally acceptable but locally displaced in the midbrain will appear in step 2 as a misplaced VTA, so this inspection does not replace that one.
