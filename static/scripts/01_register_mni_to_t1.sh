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
