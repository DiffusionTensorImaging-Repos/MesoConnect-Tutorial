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
#
# This is the production version of the tckgen call piloted in Step 4: the full budget
# (SELECT streamlines out of at most SEEDS attempts) and the cutoff you settled on there.
# Nothing in this file is tract-specific; every value comes from 00_config.sh.
#
# Needs, per participant:
#   $PROJECT/dwi/<s>/wm_fod_norm.mif               normalized WM FOD (Step 0b)
#   $OUT/<s>/rois/<TRACT>_seed_diff.nii.gz         seed region in diffusion space (Step 2)
#   $OUT/<s>/rois/<TRACT>_target_diff.nii.gz       target region in diffusion space (Step 2)
#   $OUT/<s>/rois/<TRACT>_exclusion_mask.nii.gz    inverted corridor (Step 3)
# Writes:
#   $OUT/<s>/tckgen/<TRACT>/<TRACT>_<CUTOFF>.tck   raw tractogram; Step 6 cleans it
#   $OUT/qc/<TRACT>_tckgen_summary.csv             one row per participant, for you to
#                                                  read; no later step uses it
#   $OUT/logs/05_tractography.sh.log               everything printed, kept on disk
# Usage:
#   bash 05_tractography.sh            skips participants whose .tck already exists
#   FORCE=1 bash 05_tractography.sh    redoes everyone, e.g. after rebuilding the corridor
# Changing CUTOFF changes the file name, so a new cutoff is never skipped as "exists" and
# the old tractogram stays on disk next to it.
# Runtime: about 2 min per participant at 3 T with eight threads, so roughly 2 hr for 57
# participants.  The other hemisphere is a second run of this script with TRACT changed.
# What to look for.  The last lines say how many participants reached SELECT.  In the
# example dataset that was everyone, for both hemispheres and both tracts.  A SHORT line
# means the participant stopped below SELECT; 1,800 is kept as is, something like 50
# gets a look in Step 7 and usually means the cutoff is too high for the data, the
# corridor is too narrow, or the seed or target sits outside it (Troubleshooting page).
# Generated at the SEEDS ceiling with Selected below SELECT means the budget ran out.
# MISSING lines are participants with no tractogram; the reason is earlier in the log.
# =============================================================================
# 00_config.sh holds every project-specific value.  "source" runs it in this shell so
# its exports (PROJECT, OUT, TRACT, CUTOFF, SELECT...) are visible here.  $(...) is
# command substitution; dirname "$0" is the directory this script sits in, so the config
# is found no matter which directory you run from.
source "$(dirname "$0")/00_config.sh"
# Two helpers from 00_config.sh.  start_log copies everything printed below into
# $OUT/logs/05_tractography.sh.log (tee, with stderr folded in by 2>&1) while still
# showing it on screen; tckgen's own messages and the SHORT/MISSING lines end up
# there.  read_subjects fills the array SUBJECTS with the IDs in $SUBJECTS_FILE.
start_log "$0"
read_subjects

# Main loop, one participant at a time.  "${SUBJECTS[@]}" expands the array to one word
# per ID with the quotes intact.  Serial: tckgen already uses NTHREADS cores for one
# participant, so this step peaks at NTHREADS (see the load note in 00_config.sh).
for s in "${SUBJECTS[@]}"; do
  rois="$OUT/$s/rois"
  tdir="$OUT/$s/tckgen/$TRACT"
  # The cutoff is part of the file name; Step 6 looks for exactly this name.
  tck="$tdir/${TRACT}_${CUTOFF}.tck"
  # Input checks.  [ ! -f file ] is true when the file is absent; "continue" jumps to the
  # next participant instead of letting tckgen die with a less helpful message.  The
  # exclusion mask is the last image Step 3 writes, so if it is there the corridor is
  # complete, and Step 3 needed the seed and target to build it, so those are not
  # checked separately.
  if [ ! -f "$PROJECT/dwi/$s/wm_fod_norm.mif" ]; then
    echo "!! $s missing FOD image (run 00b)"
    continue
  fi
  if [ ! -f "$rois/${TRACT}_exclusion_mask.nii.gz" ]; then
    echo "!! $s missing corridor (run Steps 2 and 3)"
    continue
  fi
  # Skip-if-exists, so a run that was interrupted picks up where it left off.  FORCE
  # comes from 00_config.sh (default 0); FORCE=1 on the command line redoes everyone.
  if [ "$FORCE" != 1 ] && [ -f "$tck" ]; then
    echo "== $s tractogram exists"
    continue
  fi
  # mkdir -p makes the parent directories too and is silent if they already exist.
  mkdir -p "$tdir"
  # tckgen creates its output file at start-up; writing to a temporary name keeps an
  # interrupted run from being mistaken for a finished tractogram on restart.
  partial="$tdir/${TRACT}_${CUTOFF}.partial.tck"
  # "if command; then" branches on the command's exit status (0 = success), so a tckgen
  # error lands in the else branch below.  Comments cannot sit between the
  # backslash-continued lines, so the options are explained here:
  #   -algorithm iFOD2      probabilistic tracking with second-order integration over
  #                         the FOD; the tckgen default, spelled out anyway
  #   -seed_image           every streamline starts inside the warped seed region
  #   -seed_unidirectional  track away from the seed in one direction only, not both
  #   -include              keep a streamline only if it reaches the target region
  #   -exclude              discard a streamline the moment it enters this image.  The
  #                         image is the inverted corridor, so this fires the moment a
  #                         streamline leaves the corridor.  It is the only exclusion
  #                         region, and it is what makes a 0.01 cutoff usable at all.
  #   -select 2500          stop once this many streamlines have passed every rule.
  #                         Enough for stable profiles and endpoint maps; more just costs
  #                         time.  Not a connectivity measure: everyone who reaches the
  #                         target gets the same count, which is why the covariate count
  #                         comes from the cleaned bundle in Step 6 instead.
  #   -seeds 25000000       ceiling on seeding attempts; tckgen gives up here even if
  #                         SELECT was not reached.  The default (1000 x select) was
  #                         sometimes not enough to reach 2500.
  #   -cutoff 0.01          minimum FOD amplitude at which tracking continues (MRtrix
  #                         default 0.05).  Chosen in Step 4; only safe this low because
  #                         the corridor keeps streamlines from wandering.  In the Step 4
  #                         pilot, higher values burned many more seeds and failed to
  #                         reach the target in some participants.
  #   -minlength/-maxlength length bounds in mm.  35 and 65 were set for VTA ->
  #                         hippocampus and held at 3 T (mean lengths 44 to 47 mm); for
  #                         another tract family set them from the Step 4 pilot means.
  #                         Streamlines outside the window are rejected outright, so a
  #                         window that is too tight throws away real ones.
  #   -stop                 end the streamline on entering the target instead of letting
  #                         it run on past it, so the bundle ends where the target starts
  #   -nthreads             threads for this one command (NTHREADS in 00_config.sh)
  #   -force                overwrite the output if it exists, e.g. a .partial.tck left by
  #                         a run that was killed before the rm -f below could run
  # No -fslgrad: the gradient table is already inside the .mif from Step 0b.  No -quiet
  # either, so tckgen's own messages and warnings land in the log via start_log.
  if tckgen "$PROJECT/dwi/$s/wm_fod_norm.mif" "$partial" \
    -algorithm iFOD2 \
    -seed_image "$rois/${TRACT}_seed_diff.nii.gz" -seed_unidirectional \
    -include "$rois/${TRACT}_target_diff.nii.gz" \
    -exclude "$rois/${TRACT}_exclusion_mask.nii.gz" \
    -select "$SELECT" -seeds "$SEEDS" -cutoff "$CUTOFF" \
    -minlength "$MINLEN" -maxlength "$MAXLEN" -stop \
    -nthreads "$NTHREADS" -force; then
    # Success: rename to the final name in one step.  mv -f replaces an existing target
    # without asking, which a FORCE=1 rerun needs.
    mv -f "$partial" "$tck"
    echo ">> $s finished"
  else
    # Failure: drop the partial so the next run redoes this participant instead of
    # skipping it.  rm -f does not complain if the file is already gone.
    rm -f "$partial"
    echo "!! $s tckgen failed or was interrupted"
  fi
