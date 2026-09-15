#!/bin/bash
# Step 5 — Full corridor-constrained tractography for every subject.
source "$(dirname "$0")/00_config.sh"
while read -r s; do d="$OUT/$s/rois"; o="$OUT/$s/tckgen/$TRACT"; mkdir -p "$o"
  [[ -f "$PROJECT/dwi/$s/wm_fod_norm.mif" ]] || { echo "!! $s missing FOD"; continue; }
  tckgen "$PROJECT/dwi/$s/wm_fod_norm.mif" "$o/${TRACT}_${CUTOFF}.tck" \
    -seed_image "$d/${TRACT}_seed_diff.nii.gz" -seed_unidirectional \
    -include "$d/${TRACT}_target_diff.nii.gz" -exclude "$d/${TRACT}_exclusion_mask.nii.gz" \
    -select "$SELECT" -seeds "$SEEDS" -cutoff "$CUTOFF" -minlength "$MINLEN" -maxlength "$MAXLEN" \
    -stop -nthreads "$NTHREADS" -force
  echo ">> $s $(tckinfo "$o/${TRACT}_${CUTOFF}.tck" | awk '/^ *count:/{print $2}') streamlines from $(tckinfo "$o/${TRACT}_${CUTOFF}.tck" | awk '/total_count:/{print $2}') seeds"
done < "$SUBJECTS_FILE"
# Audit
pass=0; fail=0; while read -r s; do f="$OUT/$s/tckgen/$TRACT/${TRACT}_${CUTOFF}.tck"
  n=$( [ -f "$f" ] && tckinfo "$f" | awk '/^ *count:/{print $2}' || echo 0 ); [ "$n" -ge "$SELECT" ] && pass=$((pass+1)) || { fail=$((fail+1)); echo "SHORT: $s ($n)"; }; done < "$SUBJECTS_FILE"
echo "reached $SELECT streamlines: $pass / $((pass+fail))"
