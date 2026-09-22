---
sidebar_position: 6
title: "Step 5. Tractography"
---

# Step 5. Corridor-constrained tractography

Tractography is performed with `tckgen` using second-order integration over fibre orientation distributions (iFOD2; Tournier et al., 2010). Seeding is unidirectional from the seed region, the target region is required, and the inverted corridor from Step 3 is supplied as the exclusion mask.

## Procedure

```bash
tckgen "$PROJECT/dwi/$s/wm_fod_norm.mif" "$tck" \
  -algorithm iFOD2 \
  -seed_image "$rois/${TRACT}_seed_diff.nii.gz" -seed_unidirectional \
  -include "$rois/${TRACT}_target_diff.nii.gz" \
  -exclude "$rois/${TRACT}_exclusion_mask.nii.gz" \
  -select 2500 -seeds 25000000 -cutoff 0.01 \
  -minlength 35 -maxlength 65 -stop \
  -nthreads 8 -force
```

Table 1 gives the rationale for each option, and Table 2 the values used per tract family. The script records the number of streamlines selected and the number generated (equal to the number of seeds consumed) per participant in `$OUT/qc/<tract>_tckgen_summary.csv`. The streamline count and mean length that enter the group-level models as covariates are taken from the cleaned bundle in Step 6, because every uncleaned tractogram that reaches the target contains the same number of streamlines. The full script follows. At 3 T with eight threads each participant and hemisphere requires approximately 2 min; 57 participants with both hemispheres required about 4 hr run serially.

**Table 1**

*Tractography Parameters*

| Option | Value | Rationale |
|---|---|---|
| `-cutoff` | from Step 4 (0.01 in the example dataset) | The corridor permits a low cutoff. |
| `-select` | 2500 | Sufficient for stable profiles and endpoint maps. Streamline count is not a measure of connectivity; participants who stop short are retained. |
| `-seeds` | 25,000,000 | Ceiling on seeding attempts. The default (1,000 × `select`) is sometimes insufficient to reach 2,500. |
| `-minlength`, `-maxlength` | 35, 65 mm | Set for VTA → hippocampus at 7 T. The example dataset retained them at 3 T, with mean lengths of 44 to 47 mm. Set per tract family from pilot lengths. |
| `-seed_unidirectional` | on | Tracking proceeds away from the seed only. |
| `-stop` | on | Tracking terminates on entering the target. |
| gradient table | embedded in the `.mif` | `-fslgrad` is omitted when the FOD image was built from a `.mif` containing gradients. |

*Note.* VTA = ventral tegmental area; FOD = fibre orientation distribution.

**Table 2**

*Parameters by Tract Family*

| Family | Cutoff with the corridor | Cutoff at 7 T (atlas construction) | Length bounds | Notes |
|---|---|---|---|---|
| VTA → hippocampus, posterior and anterior | 0.01 | 0.06 | 35–65 mm | Used for the example dataset at 3 T. |
| VTA → amygdala | 0.01, confirm by pilot | 0.06 | determine by pilot | Shorter tract; lower bounds expected. |
| VTA → accumbens, superior and inferior | 0.01 | 0.06 | determine by pilot | 0.01 has been used with the corridor by other users of the atlas. |
| Ventral pallidum → VTA | 0.01, confirm by pilot | 0.06 | determine by pilot | |
| Hippocampus → accumbens; hippocampus → ventral pallidum | 0.01, confirm by pilot | 0.08 | determine by pilot | Frequently reconstructs as two clusters; see Step 6. |

*Note.* Where a pilot is indicated, the length bounds are taken from the mean lengths reported in the Step 4 summary.

<!-- script:05_tractography.sh -->
<details>
<summary>Script <code>05_tractography.sh</code> (85 lines)</summary>

