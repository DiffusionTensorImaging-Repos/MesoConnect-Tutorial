---
sidebar_position: 2
title: "1. Registration"
---

# Step 1. Registration of the MNI template to native T1 space

The atlas and region-of-interest files are defined in MNI space, whereas tractography is performed in each participant's diffusion space. Moving an MNI-space image into a participant therefore requires two transforms: a nonlinear warp from MNI to the participant's T1 image, computed in this step, and a linear transform from T1 to diffusion space, obtained during preprocessing and applied in step 2.

A nonlinear registration is necessary because affine transforms account for global rotation, scaling and shear but not for individual differences in the size and position of subcortical structures. Positional errors of a few millimetres in the midbrain displace the VTA region outside the VTA.

## Procedure

Registration is performed with `antsRegistrationSyNQuick.sh` (Avants et al., 2008), with the participant's skull-stripped T1 image as the fixed image and the skull-stripped MNI152 1 mm template as the moving image. Image coverage should match: registering a skull-stripped participant image to a whole-head template biases the solution.

```bash
antsRegistrationSyNQuick.sh -d 3 \
  -f "$PROJECT/anat/$s/${s}_T1w_brain.nii.gz" \
  -m "$FSLDIR/data/standard/MNI152_T1_1mm_brain.nii.gz" \
  -o "$OUT/$s/reg/mni2t1_" -n 4
```

The outputs are the affine component (`mni2t1_0GenericAffine.mat`), the forward warp from MNI to T1 (`mni2t1_1Warp.nii.gz`, used in step 2), the inverse warp from T1 to MNI (`mni2t1_1InverseWarp.nii.gz`, used to return participant-level results to atlas space) and the template resampled into participant space (`mni2t1_Warped.nii.gz`).

If the T1 image has not been skull-stripped, this should be done first; atlas construction used SynthStrip (Hoopes et al., 2022) and the example dataset used ANTs brain extraction. If the T1 image is already aligned to the diffusion grid, this warp is the only transform required.

The corresponding script is [`01_register_mni_to_t1.sh`](pathname:///MesoConnect-Tutorial/scripts/01_register_mni_to_t1.sh). Each participant requires approximately 10 to 15 minutes with four threads; the script runs four participants concurrently.

## Script

<!-- script:01_register_mni_to_t1.sh -->
<details>
<summary><code>01_register_mni_to_t1.sh</code> (16 lines)</summary>

```bash title="01_register_mni_to_t1.sh"
#!/bin/bash
# Step 1 — Nonlinear registration, MNI template -> subject T1 (ANTs SyN).
# Produces the inverse warp needed to bring MNI-space atlas files into each subject.
source "$(dirname "$0")/00_config.sh"; start_log "$0"
run_one() {
  s=$1; t1="$PROJECT/anat/$s/${s}_T1w_brain.nii.gz"; d="$OUT/$s/reg"; mkdir -p "$d"
  [[ -f "$t1" ]] || { echo "!! $s missing $t1"; return; }
  [[ "$FORCE" = 1 || ! -f "$d/mni2t1_1Warp.nii.gz" ]] || { echo "== $s already registered (FORCE=1 to redo)"; return; }
  antsRegistrationSyNQuick.sh -d 3 -f "$t1" -m "$MNI_TEMPLATE" -o "$d/mni2t1_" -n 4
  echo ">> $s done"
}
export -f run_one
while read -r s; do run_one "$s" & while [ "$(jobs -r | wc -l)" -ge 4 ]; do sleep 2; done; done < "$SUBJECTS_FILE"; wait
# Audit
printf "\nSubject\tAffine\tWarp\tInvWarp\n"
while read -r s; do d="$OUT/$s/reg"; printf "%s\t%s\t%s\t%s\n" "$s" $( [ -f "$d/mni2t1_0GenericAffine.mat" ] && echo ok || echo MISSING ) $( [ -f "$d/mni2t1_1Warp.nii.gz" ] && echo ok || echo MISSING ) $( [ -f "$d/mni2t1_1InverseWarp.nii.gz" ] && echo ok || echo MISSING ); done < "$SUBJECTS_FILE"
```

</details>
<!-- /script:01_register_mni_to_t1.sh -->


## Verification

The script concludes with a per-participant table of the three transform files. Registration quality is assessed by overlaying `mni2t1_Warped.nii.gz` on the participant's T1 image; the ventricles, corpus callosum and brainstem outline should coincide. A registration that is globally acceptable but locally displaced in the midbrain will manifest in step 2 as a misplaced VTA region, so this inspection supplements rather than replaces the region-level inspection described there. In the example dataset all 57 participants produced complete transforms.
