#!/bin/bash
# =============================================================================
# Step 4. Pilot sweep of the FOD amplitude cutoff
# =============================================================================
# Runs reduced-budget tractography at several cutoffs in a few participants.
# "Selected" is the number of streamlines that met every criterion; "Generated" is
# the number tckgen had to generate (selected plus rejected) to obtain them.
# Usage:
#   bash 04_tune_cutoff.sh "sub-01 sub-02 sub-03 sub-04 sub-05" "0.1 0.08 0.06 0.01"
# Defaults: the first five participants in $SUBJECTS_FILE and the four cutoffs above.
# Follow with 04b_compare_cutoffs.py for the side-by-side images and summary table.
# =============================================================================
source "$(dirname "$0")/00_config.sh"
start_log "$0"
read_subjects

PILOT=${1:-${SUBJECTS[*]:0:5}}
CUTOFFS=${2:-"0.1 0.08 0.06 0.01"}
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
      meanlen=$(tckstats "$tck" -output mean -quiet)
    else
      meanlen=NA
    fi
    printf "%-12s %-8s %-12s %-12s %-12s\n" "$s" "$c" "$count" "$generated" "$meanlen"
  done
done
echo "Reaching the streamline target in every pilot participant is necessary but not"
echo "sufficient: compare the reconstructions with 04b_compare_cutoffs.py before choosing."
