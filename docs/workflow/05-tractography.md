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

Table 1 gives the rationale for each option, and Table 2 the values used per tract family. The script records the number of streamlines reached and the number of seeds consumed per participant in `$OUT/qc/<tract>_tckgen_summary.csv`. The streamline count and mean length that enter the group-level models as covariates are taken from the cleaned bundle in Step 6, because every uncleaned tractogram that reaches the target contains the same number of streamlines. The full script follows. At 3 T with eight threads each participant and hemisphere requires approximately 2 min; 57 participants with both hemispheres required about 4 hr run serially.

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

| Family | Cutoff at 7 T (atlas construction) | Length bounds | Notes |
|---|---|---|---|
| VTA → hippocampus, posterior and anterior | 0.06 | 35–65 mm | Example dataset used 0.01 at 3 T with the corridor. |
| VTA → amygdala | 0.06 | determine by pilot | Shorter tract; lower bounds expected. |
| VTA → accumbens, superior and inferior | 0.06 | determine by pilot | 0.01 has been used with the corridor. |
| Ventral pallidum → VTA | 0.06 | determine by pilot | |
| Hippocampus → accumbens; hippocampus → ventral pallidum | 0.08 | determine by pilot | Frequently reconstructs as two clusters; see Step 6. |

*Note.* Where a pilot is indicated, the length bounds are taken from the mean lengths reported in the Step 4 summary.

<!-- script:05_tractography.sh -->
```bash title="05_tractography.sh"
#!/bin/bash
# =============================================================================
# Step 5. Corridor-constrained tractography for every participant
# =============================================================================
# Seeds in the seed region, requires the target region, and discards any
# streamline that leaves the corridor (single exclusion mask from Step 3).
# Participants are processed serially; tckgen uses $NTHREADS threads.
# Writes <tract>_<cutoff>.tck per participant and a summary of streamlines
# reached and seeds consumed.  The streamline count and length used as model
# covariates are taken from the cleaned bundles in Step 6, not from this step.
# =============================================================================
source "$(dirname "$0")/00_config.sh"
start_log "$0"

while read -r s; do
  rois="$OUT/$s/rois"
  tdir="$OUT/$s/tckgen/$TRACT"
  tck="$tdir/${TRACT}_${CUTOFF}.tck"
  if [ ! -f "$PROJECT/dwi/$s/wm_fod_norm.mif" ]; then
    echo "!! $s missing FOD image (run 00b)"
    continue
  fi
  if [ ! -f "$rois/${TRACT}_exclusion_mask.nii.gz" ]; then
    echo "!! $s missing corridor (run Steps 2 and 3)"
    continue
  fi
  if [ "$FORCE" != 1 ] && [ -f "$tck" ]; then
    echo "== $s tractogram exists"
    continue
  fi
  mkdir -p "$tdir"
  tckgen "$PROJECT/dwi/$s/wm_fod_norm.mif" "$tck" \
    -algorithm iFOD2 \
    -seed_image "$rois/${TRACT}_seed_diff.nii.gz" -seed_unidirectional \
    -include "$rois/${TRACT}_target_diff.nii.gz" \
    -exclude "$rois/${TRACT}_exclusion_mask.nii.gz" \
    -select "$SELECT" -seeds "$SEEDS" -cutoff "$CUTOFF" \
    -minlength "$MINLEN" -maxlength "$MAXLEN" -stop \
    -nthreads "$NTHREADS" -force
  echo ">> $s finished"
done < "$SUBJECTS_FILE"

# Audit and summary table (rebuilt from the tractograms on every run)
mkdir -p "$OUT/qc"
stats="$OUT/qc/${TRACT}_tckgen_summary.csv"
echo "Subject,Streamlines,MeanLength_mm,Seeds_used" > "$stats"
reached=0
total=0
while read -r s; do
  tck="$OUT/$s/tckgen/$TRACT/${TRACT}_${CUTOFF}.tck"
  total=$((total + 1))
  if [ ! -f "$tck" ]; then
    echo "MISSING: $s"
    continue
  fi
  count=$(tckinfo "$tck" | awk '$1 == "count:" {print $2}')
  seeds=$(tckinfo "$tck" | awk '$1 == "total_count:" {print $2}')
  if [ "${count:-0}" -gt 0 ]; then
    meanlen=$(tckstats "$tck" -output mean -quiet)
  else
    meanlen=NA
  fi
  echo "$s,$count,$meanlen,$seeds" >> "$stats"
  if [ "${count:-0}" -ge "$SELECT" ]; then
    reached=$((reached + 1))
  else
    echo "SHORT: $s ($count streamlines from $seeds seeds)"
  fi
done < "$SUBJECTS_FILE"
echo "reached $SELECT streamlines: $reached / $total"
echo "summary -> $stats"
```
<!-- /script:05_tractography.sh -->

## Verification

The script reports the number of participants reaching the streamline target. In the example dataset all 114 hemisphere runs reached 2,500 streamlines, consuming 0.5 to 2.0 million seeds (about 4% of the ceiling). The anterior tract also reached 2,500 in all 114 runs, with higher seed consumption (1.5 to 11 million) consistent with its smaller corridor. A participant reaching a lower count, for example 1,800, is retained; a participant reaching a very low count, for example 50, is reviewed in Step 7.
