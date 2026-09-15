#!/bin/bash
# Step 0b — Fibre orientation distributions (run once, before step 5, if preprocessing ended at the tensor).
# Per participant: mrconvert -> dwi2response (dhollander); then group-average responses; then dwi2fod msmt_csd -> mtnormalise.
source "$(dirname "$0")/00_config.sh"; start_log "$0"
phase1(){ s=$1; d="$PROJECT/dwi/$s"; dwi=$(eval echo "$DWI_NII"); bval=$(eval echo "$BVALS"); bvec=$(eval echo "$BVECS")
  [[ -f "$dwi" && -f "$bval" && -f "$bvec" && -f "$d/nodif_brain_mask.nii.gz" ]] || { echo "!! $s missing dwi/bvals/bvecs/mask"; return; }
  [[ "$FORCE" = 1 || ! -f "$d/wm_response.txt" ]] || { echo "== $s responses exist"; return; }
  mrconvert "$dwi" "$d/dwi.mif" -fslgrad "$bvec" "$bval" -force -quiet
  mrconvert "$d/nodif_brain_mask.nii.gz" "$d/mask.mif" -force -quiet
  dwi2response dhollander "$d/dwi.mif" "$d/wm_response.txt" "$d/gm_response.txt" "$d/csf_response.txt" -mask "$d/mask.mif" -force -quiet
  echo ">> $s responses"; }
phase3(){ s=$1; d="$PROJECT/dwi/$s"
  [[ "$FORCE" = 1 || ! -f "$d/wm_fod_norm.mif" ]] || { echo "== $s FOD exists"; return; }
  dwi2fod msmt_csd "$d/dwi.mif" "$PROJECT/dwi/group_wm_response.txt" "$d/wm_fod.mif" \
    "$PROJECT/dwi/group_gm_response.txt" "$d/gm_fod.mif" "$PROJECT/dwi/group_csf_response.txt" "$d/csf_fod.mif" -mask "$d/mask.mif" -nthreads "$NTHREADS" -force -quiet
  mtnormalise "$d/wm_fod.mif" "$d/wm_fod_norm.mif" "$d/gm_fod.mif" "$d/gm_fod_norm.mif" "$d/csf_fod.mif" "$d/csf_fod_norm.mif" -mask "$d/mask.mif" -force -quiet
  echo ">> $s FOD"; }
export -f phase1 phase3
while read -r s; do phase1 "$s" & while [ "$(jobs -r | wc -l)" -ge "$MAXJOBS" ]; do sleep 2; done; done < "$SUBJECTS_FILE"; wait
responsemean "$PROJECT"/dwi/*/wm_response.txt  "$PROJECT/dwi/group_wm_response.txt"  -force -quiet
responsemean "$PROJECT"/dwi/*/gm_response.txt  "$PROJECT/dwi/group_gm_response.txt"  -force -quiet
responsemean "$PROJECT"/dwi/*/csf_response.txt "$PROJECT/dwi/group_csf_response.txt" -force -quiet
echo "== group response functions written"
while read -r s; do phase3 "$s" & while [ "$(jobs -r | wc -l)" -ge 2 ]; do sleep 5; done; done < "$SUBJECTS_FILE"; wait
printf "\nSubject\twm_fod_norm\n"; while read -r s; do printf "%s\t%s\n" "$s" "$( [ -f "$PROJECT/dwi/$s/wm_fod_norm.mif" ] && echo ok || echo MISSING )"; done < "$SUBJECTS_FILE"
