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
<details>
<summary>Script <code>03_build_corridor_mask.sh</code> (67 lines)</summary>

```bash title="03_build_corridor_mask.sh"
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
```

</details>
<!-- /script:03_build_corridor_mask.sh -->

## Dilation

A dilation of two voxels was used in the example dataset at 2 mm isotropic resolution. One voxel is appropriate when registration is accurate and pilot reconstructions appear loose; four voxels serves as a sensitivity setting when registration is uncertain. The 50% atlas is already somewhat wider than the median participant's core, which is why two voxels is generally sufficient. The dilation used should be reported.

## Verification

The script confirms that the seed and target voxels have value 0 in the exclusion mask (that is, are not excluded) and reports the corridor size. Additional checks confirm binariness, agreement of dimensions with the diffusion image, and an inclusion zone below 20% of brain volume. In the example dataset corridor sizes ranged from 1,526 to 1,934 voxels (*M* = 1,720) for the posterior tract and approximately 1,400 voxels for the anterior tract. An automated coverage check that flags inclusion zones below 1% of brain volume flags every participant; the corridor is that small by design.

Visual inspection confirms that the corridor follows a plausible path from seed to target and contains both regions (Figure 1). Contact with the ventricle or extension into cortex indicates excessive dilation or a registration error.

**Figure 1**

*Inclusion Zone for the Anterior VTA → Hippocampus Tract*

![Inclusion zone over the mean b = 0 image](/img/fig_inclusion_zone.png)

*Note.* Inclusion zone in cyan over the mean *b* = 0 image, with the seed and target contained within it. Left: axial view. Right: coronal view. VTA = ventral tegmental area.