done

# Audit and summary table (rebuilt from the tractograms on every run)
# Loops over everyone again, including participants skipped above as "exists", so the
# CSV always describes what is on disk and not just what this run produced.
mkdir -p "$OUT/qc"
stats="$OUT/qc/${TRACT}_tckgen_summary.csv"
# ">" truncates the file and writes the header row; the rows below use ">>" to append.
# Columns: participant ID, streamlines selected, mean length in mm, streamlines
# generated (selected plus rejected, which is also the number of seeds consumed).
echo "Subject,Selected,MeanLength_mm,Generated" > "$stats"
# Tallies for the closing line.  $((...)) is shell integer arithmetic.
reached=0
total=0
for s in "${SUBJECTS[@]}"; do
  tck="$OUT/$s/tckgen/$TRACT/${TRACT}_${CUTOFF}.tck"
  total=$((total + 1))
  # No tractogram means an input was missing or tckgen failed above; the reason is
  # earlier in the log.  These participants get no CSV row.
  if [ ! -f "$tck" ]; then
    echo "MISSING: $s"
    continue
  fi
  # tckinfo prints the .tck header as "key: value" lines.  awk keeps the line whose
  # first field ($1) is the key we want and prints the second field, the number.
  # count = streamlines written (selected); total_count = streamlines generated,
  # including every one that was rejected.
  count=$(tckinfo "$tck" | awk '$1 == "count:" {print $2}')
  generated=$(tckinfo "$tck" | awk '$1 == "total_count:" {print $2}')
  # Mean streamline length in mm.  tckstats -output mean prints only the mean; -quiet
  # keeps its own messages out of the log.  awk '{print $1}' takes the first field on the
  # line in case anything trails it.  ${count:-0} substitutes 0 when count is empty
  # (tckinfo failed) so -gt does not choke on an empty string.  An empty tractogram has
  # nothing to average, hence NA.
  if [ "${count:-0}" -gt 0 ]; then
    meanlen=$(tckstats "$tck" -output mean -quiet | awk '{print $1}')
  else
    meanlen=NA
  fi
  echo "$s,$count,$meanlen,$generated" >> "$stats"
  # Did this participant reach SELECT?  -ge is integer >=.  Anyone short is still kept
  # (count is not connectivity); the SHORT line is so you know whom to look at in
  # Step 7.  Generated near SEEDS with Selected well below SELECT means the seed budget
  # ran out before 2500 streamlines made it through.
  if [ "${count:-0}" -ge "$SELECT" ]; then
    reached=$((reached + 1))
  else
    echo "SHORT: $s ($count selected of $generated generated)"
  fi
done
# The closing tally.  In the example dataset every participant reached 2,500 in both
# hemispheres, with Generated between 0.5 and 2 million (about 4% of SEEDS) for the
# posterior tract and 1.5 to 11 million for the anterior one, whose corridor is smaller.
# Next: python 06_clean_bundles.py reads the .tck files written above.
echo "reached $SELECT streamlines: $reached / $total"
echo "summary -> $stats"
