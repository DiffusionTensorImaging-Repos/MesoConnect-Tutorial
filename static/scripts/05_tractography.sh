#!/bin/bash
# =============================================================================
# Step 5. Corridor-constrained tractography for every participant
# =============================================================================
# Seeds in the seed region, requires the target region, and discards any
# streamline that leaves the corridor (single exclusion mask from Step 3).
# Participants are processed serially; tckgen uses $NTHREADS threads.
# Writes <tract>_<cutoff>.tck per participant and a summary of streamlines
# selected and streamlines generated (selected plus rejected).  The streamline
# count and length used as model covariates are taken from the cleaned bundles
# in Step 6, not from this step.
# =============================================================================
source "$(dirname "$0")/00_config.sh"
start_log "$0"
read_subjects

for s in "${SUBJECTS[@]}"; do
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
  # tckgen creates its output file at start-up; writing to a temporary name keeps an
  # interrupted run from being mistaken for a finished tractogram on restart.
  partial="$tdir/${TRACT}_${CUTOFF}.partial.tck"
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

# Audit and summary table (rebuilt from the tractograms on every run)
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
  count=$(tckinfo "$tck" | awk '$1 == "count:" {print $2}')
  generated=$(tckinfo "$tck" | awk '$1 == "total_count:" {print $2}')
  if [ "${count:-0}" -gt 0 ]; then
    meanlen=$(tckstats "$tck" -output mean -quiet | awk '{print $1}')
  else
    meanlen=NA
  fi
  echo "$s,$count,$meanlen,$generated" >> "$stats"
  if [ "${count:-0}" -ge "$SELECT" ]; then
    reached=$((reached + 1))
  else
    echo "SHORT: $s ($count selected of $generated generated)"
  fi
done
echo "reached $SELECT streamlines: $reached / $total"
echo "summary -> $stats"
