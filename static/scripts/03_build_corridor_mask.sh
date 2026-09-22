#!/bin/bash
# =============================================================================
# Step 3. Build the corridor and its exclusion mask
# =============================================================================
# Dilate the warped atlas, add seed and target, binarize, invert: tckgen's -exclude mask.
# In:  $OUT/<participant>/rois/<TRACT>_{atlas,seed,target}_diff.nii.gz (Step 2)
# Out: same dir, <TRACT>_{atlas_dilated,inclusion_zone,exclusion_mask}.nii.gz
# Run: bash 03_build_corridor_mask.sh   (after Step 2; FORCE=1 redoes all)
# =============================================================================
source "$(dirname "$0")/00_config.sh"
start_log "$0"
read_subjects

# One -dilM pass (3x3x3) per voxel; DILATE_VOX=2 (4 mm) is slack for registration error.
DILATE_ARGS=""
for ((i = 0; i < DILATE_VOX; i++)); do
  DILATE_ARGS="$DILATE_ARGS -dilM"
done

# build_one <ID>: writes the three corridor images; skips if the mask exists unless FORCE=1
build_one() {
  local s=$1
  local d="$OUT/$s/rois"
  if [ "$FORCE" != 1 ] && [ -f "$d/${TRACT}_exclusion_mask.nii.gz" ]; then
    echo "== $s corridor exists"
    return
  fi
  if [ ! -f "$d/${TRACT}_atlas_diff.nii.gz" ]; then
    echo "!! $s missing warped atlas (run Step 2)"
    return
  fi
  # $DILATE_ARGS is unquoted on purpose: it must expand to separate -dilM options
  fslmaths "$d/${TRACT}_atlas_diff.nii.gz" $DILATE_ARGS "$d/${TRACT}_atlas_dilated.nii.gz"
  # Seed and target go in before the inversion, or the corridor ends short of them
  fslmaths "$d/${TRACT}_atlas_dilated.nii.gz" \
    -add "$d/${TRACT}_seed_diff.nii.gz" \
    -add "$d/${TRACT}_target_diff.nii.gz" \
    -bin "$d/${TRACT}_inclusion_zone.nii.gz"
  fslmaths "$d/${TRACT}_inclusion_zone.nii.gz" -binv "$d/${TRACT}_exclusion_mask.nii.gz"
  echo ">> $s corridor: $(nvox "$d/${TRACT}_inclusion_zone.nii.gz") voxels"
}

for s in "${SUBJECTS[@]}"; do
  build_one "$s" &
  throttle "$MAXJOBS"
done
# Not a bare wait: see wait_for_jobs in 00_config.sh
wait_for_jobs

# Audit: seed_excluded and target_excluded must be 0 for every participant before Step 4
tmp=$(mktemp -d)
printf "\nSubject\tseed_excluded\ttarget_excluded\tcorridor_vox\n"
for s in "${SUBJECTS[@]}"; do
  d="$OUT/$s/rois"
  excl="$d/${TRACT}_exclusion_mask.nii.gz"
  if [ ! -f "$excl" ]; then
    printf "%s\tMISSING\n" "$s"
    continue
  fi
  fslmaths "$excl" -mul "$d/${TRACT}_seed_diff.nii.gz" "$tmp/seed"
  fslmaths "$excl" -mul "$d/${TRACT}_target_diff.nii.gz" "$tmp/target"
  printf "%s\t%s\t%s\t%s\n" "$s" \
    "$(nvox "$tmp/seed")" \
    "$(nvox "$tmp/target")" \
    "$(nvox "$d/${TRACT}_inclusion_zone.nii.gz")"
done
rm -rf "$tmp"
