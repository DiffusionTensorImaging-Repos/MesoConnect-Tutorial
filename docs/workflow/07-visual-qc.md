---
sidebar_position: 8
title: "7. Quality control"
---

# Step 7. Quality control of cleaned bundles

Every participant and hemisphere is inspected after cleaning. The script converts each cleaned bundle to a tract-density image with `tckmap`, selects the axial and coronal slices of greatest density, overlays the image on the mean b0, and writes one image per participant together with automatic flags (Table 1).

**Table 1.** *Automatic flags.*

| Flag | Criterion |
|---|---|
| `LOW_VOXELS` | fewer than 50 tract-density voxels |
| `HIGH_VOXELS` | more than 5,000 tract-density voxels |
| `LOW_DENSITY` | maximum density below 5 streamlines per voxel |

The corresponding script is [`07_visual_qc.py`](pathname:///MesoConnect-Tutorial/scripts/07_visual_qc.py); flags are printed on the image.

## Criteria

A correct reconstruction shows the expected shape for the tract (for VTA → hippocampus, an arc from the ventral midbrain laterally into the medial temporal lobe), consistent shape across participants with variation in size, and no isolated voxel clusters, no density in the contralateral hemisphere or frontal lobe, and no empty tracts (Figures 1 to 3).

![Cleaned tract](/img/step26_qc_s169_left.png)

*Figure 1.* Cleaned left posterior VTA → hippocampus tract, one participant.

![Lowest retention](/img/step26_qc_s0105_left.png)

*Figure 2.* The participant with the lowest cleaning retention (26%; 659 streamlines).

![Anterior cleaned](/img/anterior_step26a_tract_s169.png)

*Figure 3.* Cleaned anterior VTA → hippocampus tract.

## Interactive review

The overlay images support a batch review. Flagged participants, and a sample of unflagged participants, should additionally be examined in a viewer with slice navigation, magnification and opacity control.

```bash
fsleyes "$PROJECT/dwi/$s/mean_b0.nii.gz" \
  "$OUT/$s/tckgen/$TRACT/${TRACT}_${CUTOFF}_cleaned.tck" -cm hot -a 70 &

mrview "$PROJECT/dwi/$s/mean_b0.nii.gz" \
  -tractography.load "$OUT/$s/tckgen/$TRACT/${TRACT}_${CUTOFF}_cleaned.tck" &
```

## Comparison with the atlas

For a quantitative check, each participant's cleaned tract-density image can be warped to MNI space with the inverse warp from step 1 and compared with the atlas by Dice overlap against the 50% map, or by the fraction of the participant tract lying within the 25% probability map. This overlap should not be reported as validation of the atlas, because the reconstruction was constrained by it.

```bash
tckmap "$tck" "$tdi" -template "$PROJECT/dwi/$s/nodif_brain_mask.nii.gz" -force
fslmaths "$tdi" -thr 1 -bin "${tdi%.nii.gz}_bin.nii.gz"
```

## Example dataset

All 114 posterior and 114 anterior tracts passed without flags. The two participants with borderline registration scores in step 2 passed.
