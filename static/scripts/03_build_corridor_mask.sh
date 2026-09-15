#!/bin/bash
# Step 3 — Build the corridor: dilate the warped atlas, add seed + target, binarize, invert.
# The inverted image is a single exclusion mask for tckgen (everything outside the corridor).
source "$(dirname "$0")/00_config.sh"
DIL=""; for ((i=0;i<DILATE_VOX;i++)); do DIL="$DIL -dilM"; done
run_one() {
  s=$1; d="$OUT/$s/rois"
  [[ -f "$d/${TRACT}_atlas_diff.nii.gz" ]] || { echo "!! $s missing warped atlas"; return; }
  fslmaths "$d/${TRACT}_atlas_diff.nii.gz" $DIL "$d/${TRACT}_atlas_dilated.nii.gz"
  fslmaths "$d/${TRACT}_atlas_dilated.nii.gz" -add "$d/${TRACT}_seed_diff.nii.gz" -add "$d/${TRACT}_target_diff.nii.gz" -bin "$d/${TRACT}_inclusion_zone.nii.gz"
  fslmaths "$d/${TRACT}_inclusion_zone.nii.gz" -binv "$d/${TRACT}_exclusion_mask.nii.gz"
  echo ">> $s corridor voxels: $(fslstats "$d/${TRACT}_inclusion_zone.nii.gz" -V | awk '{print $1}')"
}
export -f run_one; export DIL
while read -r s; do run_one "$s" & while [ "$(jobs -r | wc -l)" -ge "$MAXJOBS" ]; do sleep 0.5; done; done < "$SUBJECTS_FILE"; wait
# Audit: seed and target must NOT be excluded (value 0 inside the exclusion mask)
printf "\nSubject\tseed_excluded\ttarget_excluded\tcorridor_vox\n"
while read -r s; do d="$OUT/$s/rois"
  se=$(fslmaths "$d/${TRACT}_exclusion_mask.nii.gz" -mul "$d/${TRACT}_seed_diff.nii.gz" /tmp/_se_$s -odt char && fslstats /tmp/_se_$s -V | awk '{print $1}')
  te=$(fslmaths "$d/${TRACT}_exclusion_mask.nii.gz" -mul "$d/${TRACT}_target_diff.nii.gz" /tmp/_te_$s -odt char && fslstats /tmp/_te_$s -V | awk '{print $1}')
  rm -f /tmp/_se_$s.nii.gz /tmp/_te_$s.nii.gz
  printf "%s\t%s\t%s\t%s\n" "$s" "$se" "$te" "$(fslstats "$d/${TRACT}_inclusion_zone.nii.gz" -V | awk '{print $1}')"; done < "$SUBJECTS_FILE"
