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
