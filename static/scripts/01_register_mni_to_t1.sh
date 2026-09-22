#!/bin/bash
# =============================================================================
# Step 1. ANTs SyN registration of the MNI152 template (moving) to each T1 (fixed)
# =============================================================================
# Step 2 applies the forward affine + warp to carry MNI-space seed, target and atlas into T1.
# In:  $PROJECT/anat/<subj>/<subj>_T1w_brain.nii.gz (skull-stripped), $MNI_TEMPLATE
# Out: $OUT/<subj>/reg/mni2t1_{0GenericAffine.mat,1Warp,1InverseWarp,Warped}; QC = Warped
# Run: bash 01_register_mni_to_t1.sh  (FORCE=1 redoes everyone). Hours; log in $OUT/logs/
# =============================================================================

source "$(dirname "$0")/00_config.sh"
start_log "$0"
read_subjects

# Register one participant; returns early if the T1 is missing or the warp already exists.
register_one() {
  local s=$1
  local t1="$PROJECT/anat/$s/${s}_T1w_brain.nii.gz"
  local d="$OUT/$s/reg"
  if [ ! -f "$t1" ]; then
    echo "!! $s missing $t1"
    return
  fi
  if [ "$FORCE" != 1 ] && [ -f "$d/mni2t1_1Warp.nii.gz" ]; then
    echo "== $s already registered (FORCE=1 to recompute)"
    return
  fi
  mkdir -p "$d"
  antsRegistrationSyNQuick.sh -d 3 \
    -f "$t1" \
    -m "$MNI_TEMPLATE" \
    -o "$d/mni2t1_" \
    -n "$ANTS_THREADS"
  echo ">> $s registered"
}

for s in "${SUBJECTS[@]}"; do
  register_one "$s" &
  throttle "$ANTS_JOBS"
done
# Not a bare "wait": that would also hang on the tee process start_log opened.
wait_for_jobs

# Audit. Step 2 skips any participant with a MISSING affine or warp, so fix those first.
printf "\nSubject\tAffine\tWarp\tInverseWarp\n"
for s in "${SUBJECTS[@]}"; do
  d="$OUT/$s/reg"
  printf "%s\t%s\t%s\t%s\n" "$s" \
    "$(present "$d/mni2t1_0GenericAffine.mat")" \
    "$(present "$d/mni2t1_1Warp.nii.gz")" \
    "$(present "$d/mni2t1_1InverseWarp.nii.gz")"
done
