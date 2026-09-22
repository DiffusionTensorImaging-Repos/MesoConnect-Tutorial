#!/bin/bash
# =============================================================================
# Step 4. Pilot sweep of the FOD amplitude cutoff
# =============================================================================
# Runs reduced-budget tractography at several cutoffs in a few pilot participants.
# Needs $PROJECT/dwi/<s>/wm_fod_norm.mif (Step 0b) and, from Steps 2 and 3, $OUT/<s>/rois/
#   <TRACT>_seed_diff.nii.gz, <TRACT>_target_diff.nii.gz, <TRACT>_exclusion_mask.nii.gz
# Writes $OUT/<s>/tckgen/<TRACT>/<TRACT>_pilot_<cutoff>.tck and $OUT/logs/04_tune_cutoff.sh.log
# Usage: bash 04_tune_cutoff.sh [participants] [cutoffs]; defaults: first 5, 0.1 0.08 0.06 0.01
source "$(dirname "$0")/00_config.sh"
start_log "$0"
read_subjects

PILOT=${1:-${SUBJECTS[*]:0:5}}
# Highest cutoff first: 04b_compare_cutoffs.py uses the first one as its Dice reference.
CUTOFFS=${2:-"0.1 0.08 0.06 0.01"}
# Reduced budgets so the sweep is cheap; the seed cap stops a failing cutoff in bounded time.
PILOT_SELECT=1000
PILOT_SEEDS=5000000

printf "%-12s %-8s %-12s %-12s %-12s\n" Subject Cutoff Selected Generated MeanLen_mm
for s in $PILOT; do
  rois="$OUT/$s/rois"
  tdir="$OUT/$s/tckgen/$TRACT"
  if [ ! -f "$rois/${TRACT}_exclusion_mask.nii.gz" ]; then
    echo "!! $s missing corridor (run Steps 2 and 3)"
    continue
  fi
  mkdir -p "$tdir"
  for c in $CUTOFFS; do
    tck="$tdir/${TRACT}_pilot_${c}.tck"
    # -seed_unidirectional: track one way from the seed.  -stop: end the streamline once it
    # enters the target.  -exclude: the inverted corridor, so a streamline dies on leaving it.
    tckgen "$PROJECT/dwi/$s/wm_fod_norm.mif" "$tck" \
      -algorithm iFOD2 \
      -seed_image "$rois/${TRACT}_seed_diff.nii.gz" -seed_unidirectional \
      -include "$rois/${TRACT}_target_diff.nii.gz" \
      -exclude "$rois/${TRACT}_exclusion_mask.nii.gz" \
      -select "$PILOT_SELECT" -seeds "$PILOT_SEEDS" -cutoff "$c" \
      -minlength "$MINLEN" -maxlength "$MAXLEN" -stop \
      -nthreads "$NTHREADS" -force -quiet
    count=$(tckinfo "$tck" | awk '$1 == "count:" {print $2}')
    generated=$(tckinfo "$tck" | awk '$1 == "total_count:" {print $2}')
    if [ "${count:-0}" -gt 0 ]; then
      meanlen=$(tckstats "$tck" -output mean -quiet | awk '{print $1}')
    else
      meanlen=NA
    fi
    printf "%-12s %-8s %-12s %-12s %-12s\n" "$s" "$c" "$count" "$generated" "$meanlen"
  done
done
echo "Reaching the streamline target in every pilot participant is necessary but not"
echo "sufficient: compare the reconstructions with 04b_compare_cutoffs.py before choosing."
