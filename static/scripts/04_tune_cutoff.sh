#!/bin/bash
# =============================================================================
# Step 4. Pilot sweep of the FOD amplitude cutoff
# =============================================================================
# Runs reduced-budget tractography at several cutoffs in a few participants.
# "Selected" is the number of streamlines that met every criterion; "Generated" is
# the number tckgen had to generate (selected plus rejected) to obtain them.  tckgen
# generates one streamline per seed, so it is also the number of seeds consumed.
#
# Why this exists.  The cutoff is the minimum FOD amplitude at which tckgen keeps
# tracking.  Too high and streamlines die before the target; too low and, without a
# corridor, they wander all over the brain.  Inside the corridor a very low cutoff
# (0.01, the default in 00_config.sh) reached the target in every pilot participant of
# the example dataset with about a fifth of the seeds 0.06 needed, and later in all 57
# at the production budget.  That has to be checked again on each new dataset or tract
# family, which is what this sweep is for.
#
# Needs, per pilot participant (Steps 0b, 2 and 3 must have run for them):
#   $PROJECT/dwi/<s>/wm_fod_norm.mif               normalized WM FOD (Step 0b)
#   $OUT/<s>/rois/<TRACT>_seed_diff.nii.gz         seed region in diffusion space (Step 2)
#   $OUT/<s>/rois/<TRACT>_target_diff.nii.gz       target region in diffusion space (Step 2)
#   $OUT/<s>/rois/<TRACT>_exclusion_mask.nii.gz    inverted corridor (Step 3)
# Writes:
#   $OUT/<s>/tckgen/<TRACT>/<TRACT>_pilot_<cutoff>.tck   one tractogram per cutoff
#   $OUT/logs/04_tune_cutoff.sh.log                       the table below, kept on disk
# Usage:
#   bash 04_tune_cutoff.sh "sub-01 sub-02 sub-03 sub-04 sub-05" "0.1 0.08 0.06 0.01"
# Defaults: the first five participants in $SUBJECTS_FILE and the four cutoffs above.
# Runtime: under an hour for five participants and four cutoffs at the default NTHREADS.
# Expect the high cutoffs to take longest, since they burn the whole 5 million seed
# budget without reaching 1000; 0.01 used about 415,000 seeds in the example dataset.
# What to look for.  A cutoff is a candidate only if Selected reaches 1000 in every
# pilot participant.  Selected below 1000 with Generated at or near the 5 million seed
# limit means the budget ran out.  MeanLen_mm should be similar across cutoffs and sit
# well inside MINLEN and MAXLEN; for a new tract family set the bounds from these means.
# Follow with 04b_compare_cutoffs.py for the side-by-side images and summary table.
# Then put the chosen value in CUTOFF in 00_config.sh; Step 5 reads it from there.
# =============================================================================
# 00_config.sh holds every project-specific value (paths, TRACT, MINLEN, NTHREADS...).
# "source" runs it in this shell so its exports are visible here.  $(...) substitutes a
# command's output; dirname "$0" is the directory this script lives in, so the config is
# found no matter which directory you run from.
source "$(dirname "$0")/00_config.sh"
# Two helpers from 00_config.sh.  start_log copies everything printed below into
# $OUT/logs/04_tune_cutoff.sh.log (via tee) while still showing it on screen, so the
# table survives after the terminal is closed.  read_subjects fills the SUBJECTS array
# with the IDs in $SUBJECTS_FILE.
start_log "$0"
read_subjects

# Arguments, with defaults.  ${1:-default} means "use the first argument if it was given
# and non-empty, otherwise the default".  ${SUBJECTS[*]:0:5} slices the array (offset 0,
# length 5) and joins the five IDs into one space-separated string, the same shape as a
# quoted list passed on the command line.
PILOT=${1:-${SUBJECTS[*]:0:5}}
# Order matters downstream: 04b_compare_cutoffs.py takes the first cutoff as the
# conservative reference for its Dice overlap, so list the highest cutoff first.
CUTOFFS=${2:-"0.1 0.08 0.06 0.01"}
# Reduced budgets so the sweep is cheap; everything else matches the Step 5 production
# run (SELECT=2500, SEEDS=25000000 in 00_config.sh).  1000 streamlines is enough to see
# whether a cutoff reaches the target and what the bundle looks like.  5 million seeds
# is the ceiling on attempts, so a cutoff that cannot get there still stops in bounded
# time; tckgen's own default would be 1000 x select, i.e. 1 million here.
PILOT_SELECT=1000
PILOT_SEEDS=5000000

