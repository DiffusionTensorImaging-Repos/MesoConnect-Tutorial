#!/bin/bash
# =============================================================================
# Step 2. Warp the seed, target and tract atlas into diffusion space
# =============================================================================
# MNI -> T1 with the ANTs transforms from Step 1, then T1 -> diffusion with FLIRT,
# using the matrix or the image header according to T1_TO_DWI in 00_config.sh.
# Nearest-neighbour interpolation throughout; outputs are re-binarized.
# =============================================================================
source "$(dirname "$0")/00_config.sh"
start_log "$0"
read_subjects

warp_one() {
  local s=$1
  local d="$OUT/$s/rois"
  local t1="$PROJECT/anat/$s/${s}_T1w_brain.nii.gz"
  local ref="$PROJECT/dwi/$s/nodif_brain_mask.nii.gz"
  local warp="$OUT/$s/reg/mni2t1_1Warp.nii.gz"
  local aff="$OUT/$s/reg/mni2t1_0GenericAffine.mat"
  local mat="$PROJECT/xfm/$s/str2diff.mat"
  local name src in_t1 in_diff

  if [ "$FORCE" != 1 ] && [ -f "$d/${TRACT}_atlas_diff.nii.gz" ]; then
    echo "== $s already warped"
    return
  fi
  if [ ! -f "$warp" ] || [ ! -f "$aff" ] || [ ! -f "$ref" ]; then
    echo "!! $s missing registration outputs or diffusion reference"
    return
  fi
  if [ "$T1_TO_DWI" = matrix ] && [ ! -f "$mat" ]; then
    echo "!! $s missing $mat"
    return
  fi
  mkdir -p "$d"

  for name in seed target atlas; do
    case $name in
      seed)   src=$SEED_MNI ;;
      target) src=$TARGET_MNI ;;
      atlas)  src=$ATLAS_MNI ;;
    esac
    in_t1="$d/${TRACT}_${name}_t1.nii.gz"
    in_diff="$d/${TRACT}_${name}_diff.nii.gz"

    antsApplyTransforms -d 3 -i "$src" -r "$t1" -o "$in_t1" \
      -t "$warp" -t "$aff" -n NearestNeighbor

    if [ "$T1_TO_DWI" = matrix ]; then
      flirt -in "$in_t1" -ref "$ref" -applyxfm -init "$mat" \
        -interp nearestneighbour -out "$in_diff"
    else
      # T1 and diffusion share a space: resample onto the diffusion grid by header
      flirt -in "$in_t1" -ref "$ref" -applyxfm -usesqform \
        -interp nearestneighbour -out "$in_diff"
    fi
    fslmaths "$in_diff" -thr 0.5 -bin "$in_diff"
  done
  echo ">> $s warped"
}

case "$T1_TO_DWI" in
  matrix) echo "== T1 -> diffusion: applying xfm/<subj>/str2diff.mat" ;;
  header) echo "== T1 -> diffusion: resampling by image header (no matrix)" ;;
  *)      echo "!! T1_TO_DWI must be matrix or header"; exit 1 ;;
esac

for s in "${SUBJECTS[@]}"; do
  warp_one "$s" &
  throttle "$MAXJOBS"
done
wait_for_jobs

# Audit: voxel counts and seed-target overlap (the overlap must be 0)
tmp=$(mktemp -d)
printf "\nSubject\tseed_vox\ttarget_vox\tatlas_vox\tseed_target_overlap\n"
for s in "${SUBJECTS[@]}"; do
  d="$OUT/$s/rois"
  if [ ! -f "$d/${TRACT}_atlas_diff.nii.gz" ]; then
    printf "%s\tMISSING\n" "$s"
    continue
  fi
  fslmaths "$d/${TRACT}_seed_diff.nii.gz" -mul "$d/${TRACT}_target_diff.nii.gz" "$tmp/overlap"
  printf "%s\t%s\t%s\t%s\t%s\n" "$s" \
    "$(nvox "$d/${TRACT}_seed_diff.nii.gz")" \
    "$(nvox "$d/${TRACT}_target_diff.nii.gz")" \
    "$(nvox "$d/${TRACT}_atlas_diff.nii.gz")" \
    "$(nvox "$tmp/overlap")"
done
rm -rf "$tmp"
