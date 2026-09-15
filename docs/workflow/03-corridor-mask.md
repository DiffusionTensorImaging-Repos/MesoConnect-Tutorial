---
sidebar_position: 4
title: "3. Corridor mask"
---

# 3. Corridor mask

Atlas construction used a dozen hand-tidied exclusion ROIs per tract. The corridor workflow replaces them with one mask derived from the atlas:

1. Dilate the warped atlas by one or two voxels.
2. Add the seed and target and binarize. This is the inclusion zone.
3. Invert it. Everything outside the zone becomes a single exclusion mask for `tckgen`.

```bash
fslmaths "$d/${TRACT}_atlas_diff.nii.gz" -dilM -dilM "$d/${TRACT}_atlas_dilated.nii.gz"
fslmaths "$d/${TRACT}_atlas_dilated.nii.gz" -add "$d/${TRACT}_seed_diff.nii.gz" \
         -add "$d/${TRACT}_target_diff.nii.gz" -bin "$d/${TRACT}_inclusion_zone.nii.gz"
fslmaths "$d/${TRACT}_inclusion_zone.nii.gz" -binv "$d/${TRACT}_exclusion_mask.nii.gz"
```

The seed and target must be added before inversion. Otherwise the corridor ends short of them and tracking terminates at the boundary.

Script: [`03_build_corridor_mask.sh`](pathname:///MesoConnect-Tutorial/scripts/03_build_corridor_mask.sh). Seconds per subject. `DILATE_VOX` in the configuration sets the number of `-dilM` passes.

## Dilation

Two voxels is the default and was used in the example dataset at 2 mm resolution. One voxel is appropriate when registration is good and pilot tracts appear loose. Four voxels is a sensitivity setting for uncertain registration. The 50% atlas is slightly wider than the median subject's core, which is why two voxels suffice. Report the dilation used.

## Audit

The script confirms that the seed and target have value 0 in the exclusion mask (are not excluded) and prints the corridor size. Additional checks: binariness, dimensions matching the DWI, and inclusion zone below 20% of brain volume. Example dataset: corridor sizes ranged from 1,526 to 1,934 voxels (mean 1,720) for the posterior tract and about 1,400 for the anterior tract. An automated coverage check that flags zones below 1% of brain volume will flag every subject, since the corridor is that small by design.

## Inspection

Inclusion zone in cyan over the mean b0, with seed and target inside it:

![Anterior inclusion zone](/img/anterior_step22a_incl.png)

The corridor should follow a plausible path from seed to target and contain both. Contact with the ventricle or extension into cortex indicates excessive dilation or a registration error.
