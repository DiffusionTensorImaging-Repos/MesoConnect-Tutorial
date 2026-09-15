---
sidebar_position: 4
title: "3. Corridor construction"
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

The seed and target must be added before inversion; otherwise the corridor terminates short of them and tracking stops at the boundary.

The corresponding script is [`03_build_corridor_mask.sh`](pathname:///MesoConnect-Tutorial/scripts/03_build_corridor_mask.sh). The `DILATE_VOX` setting in the configuration controls the number of `-dilM` passes.

## Dilation

A dilation of two voxels was used in the example dataset at 2 mm isotropic resolution. One voxel is appropriate when registration is accurate and pilot reconstructions appear loose; four voxels serves as a sensitivity setting when registration is uncertain. The 50% atlas is already somewhat wider than the median participant's core, which is why two voxels is generally sufficient. The dilation used should be reported.

## Verification

The script confirms that the seed and target voxels have value 0 in the exclusion mask (that is, are not excluded) and reports the corridor size. Additional checks confirm binariness, agreement of dimensions with the diffusion image, and an inclusion zone below 20% of brain volume. In the example dataset corridor sizes ranged from 1,526 to 1,934 voxels (M = 1,720) for the posterior tract and approximately 1,400 voxels for the anterior tract. An automated coverage check that flags inclusion zones below 1% of brain volume flags every participant; the corridor is that small by design.

Visual inspection confirms that the corridor follows a plausible path from seed to target and contains both regions (Figure 1). Contact with the ventricle or extension into cortex indicates excessive dilation or a registration error.

![Anterior inclusion zone](/img/anterior_step22a_incl.png)

*Figure 1.* Inclusion zone (cyan) for the anterior VTA → hippocampus tract over the mean b0 image, with the seed and target contained within it.
