#!/bin/bash
# Step 4 — Pilot the FOD cutoff on a handful of subjects before the full run.
# Usage: 04_tune_cutoff.sh "s001 s002 s003 s004 s005" "0.1 0.08 0.06 0.01"
source "$(dirname "$0")/00_config.sh"; start_log "$0"
PILOT=${1:-"$(head -5 "$SUBJECTS_FILE" | tr '\n' ' ')"}; CUTOFFS=${2:-"0.1 0.08 0.06 0.01"}
printf "%-10s %-8s %-12s %-12s %-10s\n" Subject Cutoff Streamlines Seeds MeanLen_mm
for s in $PILOT; do d="$OUT/$s/rois"; o="$OUT/$s/tckgen/$TRACT"; mkdir -p "$o"
  for c in $CUTOFFS; do
    tckgen "$PROJECT/dwi/$s/wm_fod_norm.mif" "$o/${TRACT}_pilot_${c}.tck" \
      -seed_image "$d/${TRACT}_seed_diff.nii.gz" -seed_unidirectional \
      -include "$d/${TRACT}_target_diff.nii.gz" -exclude "$d/${TRACT}_exclusion_mask.nii.gz" \
      -select 1000 -seeds 5000000 -cutoff "$c" -minlength "$MINLEN" -maxlength "$MAXLEN" -stop -nthreads "$NTHREADS" -force -quiet
    n=$(tckinfo "$o/${TRACT}_pilot_${c}.tck" | awk '/^ *count:/{print $2}'); sd=$(tckinfo "$o/${TRACT}_pilot_${c}.tck" | awk '/total_count:/{print $2}')
    ml=$(tckstats "$o/${TRACT}_pilot_${c}.tck" -quiet | awk '/mean/{print $2; exit}')
    printf "%-10s %-8s %-12s %-12s %-10s\n" "$s" "$c" "$n" "$sd" "$ml"
  done
done
echo "Select the most permissive cutoff that reaches the streamline target in every pilot subject."
