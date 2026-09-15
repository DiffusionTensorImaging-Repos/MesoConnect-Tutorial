---
sidebar_position: 8
title: "7. Visual QC"
---

# 7. Look at every cleaned bundle

This is not optional and not a sample. Every subject, every hemisphere, after cleaning.

The script converts each cleaned `.tck` to a tract-density image with `tckmap`, picks the axial and coronal slices with the most density, overlays the TDI on the mean b0, and writes one PNG per subject with automatic flags.

| Flag | Rule |
|---|---|
| `LOW_VOXELS` | fewer than 50 TDI voxels |
| `HIGH_VOXELS` | more than 5,000 |
| `LOW_DENSITY` | maximum density under 5 streamlines per voxel |

Script: [`07_visual_qc.py`](pathname:///MesoConnect-Tutorial/scripts/07_visual_qc.py). Flagged subjects get the flag printed on the image.

## What to look for

- The expected shape: for VTA → hippocampus, an arc from the ventral midbrain laterally into the medial temporal lobe.
- Consistent shape across subjects; size will vary.
- No stray blobs, nothing in the contralateral hemisphere or the frontal lobe, no empty tracts.

A cleaned posterior VTA → hippocampus tract:

![Cleaned tract](/img/step26_qc_s169_left.png)

The subject with the lowest retention (26%, 659 streamlines) still shows a clear bundle:

![Lowest retention](/img/step26_qc_s0105_left.png)

Anterior tract:

![Anterior cleaned](/img/anterior_step26a_tract_s169.png)

## Interactive review

Static PNGs are for the batch pass. Load anything flagged, and a random handful that were not, in a viewer where you can scroll, zoom and change opacity.

```bash
fsleyes "$PROJECT/dwi/$s/mean_b0.nii.gz" \
  "$OUT/$s/tckgen/$TRACT/${TRACT}_${CUTOFF}_cleaned.tck" -cm hot -a 70 &

# or
mrview "$PROJECT/dwi/$s/mean_b0.nii.gz" \
  -tractography.load "$OUT/$s/tckgen/$TRACT/${TRACT}_${CUTOFF}_cleaned.tck" &
```

## Compare to the atlas

For a quantitative check, warp each subject's cleaned TDI back to MNI with the inverse warp from step 1 and compute Dice against the 50% atlas, or the fraction of the subject tract inside the 25% probability map. Do not present that overlap as validation of the atlas; the tract was constrained by it.

```bash
tckmap "$tck" "$tdi" -template "$PROJECT/dwi/$s/nodif_brain_mask.nii.gz" -force
fslmaths "$tdi" -thr 1 -bin "${tdi%.nii.gz}_bin.nii.gz"
```

## Result in the example

114 of 114 posterior and 114 of 114 anterior tracts passed with zero flags. The two subjects with borderline registration scores in step 2 both passed here, which is the check that mattered.
