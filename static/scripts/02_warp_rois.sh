#!/bin/bash
# =============================================================================
# Step 2. Warp the seed, target and tract atlas into diffusion space
# =============================================================================
# MNI -> T1 with the Step 1 ANTs transforms, then T1 -> diffusion with FLIRT by matrix or
# by image header (T1_TO_DWI in 00_config.sh). Nearest neighbour throughout, re-binarized.
# In:  $OUT/<subj>/reg/mni2t1_*, $PROJECT/{anat,dwi,xfm}/<subj>/ (T1 brain, nodif mask, xfm)
# Out: $OUT/<subj>/rois/${TRACT}_{seed,target,atlas}_{t1,diff}.nii.gz (_t1 kept for checks)
# Run: bash 02_warp_rois.sh   (FORCE=1 bash 02_warp_rois.sh redoes finished participants)
# =============================================================================
source "$(dirname "$0")/00_config.sh"
start_log "$0"
read_subjects

# Warp one participant's seed, target and atlas; a missing input prints "!!" and returns.
warp_one() {
  local s=$1
  local d="$OUT/$s/rois"
  local t1="$PROJECT/anat/$s/${s}_T1w_brain.nii.gz"
  local ref="$PROJECT/dwi/$s/nodif_brain_mask.nii.gz"
  local warp="$OUT/$s/reg/mni2t1_1Warp.nii.gz"
  local aff="$OUT/$s/reg/mni2t1_0GenericAffine.mat"
  local mat="$PROJECT/xfm/$s/str2diff.mat"
  local name src in_t1 in_diff

  # Resume: the atlas is written last, so if it exists this participant already finished.
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

    # MNI -> T1. ANTs applies the -t stack last-listed first: affine, then warp. Do not swap.
    antsApplyTransforms -d 3 -i "$src" -r "$t1" -o "$in_t1" \
      -t "$warp" -t "$aff" -n NearestNeighbor

    # T1 -> diffusion
    if [ "$T1_TO_DWI" = matrix ]; then
      flirt -in "$in_t1" -ref "$ref" -applyxfm -init "$mat" \
        -interp nearestneighbour -out "$in_diff"
    else
      # -usesqform: alignment from the two images' sform/qform headers, no matrix file
      flirt -in "$in_t1" -ref "$ref" -applyxfm -usesqform \
        -interp nearestneighbour -out "$in_diff"
    fi
    # Guarantee a clean 0/1 mask: Step 3 adds and inverts these, Step 5 seeds from them.
    fslmaths "$in_diff" -thr 0.5 -bin "$in_diff"
  done
  echo ">> $s warped"
}

# Catch a bad T1_TO_DWI now rather than after warping everyone the wrong way.
case "$T1_TO_DWI" in
  matrix) echo "== T1 -> diffusion: applying xfm/<subj>/str2diff.mat" ;;
  header) echo "== T1 -> diffusion: resampling by image header (no matrix)" ;;
  *)      echo "!! T1_TO_DWI must be matrix or header"; exit 1 ;;
esac

# --- Warp everyone, MAXJOBS at a time ---
for s in "${SUBJECTS[@]}"; do
  warp_one "$s" &
  throttle "$MAXJOBS"
done
# Not a bare "wait": some bash versions would also wait on the start_log logger (never exits).
wait_for_jobs

# --- Audit: voxel counts and seed-target overlap (overlap must be 0) ---
tmp=$(mktemp -d)
printf "\nSubject\tseed_vox\ttarget_vox\tatlas_vox\tseed_target_overlap\n"
for s in "${SUBJECTS[@]}"; do
  d="$OUT/$s/rois"
  if [ ! -f "$d/${TRACT}_atlas_diff.nii.gz" ]; then
    printf "%s\tMISSING\n" "$s"
    continue
  fi
  # A voxel in both masks would count as "reached" in Step 5 before the streamline has moved.
  fslmaths "$d/${TRACT}_seed_diff.nii.gz" -mul "$d/${TRACT}_target_diff.nii.gz" "$tmp/overlap"
  printf "%s\t%s\t%s\t%s\t%s\n" "$s" \
    "$(nvox "$d/${TRACT}_seed_diff.nii.gz")" \
    "$(nvox "$d/${TRACT}_target_diff.nii.gz")" \
    "$(nvox "$d/${TRACT}_atlas_diff.nii.gz")" \
    "$(nvox "$tmp/overlap")"
done
rm -rf "$tmp"
