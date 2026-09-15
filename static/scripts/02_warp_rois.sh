#!/bin/bash
# Step 2 — Warp seed, target and tract atlas from MNI -> T1 (ANTs) -> diffusion (FLIRT).
# Nearest-neighbour throughout; outputs re-binarized as a safety step.
source "$(dirname "$0")/00_config.sh"; start_log "$0"
run_one() {
  s=$1; d="$OUT/$s/rois"; mkdir -p "$d"
  [[ "$FORCE" = 1 || ! -f "$d/${TRACT}_atlas_diff.nii.gz" ]] || { echo "== $s already warped"; return; }
  t1="$PROJECT/anat/$s/${s}_T1w_brain.nii.gz"; ref="$PROJECT/dwi/$s/nodif_brain_mask.nii.gz"
  warp="$OUT/$s/reg/mni2t1_1Warp.nii.gz"; aff="$OUT/$s/reg/mni2t1_0GenericAffine.mat"; mat="$PROJECT/xfm/$s/str2diff.mat"
  [[ -f "$warp" && -f "$aff" && -f "$ref" ]] || { echo "!! $s missing registration or reference"; return; }
  for pair in "seed:$SEED_MNI" "target:$TARGET_MNI" "atlas:$ATLAS_MNI"; do
    name=${pair%%:*}; src=${pair#*:}
    antsApplyTransforms -d 3 -i "$src" -r "$t1" -o "$d/${TRACT}_${name}_t1.nii.gz" -t "$warp" -t "$aff" -n NearestNeighbor
    if [[ -f "$mat" ]]; then
      flirt -in "$d/${TRACT}_${name}_t1.nii.gz" -ref "$ref" -applyxfm -init "$mat" -out "$d/${TRACT}_${name}_diff.nii.gz" -interp nearestneighbour
    else   # T1 and diffusion already share a grid: just resample onto the diffusion reference
      flirt -in "$d/${TRACT}_${name}_t1.nii.gz" -ref "$ref" -applyxfm -usesqform -out "$d/${TRACT}_${name}_diff.nii.gz" -interp nearestneighbour
    fi
    fslmaths "$d/${TRACT}_${name}_diff.nii.gz" -thr 0.5 -bin "$d/${TRACT}_${name}_diff.nii.gz"
  done
  echo ">> $s done"
}
export -f run_one
while read -r s; do run_one "$s" & while [ "$(jobs -r | wc -l)" -ge "$MAXJOBS" ]; do sleep 1; done; done < "$SUBJECTS_FILE"; wait
# Audit: voxel counts, binariness, seed/target overlap (must be 0)
printf "\nSubject\tseed_vox\ttarget_vox\tatlas_vox\tseed∩target\n"
while read -r s; do d="$OUT/$s/rois"
  sv=$(fslstats "$d/${TRACT}_seed_diff.nii.gz" -V | awk '{print $1}'); tv=$(fslstats "$d/${TRACT}_target_diff.nii.gz" -V | awk '{print $1}'); av=$(fslstats "$d/${TRACT}_atlas_diff.nii.gz" -V | awk '{print $1}')
  ov=$(fslmaths "$d/${TRACT}_seed_diff.nii.gz" -mul "$d/${TRACT}_target_diff.nii.gz" /tmp/_ov_$s -odt char && fslstats /tmp/_ov_$s -V | awk '{print $1}'); rm -f /tmp/_ov_$s.nii.gz
  printf "%s\t%s\t%s\t%s\t%s\n" "$s" "$sv" "$tv" "$av" "$ov"; done < "$SUBJECTS_FILE"
