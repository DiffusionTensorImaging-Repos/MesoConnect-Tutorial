---
sidebar_position: 2
title: "1. Register MNI to T1"
---

# 1. Register the MNI template to each subject's T1

The atlas and the ROIs live in MNI space; tractography runs in each subject's diffusion space. Two transforms get an MNI image into a subject: a **nonlinear** MNI → T1 warp (this step, ANTs SyN) and a **linear** T1 → diffusion matrix (from your preprocessing, applied in step 2).

The warp has to be nonlinear. An affine handles rotation, scale and shear, not the fact that one person's hippocampus is wider or their VTA sits a few millimetres lower than the template. A few millimetres is the whole VTA.

## Command

`antsRegistrationSyNQuick.sh` with the subject's skull-stripped T1 as the fixed image and the MNI brain as the moving image. Coverage has to match: a skull-stripped subject against a full-head template pulls the registration toward the scalp. Use `MNI152_T1_1mm_brain.nii.gz`.

```bash
antsRegistrationSyNQuick.sh -d 3 \
  -f "$PROJECT/anat/$s/${s}_T1w_brain.nii.gz" \
  -m "$FSLDIR/data/standard/MNI152_T1_1mm_brain.nii.gz" \
  -o "$OUT/$s/reg/mni2t1_" -n 4
```

Outputs: `mni2t1_0GenericAffine.mat`, `mni2t1_1Warp.nii.gz` (MNI → T1, the one you use), `mni2t1_1InverseWarp.nii.gz` (T1 → MNI, for sending subject results back to the atlas), and `mni2t1_Warped.nii.gz` (the template in subject space, for a visual check).

If your T1 is not skull-stripped, strip it first; the atlas construction used SynthStrip, the example dataset used ANTs brain extraction. If the T1 is already aligned to the diffusion grid, this warp is the only transform you need.

Script: [`01_register_mni_to_t1.sh`](pathname:///MesoConnect-Tutorial/scripts/01_register_mni_to_t1.sh). Roughly 10 to 15 minutes per subject with four threads; it runs four subjects at a time.

## Audit

The script ends with a table of which of the three transform files exist per subject. In the example dataset, 57 of 57 produced all three.

## Look at it

Open `mni2t1_Warped.nii.gz` over the subject T1 in FSLeyes and toggle. Ventricles, the corpus callosum and the brainstem outline should sit on top of each other. A registration that is globally fine but locally off in the midbrain will show up in step 2 as a VTA in the wrong place, so this look is a quick sanity check, not the last one.
