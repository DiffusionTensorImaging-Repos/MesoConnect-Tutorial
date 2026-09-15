---
sidebar_position: 4
title: "3. Build the corridor"
---

# 3. Build the corridor mask

The atlas was built with a dozen hand-tidied exclusion ROIs per tract. You do not need them. The atlas already encodes where streamlines for this tract plausibly go, so one operation replaces all of them:

1. Dilate the warped atlas by one or two voxels.
2. Add the seed and target and binarize. This is the **inclusion zone**.
3. Invert it. Everything outside the zone becomes a single **exclusion mask** for `tckgen`.

```bash
fslmaths "$d/${TRACT}_atlas_diff.nii.gz" -dilM -dilM "$d/${TRACT}_atlas_dilated.nii.gz"
fslmaths "$d/${TRACT}_atlas_dilated.nii.gz" -add "$d/${TRACT}_seed_diff.nii.gz" \
         -add "$d/${TRACT}_target_diff.nii.gz" -bin "$d/${TRACT}_inclusion_zone.nii.gz"
fslmaths "$d/${TRACT}_inclusion_zone.nii.gz" -binv "$d/${TRACT}_exclusion_mask.nii.gz"
```

The seed and target have to be added before inverting, otherwise the corridor starts and ends a voxel short of them and tracking fails at the boundary.

Script: [`03_build_corridor_mask.sh`](pathname:///MesoConnect-Tutorial/scripts/03_build_corridor_mask.sh). Seconds per subject; `DILATE_VOX` in the config sets the number of `-dilM` passes.

## How much to dilate

Two voxels is the default and worked at 3 T with 2 mm voxels. One voxel is tighter and appropriate if your registration is good and the pilot tracts look loose. Four is a sensitivity setting for uncertain registration. The 50% atlas is already a little wider than the median subject's core, which is why two voxels suffice; dilating a 25% atlas by four is a corridor in name only. Treat dilation as a tractography-enabling step, not as a change to the atlas definition, and report it.

## Audit

The script confirms the seed and target have value 0 in the exclusion mask (not excluded) and prints the corridor size. Add checks for binariness, dimensions matching the DWI, and that the inclusion zone is under 20% of the brain. Example dataset: corridor sizes ran 1,526 to 1,934 voxels (mean 1,720) for the posterior tract and about 1,400 for the anterior, consistent across subjects. An automated coverage check that flags zones under 1% of brain volume will flag every subject; the corridor is supposed to be that small.

## Look at it

Inclusion zone in cyan over the mean b0, seed and target inside it:

![Anterior inclusion zone](/img/anterior_step22a_incl.png)

The corridor should trace a plausible path from seed to target and contain both. A corridor that touches the ventricle or spills into cortex means too much dilation or a bad registration.
