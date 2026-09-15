---
sidebar_position: 8
title: "7. Visual QC"
---

# 7. Visual QC of cleaned bundles

Every subject and hemisphere is inspected after cleaning.

The script converts each cleaned `.tck` to a tract-density image with `tckmap`, selects the axial and coronal slices with the greatest density, overlays the TDI on the mean b0, and writes one PNG per subject with automatic flags.

| Flag | Rule |
|---|---|
| `LOW_VOXELS` | fewer than 50 TDI voxels |
| `HIGH_VOXELS` | more than 5,000 |
| `LOW_DENSITY` | maximum density under 5 streamlines per voxel |

Script: [`07_visual_qc.py`](pathname:///MesoConnect-Tutorial/scripts/07_visual_qc.py). Flags are printed on the image.

## Expected appearance

- The expected shape for the tract. For VTA → hippocampus, an arc from the ventral midbrain laterally into the medial temporal lobe.
- Consistent shape across subjects, with variation in size.
- No isolated clusters of voxels, no density in the contralateral hemisphere or frontal lobe, no empty tracts.

A cleaned posterior VTA → hippocampus tract:

![Cleaned tract](/img/step26_qc_s169_left.png)

The subject with the lowest retention (26%, 659 streamlines):

![Lowest retention](/img/step26_qc_s0105_left.png)

Anterior tract:

![Anterior cleaned](/img/anterior_step26a_tract_s169.png)

## Interactive review

The PNGs support a batch pass. Load flagged subjects, and a sample of unflagged ones, in a viewer with slice navigation, zoom and opacity control.

```bash
fsleyes "$PROJECT/dwi/$s/mean_b0.nii.gz" \
  "$OUT/$s/tckgen/$TRACT/${TRACT}_${CUTOFF}_cleaned.tck" -cm hot -a 70 &

# or
mrview "$PROJECT/dwi/$s/mean_b0.nii.gz" \
  -tractography.load "$OUT/$s/tckgen/$TRACT/${TRACT}_${CUTOFF}_cleaned.tck" &
```

## Comparison to the atlas

For a quantitative check, warp each subject's cleaned TDI to MNI with the inverse warp from step 1 and compute Dice against the 50% atlas, or the fraction of the subject tract inside the 25% probability map. This overlap should not be reported as validation of the atlas, since the reconstruction was constrained by it.

```bash
tckmap "$tck" "$tdi" -template "$PROJECT/dwi/$s/nodif_brain_mask.nii.gz" -force
fslmaths "$tdi" -thr 1 -bin "${tdi%.nii.gz}_bin.nii.gz"
```

## Example dataset

All 114 posterior and 114 anterior tracts passed with no flags. The two subjects with borderline registration scores in step 2 passed.
