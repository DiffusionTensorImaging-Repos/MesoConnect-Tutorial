#!/bin/bash
# =============================================================================
# Step 3. Build the corridor and its exclusion mask
# =============================================================================
# Dilate the warped atlas, add the seed and target, binarize (inclusion zone),
# then invert.  The inverted image is the single exclusion mask given to tckgen:
# every voxel outside the corridor terminates and discards a streamline.
# =============================================================================
source "$(dirname "$0")/00_config.sh"
start_log "$0"

# One -dilM pass (3 x 3 x 3 kernel) per voxel of requested dilation
DILATE_ARGS=""
for ((i = 0; i < DILATE_VOX; i++)); do
  DILATE_ARGS="$DILATE_ARGS -dilM"
done

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
  # $DILATE_ARGS is intentionally unquoted so that it expands to separate options
  fslmaths "$d/${TRACT}_atlas_diff.nii.gz" $DILATE_ARGS "$d/${TRACT}_atlas_dilated.nii.gz"
  fslmaths "$d/${TRACT}_atlas_dilated.nii.gz" \
    -add "$d/${TRACT}_seed_diff.nii.gz" \
    -add "$d/${TRACT}_target_diff.nii.gz" \
    -bin "$d/${TRACT}_inclusion_zone.nii.gz"
  fslmaths "$d/${TRACT}_inclusion_zone.nii.gz" -binv "$d/${TRACT}_exclusion_mask.nii.gz"
  echo ">> $s corridor: $(nvox "$d/${TRACT}_inclusion_zone.nii.gz") voxels"
}

while read -r s; do
  build_one "$s" &
  throttle "$MAXJOBS"
done < "$SUBJECTS_FILE"
wait

# Audit: no seed or target voxel may fall inside the exclusion mask (both counts 0)
tmp=$(mktemp -d)
printf "\nSubject\tseed_excluded\ttarget_excluded\tcorridor_vox\n"
while read -r s; do
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
done < "$SUBJECTS_FILE"
rm -rf "$tmp"