```bash title="05_tractography.sh"
#!/bin/bash
# =============================================================================
# Step 5. Corridor-constrained tractography for every participant
# =============================================================================
# Tracks from seed to target and drops any streamline that leaves the Step 3 corridor.
# In:  $PROJECT/dwi/<s>/wm_fod_norm.mif; $OUT/<s>/rois/<TRACT>_{seed,target}_diff.nii.gz,
#      $OUT/<s>/rois/<TRACT>_exclusion_mask.nii.gz
# Out: $OUT/<s>/tckgen/<TRACT>/<TRACT>_<CUTOFF>.tck; $OUT/qc/<TRACT>_tckgen_summary.csv
# Run: bash 05_tractography.sh  (FORCE=1 redoes everyone; about 2 hr for 57 participants)
# =============================================================================
source "$(dirname "$0")/00_config.sh"
start_log "$0"
read_subjects

# --- Tractography, one participant at a time; tckgen itself uses NTHREADS cores ---
for s in "${SUBJECTS[@]}"; do
  rois="$OUT/$s/rois"
  tdir="$OUT/$s/tckgen/$TRACT"
  # The cutoff is in the file name, so a new cutoff is never skipped as "exists".
  tck="$tdir/${TRACT}_${CUTOFF}.tck"
  if [ ! -f "$PROJECT/dwi/$s/wm_fod_norm.mif" ]; then
    echo "!! $s missing FOD image (run 00b)"
    continue
  fi
  # The exclusion mask is the last thing Step 3 writes, so it stands in for seed and target.
  if [ ! -f "$rois/${TRACT}_exclusion_mask.nii.gz" ]; then
    echo "!! $s missing corridor (run Steps 2 and 3)"
    continue
  fi
  if [ "$FORCE" != 1 ] && [ -f "$tck" ]; then
    echo "== $s tractogram exists"
    continue
  fi
  mkdir -p "$tdir"
  # tckgen creates the output at start-up; write to a temp name so an interrupted run is redone.
  partial="$tdir/${TRACT}_${CUTOFF}.partial.tck"
  # -seed_unidirectional: track one way from the seed.  -stop: end on entering the target.
  # -exclude is the inverted corridor, which is what makes a cutoff this low safe.
  if tckgen "$PROJECT/dwi/$s/wm_fod_norm.mif" "$partial" \
    -algorithm iFOD2 \
    -seed_image "$rois/${TRACT}_seed_diff.nii.gz" -seed_unidirectional \
    -include "$rois/${TRACT}_target_diff.nii.gz" \
    -exclude "$rois/${TRACT}_exclusion_mask.nii.gz" \
    -select "$SELECT" -seeds "$SEEDS" -cutoff "$CUTOFF" \
    -minlength "$MINLEN" -maxlength "$MAXLEN" -stop \
    -nthreads "$NTHREADS" -force; then
    mv -f "$partial" "$tck"
    echo ">> $s finished"
  else
    rm -f "$partial"
    echo "!! $s tckgen failed or was interrupted"
  fi
done

# --- Summary table, rebuilt from everything on disk, not just this run ---
mkdir -p "$OUT/qc"
stats="$OUT/qc/${TRACT}_tckgen_summary.csv"
echo "Subject,Selected,MeanLength_mm,Generated" > "$stats"
reached=0
total=0
for s in "${SUBJECTS[@]}"; do
  tck="$OUT/$s/tckgen/$TRACT/${TRACT}_${CUTOFF}.tck"
  total=$((total + 1))
  if [ ! -f "$tck" ]; then
    echo "MISSING: $s"
    continue
  fi
  # count = streamlines kept; total_count = streamlines generated, including rejected ones.
  count=$(tckinfo "$tck" | awk '$1 == "count:" {print $2}')
  generated=$(tckinfo "$tck" | awk '$1 == "total_count:" {print $2}')
  if [ "${count:-0}" -gt 0 ]; then
    meanlen=$(tckstats "$tck" -output mean -quiet | awk '{print $1}')
  else
    meanlen=NA
  fi
  echo "$s,$count,$meanlen,$generated" >> "$stats"
  # Anyone short is still kept (count is not connectivity); SHORT flags whom to check in Step 7.
  if [ "${count:-0}" -ge "$SELECT" ]; then
    reached=$((reached + 1))
  else
    echo "SHORT: $s ($count selected of $generated generated)"
  fi
done
echo "reached $SELECT streamlines: $reached / $total"
echo "summary -> $stats"
```

</details>
<!-- /script:05_tractography.sh -->

## Verification

The script reports the number of participants reaching the streamline target and, for each participant, the number of streamlines generated. Reaching the target in every participant with a small fraction of the seed ceiling is the expected outcome. A participant reaching a lower count, for example 1,800, is retained; a participant reaching a very low count, for example 50, is reviewed in Step 7.
