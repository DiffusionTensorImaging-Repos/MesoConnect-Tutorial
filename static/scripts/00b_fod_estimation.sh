#!/bin/bash
# =============================================================================
# Step 0b. Fibre orientation distributions (multi-shell multi-tissue CSD)
# =============================================================================
# Run once, before Step 5, when preprocessing ended at the tensor.
#   Phase 1 (per participant)  response functions: dwi2response dhollander
#   Phase 2 (group)            average response functions: responsemean
#   Phase 3 (per participant)  dwi2fod msmt_csd, then mtnormalise
# Single-shell data support two tissues only: remove the GM response and GM FOD
# arguments from the dwi2fod and mtnormalise calls.
# =============================================================================
source "$(dirname "$0")/00_config.sh"
start_log "$0"

estimate_response() {
  local s=$1
  local d="$PROJECT/dwi/$s"
  local f
  for f in data.nii.gz bvals bvecs nodif_brain_mask.nii.gz; do
    if [ ! -f "$d/$f" ]; then
      echo "!! $s missing $d/$f"
      return
    fi
  done
  if [ "$FORCE" != 1 ] && [ -f "$d/wm_response.txt" ]; then
    echo "== $s response functions exist"
    return
  fi
  mrconvert "$d/data.nii.gz" "$d/dwi.mif" -fslgrad "$d/bvecs" "$d/bvals" -force -quiet
  mrconvert "$d/nodif_brain_mask.nii.gz" "$d/mask.mif" -force -quiet
  dwi2response dhollander "$d/dwi.mif" \
    "$d/wm_response.txt" "$d/gm_response.txt" "$d/csf_response.txt" \
    -mask "$d/mask.mif" -force -quiet
  echo ">> $s response functions"
}

estimate_fod() {
  local s=$1
  local d="$PROJECT/dwi/$s"
  local g="$PROJECT/dwi"
  if [ "$FORCE" != 1 ] && [ -f "$d/wm_fod_norm.mif" ]; then
    echo "== $s FOD exists"
    return
  fi
  dwi2fod msmt_csd "$d/dwi.mif" \
    "$g/group_wm_response.txt"  "$d/wm_fod.mif" \
    "$g/group_gm_response.txt"  "$d/gm_fod.mif" \
    "$g/group_csf_response.txt" "$d/csf_fod.mif" \
    -mask "$d/mask.mif" -nthreads "$NTHREADS" -force -quiet
  mtnormalise \
    "$d/wm_fod.mif"  "$d/wm_fod_norm.mif" \
    "$d/gm_fod.mif"  "$d/gm_fod_norm.mif" \
    "$d/csf_fod.mif" "$d/csf_fod_norm.mif" \
    -mask "$d/mask.mif" -force -quiet
  echo ">> $s FOD"
}

# Phase 1
while read -r s; do
  estimate_response "$s" &
  throttle "$MAXJOBS"
done < "$SUBJECTS_FILE"
wait

# Phase 2
for tissue in wm gm csf; do
  responsemean "$PROJECT"/dwi/*/${tissue}_response.txt \
    "$PROJECT/dwi/group_${tissue}_response.txt" -force -quiet
done
echo "== group response functions written"

# Phase 3 (memory-intensive: two participants at a time)
while read -r s; do
  estimate_fod "$s" &
  throttle 2
done < "$SUBJECTS_FILE"
wait

# Audit
printf "\nSubject\twm_fod_norm\n"
while read -r s; do
  printf "%s\t%s\n" "$s" "$(present "$PROJECT/dwi/$s/wm_fod_norm.mif")"
done < "$SUBJECTS_FILE"
