#!/bin/bash
# =============================================================================
# Step 0b. Fibre orientation distributions (multi-shell multi-tissue CSD)
# =============================================================================
# Estimates per-participant response functions, averages them across the sample and
# deconvolves everyone with that average, so FOD amplitudes and CUTOFF are comparable.
# Inputs:  $PROJECT/dwi/<ID>/{data.nii.gz,bvals,bvecs,nodif_brain_mask.nii.gz}
# Outputs: $PROJECT/dwi/<ID>/{wm,gm,csf}_fod_norm.mif and $PROJECT/dwi/group_*_response.txt
# Run:     bash 00b_fod_estimation.sh   (FORCE=1 redoes everything; hours, use tmux)
# =============================================================================
source "$(dirname "$0")/00_config.sh"
start_log "$0"
read_subjects

# Phase 1 worker: convert one participant to .mif and estimate WM, GM and CSF responses.
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
  # -fslgrad bvecs bvals: put the gradient table in the header, so later steps need no -fslgrad.
  mrconvert "$d/data.nii.gz" "$d/dwi.mif" -fslgrad "$d/bvecs" "$d/bvals" -force -quiet
  mrconvert "$d/nodif_brain_mask.nii.gz" "$d/mask.mif" -force -quiet
  # dhollander: unsupervised WM, GM and CSF response estimation.
  dwi2response dhollander "$d/dwi.mif" \
    "$d/wm_response.txt" "$d/gm_response.txt" "$d/csf_response.txt" \
    -mask "$d/mask.mif" -force -quiet
  echo ">> $s response functions"
}

# Phase 3 worker: msmt-CSD with the group-average responses, then mtnormalise.
estimate_fod() {
  local s=$1
  local d="$PROJECT/dwi/$s"
  local g="$PROJECT/dwi"
  if [ "$FORCE" != 1 ] && [ -f "$d/wm_fod_norm.mif" ]; then
    echo "== $s FOD exists"
    return
  fi
  # Group responses, not the participant's own, so every FOD is deconvolved the same way.
  dwi2fod msmt_csd "$d/dwi.mif" \
    "$g/group_wm_response.txt"  "$d/wm_fod.mif" \
    "$g/group_gm_response.txt"  "$d/gm_fod.mif" \
    "$g/group_csf_response.txt" "$d/csf_fod.mif" \
    -mask "$d/mask.mif" -nthreads "$NTHREADS" -force -quiet
  # wm_fod_norm.mif means "done", so write a temp name and rename only if mtnormalise succeeds.
  if mtnormalise \
    "$d/wm_fod.mif"  "$d/wm_fod_norm.partial.mif" \
    "$d/gm_fod.mif"  "$d/gm_fod_norm.mif" \
    "$d/csf_fod.mif" "$d/csf_fod_norm.mif" \
    -mask "$d/mask.mif" -force -quiet; then
    mv -f "$d/wm_fod_norm.partial.mif" "$d/wm_fod_norm.mif"
    echo ">> $s FOD"
  else
    rm -f "$d/wm_fod_norm.partial.mif"
    echo "!! $s FOD estimation failed or was interrupted"
  fi
}

# --- Phase 1: response functions, $MAXJOBS participants at a time ---
for s in "${SUBJECTS[@]}"; do
  estimate_response "$s" &
  throttle "$MAXJOBS"
done
# Not a bare "wait": the start_log logger never exits and bash 5.0-5.2 would wait on it too.
wait_for_jobs

# --- Phase 2: group-average response functions ---
# No FORCE guard (cheap). The glob takes every folder in $PROJECT/dwi, not just $SUBJECTS_FILE.
for tissue in wm gm csf; do
  responsemean "$PROJECT"/dwi/*/${tissue}_response.txt \
    "$PROJECT/dwi/group_${tissue}_response.txt" -force -quiet
done
echo "== group response functions written"

# --- Phase 3: CSD + normalisation, $FOD_JOBS at a time (dwi2fod is memory-heavy) ---
for s in "${SUBJECTS[@]}"; do
  estimate_fod "$s" &
  throttle "$FOD_JOBS"
done
wait_for_jobs

# --- Audit: ok or MISSING for the file Steps 4 and 5 track on ---
printf "\nSubject\twm_fod_norm\n"
for s in "${SUBJECTS[@]}"; do
  printf "%s\t%s\n" "$s" "$(present "$PROJECT/dwi/$s/wm_fod_norm.mif")"
done
