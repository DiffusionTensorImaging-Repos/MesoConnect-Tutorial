---
sidebar_position: 4
title: "Step 3. Corridor construction"
---

# Step 3. Corridor construction

Atlas construction used approximately a dozen individually prepared exclusion regions per tract. The corridor workflow replaces them with a single mask derived from the warped atlas. The atlas is dilated, the seed and target regions are added, the union is binarized to form an inclusion zone, and the inclusion zone is inverted. The inverted image serves as the sole exclusion mask for tractography: any streamline leaving the corridor is discarded.

## Procedure

```bash
fslmaths "$d/${TRACT}_atlas_diff.nii.gz" -dilM -dilM "$d/${TRACT}_atlas_dilated.nii.gz"
fslmaths "$d/${TRACT}_atlas_dilated.nii.gz" -add "$d/${TRACT}_seed_diff.nii.gz" \
         -add "$d/${TRACT}_target_diff.nii.gz" -bin "$d/${TRACT}_inclusion_zone.nii.gz"
fslmaths "$d/${TRACT}_inclusion_zone.nii.gz" -binv "$d/${TRACT}_exclusion_mask.nii.gz"
```

The seed and target must be added before inversion; otherwise the corridor terminates short of them and tracking stops at the boundary. The full script follows; the `DILATE_VOX` setting in the configuration controls the number of `-dilM` passes.

<!-- script:03_build_corridor_mask.sh -->
```bash title="03_build_corridor_mask.sh"
#!/bin/bash
# Step 3 — Build the corridor: dilate the warped atlas, add seed + target, binarize, invert.
# The inverted image is a single exclusion mask for tckgen (everything outside the corridor).
source "$(dirname "$0")/00_config.sh"; start_log "$0"
DIL=""; for ((i=0;i<DILATE_VOX;i++)); do DIL="$DIL -dilM"; done
run_one() {
  s=$1; d="$OUT/$s/rois"
  [[ "$FORCE" = 1 || ! -f "$d/${TRACT}_exclusion_mask.nii.gz" ]] || { echo "== $s corridor exists"; return; }
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
```
<!-- /script:03_build_corridor_mask.sh -->

## Dilation

A dilation of two voxels was used in the example dataset at 2 mm isotropic resolution. One voxel is appropriate when registration is accurate and pilot reconstructions appear loose; four voxels serves as a sensitivity setting when registration is uncertain. The 50% atlas is already somewhat wider than the median participant's core, which is why two voxels is generally sufficient. The dilation used should be reported.

## Verification

The script confirms that the seed and target voxels have value 0 in the exclusion mask (that is, are not excluded) and reports the corridor size. Additional checks confirm binariness, agreement of dimensions with the diffusion image, and an inclusion zone below 20% of brain volume. In the example dataset corridor sizes ranged from 1,526 to 1,934 voxels (*M* = 1,720) for the posterior tract and approximately 1,400 voxels for the anterior tract. An automated coverage check that flags inclusion zones below 1% of brain volume flags every participant; the corridor is that small by design.

Visual inspection confirms that the corridor follows a plausible path from seed to target and contains both regions (Figure 1). Contact with the ventricle or extension into cortex indicates excessive dilation or a registration error.

**Figure 1**

*Inclusion Zone for the Anterior VTA → Hippocampus Tract*

![Inclusion zone over the mean b = 0 image](/img/anterior_step22a_incl.png)

*Note.* Inclusion zone in cyan over the mean *b* = 0 image, with the seed and target contained within it. VTA = ventral tegmental area.
