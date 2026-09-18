#!/bin/bash
# =============================================================================
# Step 1. Nonlinear registration of the MNI template to each participant's T1
# =============================================================================
# Fixed image: participant T1 (skull-stripped).  Moving image: MNI152 1 mm brain.
# The forward transforms (mni2t1_0GenericAffine.mat, mni2t1_1Warp.nii.gz) carry
# MNI-space files into T1 space in Step 2; the inverse warp returns
# participant-level results to MNI space.
# =============================================================================
source "$(dirname "$0")/00_config.sh"
start_log "$0"

ANTS_THREADS=4      # threads per registration
ANTS_JOBS=4         # registrations run concurrently

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

while read -r s; do
  register_one "$s" &
  throttle "$ANTS_JOBS"
done < "$SUBJECTS_FILE"
wait

# Audit
printf "\nSubject\tAffine\tWarp\tInverseWarp\n"
while read -r s; do
  d="$OUT/$s/reg"
  printf "%s\t%s\t%s\t%s\n" "$s" \
    "$(present "$d/mni2t1_0GenericAffine.mat")" \
    "$(present "$d/mni2t1_1Warp.nii.gz")" \
    "$(present "$d/mni2t1_1InverseWarp.nii.gz")"
done < "$SUBJECTS_FILE"