# Header row of the results table.  printf with %-12s pads each field to a fixed width,
# left-justified, so the rows line up in the log.
printf "%-12s %-8s %-12s %-12s %-12s\n" Subject Cutoff Selected Generated MeanLen_mm
# $PILOT is deliberately unquoted: the shell splits the string on spaces, giving one loop
# iteration per participant ID.
for s in $PILOT; do
  rois="$OUT/$s/rois"
  tdir="$OUT/$s/tckgen/$TRACT"
  # [ ! -f file ] is true when the file does not exist.  The exclusion mask is the last
  # image Step 3 writes, so if it is missing the corridor is not ready; skip this
  # participant ("continue" jumps to the next one) rather than let tckgen fail.
  # The FOD image is not checked here.  If it is missing, tckgen fails, the row comes
  # out with blank counts and NA, and the error message is in the log.
  if [ ! -f "$rois/${TRACT}_exclusion_mask.nii.gz" ]; then
    echo "!! $s missing corridor (run Steps 2 and 3)"
    continue
  fi
  # mkdir -p creates parent directories as needed and is silent if it already exists.
  mkdir -p "$tdir"
  for c in $CUTOFFS; do
    # The cutoff goes in the file name, so the pilot runs sit side by side in the same
    # directory Step 5 will use later but never collide with the production tractogram
    # (<TRACT>_<CUTOFF>.tck).  04b_compare_cutoffs.py looks for exactly this name.
    tck="$tdir/${TRACT}_pilot_${c}.tck"
    # Same tckgen options as Step 5 apart from the budget, the cutoff and -quiet.
    # Comments cannot go between the backslash-continued lines, so they are explained here:
    #   -algorithm iFOD2      probabilistic tracking on the FOD; the tckgen default,
    #                         spelled out so nobody has to guess
    #   -seed_image           start every streamline inside the warped seed region
    #   -seed_unidirectional  track away from the seed in one direction only, not both
    #   -include              keep a streamline only if it reaches the target region
    #   -exclude              discard a streamline the moment it enters this image, which
    #                         is the inverted corridor, i.e. the moment it leaves the
    #                         corridor.  This single exclusion region is what makes a
    #                         0.01 cutoff usable at all.
    #   -select / -seeds      stop at 1000 accepted streamlines or 5 million seeds,
    #                         whichever comes first
    #   -cutoff               the value under test (MRtrix default 0.05)
    #   -minlength/-maxlength length bounds in mm (35 and 65 for VTA -> hippocampus)
    #   -stop                 end the streamline on entering the target instead of
    #                         letting it run on past it
    #   -nthreads             threads for this one command (NTHREADS in 00_config.sh)
    #   -force                overwrite a .tck left by an earlier sweep; there is no
    #                         skip-if-exists here, a rerun simply redoes everything
    #   -quiet                suppress the progress output, so the log holds the table
    #                         and not twenty progress bars
    tckgen "$PROJECT/dwi/$s/wm_fod_norm.mif" "$tck" \
      -algorithm iFOD2 \
      -seed_image "$rois/${TRACT}_seed_diff.nii.gz" -seed_unidirectional \
      -include "$rois/${TRACT}_target_diff.nii.gz" \
      -exclude "$rois/${TRACT}_exclusion_mask.nii.gz" \
      -select "$PILOT_SELECT" -seeds "$PILOT_SEEDS" -cutoff "$c" \
      -minlength "$MINLEN" -maxlength "$MAXLEN" -stop \
      -nthreads "$NTHREADS" -force -quiet
    # tckinfo prints the .tck header as "key: value" lines.  awk keeps the line whose
    # first field ($1) is the key we want and prints the second field, the number.
    # count = streamlines written (selected); total_count = streamlines generated,
    # including the ones rejected by the include, exclude and length rules.
    count=$(tckinfo "$tck" | awk '$1 == "count:" {print $2}')
    generated=$(tckinfo "$tck" | awk '$1 == "total_count:" {print $2}')
    # Mean streamline length in mm.  tckstats -output mean prints just that number, and
    # -quiet keeps progress messages out of the log; awk '{print $1}' takes the first
    # field in case anything trails it.  ${count:-0} substitutes 0 when count is empty
    # (tckinfo failed) so the -gt test does not choke on an empty string.  A run that
    # selected nothing has no lengths to average, hence NA.
    if [ "${count:-0}" -gt 0 ]; then
      meanlen=$(tckstats "$tck" -output mean -quiet | awk '{print $1}')
    else
      meanlen=NA
    fi
    # One table row per participant and cutoff, same widths as the header.
    printf "%-12s %-8s %-12s %-12s %-12s\n" "$s" "$c" "$count" "$generated" "$meanlen"
  done
done
# Reaching 1000 everywhere rules cutoffs out but does not pick one: a permissive cutoff
# can also fill the corridor instead of following the tract.  04b renders the density
# images side by side and reports Dice against the most conservative cutoff; the pick is
# the most permissive value that both reaches the target in everyone and matches that
# picture.  In the example dataset that was 0.01.
echo "Reaching the streamline target in every pilot participant is necessary but not"
echo "sufficient: compare the reconstructions with 04b_compare_cutoffs.py before choosing."
