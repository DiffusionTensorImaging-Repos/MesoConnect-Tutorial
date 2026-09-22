#!/bin/bash
# =============================================================================
# Step 1. Nonlinear registration of the MNI template to each participant's T1
# =============================================================================
# Fixed image: participant T1 (skull-stripped).  Moving image: MNI152 1 mm brain.
# The forward transforms (mni2t1_0GenericAffine.mat, mni2t1_1Warp.nii.gz) carry
# MNI-space files into T1 space in Step 2; the inverse warp returns
# participant-level results to MNI space.
#
# Why we need this: the atlas, seed and target are drawn in MNI space, but we track
# in each participant's own diffusion space. An affine handles global size, rotation
# and shear, not where one person's midbrain sits, and a few mm of error there puts
# the VTA seed outside the VTA. So we compute a nonlinear warp (ANTs SyN) from MNI to
# the T1 here, and Step 2 chains it with the T1 -> diffusion transform from
# preprocessing. If the T1 already sits on the diffusion grid, this warp is the only
# transform needed (T1_TO_DWI=header in 00_config.sh).
#
# Needs before it runs:
#   00_config.sh edited for this project (PROJECT, OUT, SUBJECTS_FILE, ANTS_*)
#   $PROJECT/anat/<subj>/<subj>_T1w_brain.nii.gz   skull-stripped T1, one per participant
#   $MNI_TEMPLATE, which 00_config.sh points at $FSLDIR/data/standard/MNI152_T1_1mm_brain,
#                  so FSL must be set up in this shell before you run this. ANTSPATH must
#                  point at your ANTs bin directory (00_config.sh assumes /usr/local/ants/bin)
#   Both images must be brain-only. A stripped T1 against a whole-head template (or the
#   reverse) drags the solution toward the skull and biases the warp. If your T1 still
#   has a skull, strip it first (the example dataset used ANTs brain extraction).
#
# Writes, per participant, into $OUT/<subj>/reg/:
#   mni2t1_0GenericAffine.mat   linear part of the MNI -> T1 transform
#   mni2t1_1Warp.nii.gz         nonlinear MNI -> T1 warp; Step 2 applies this + the affine
#   mni2t1_1InverseWarp.nii.gz  T1 -> MNI warp, for taking participant results back to MNI
#   mni2t1_Warped.nii.gz        the template resampled into this participant's T1 space;
#                               nothing downstream reads it, but it is the QC image
# Everything printed also lands in $OUT/logs/01_register_mni_to_t1.sh.log.
#
# Run:   bash 01_register_mni_to_t1.sh        (FORCE=1 bash 01_... redoes everyone)
# Time:  about 10-15 min per participant at 4 threads, 4 participants at a time, so a
#        full sample takes hours. Run it under tmux or a job scheduler. Peak load is
#        about ANTS_THREADS x ANTS_JOBS threads (16 by default); lower both in
#        00_config.sh on a workstation or a shared node.
# Check: the audit table at the end should read "ok" three times per participant (all
#        57 did in the example dataset). Then open mni2t1_Warped.nii.gz over the T1 for
#        each participant: ventricles, corpus callosum and brainstem outline should
#        coincide. A warp that looks fine globally can still be off in the midbrain,
#        which is why Step 2 has you inspect the warped VTA itself as well.
# =============================================================================

# Pull in the paths, parameters and helper functions (start_log, read_subjects,
# throttle, wait_for_jobs, present). "$(...)" runs a command and pastes its output into
# the line; "$(dirname "$0")" is the directory this script lives in, so it finds
# 00_config.sh no matter which directory you call it from.
source "$(dirname "$0")/00_config.sh"
# From here on everything printed goes to the terminal and to the log file.
start_log "$0"
# Fills the SUBJECTS array from $SUBJECTS_FILE (one ID per line).
read_subjects

# Register one participant. Argument: the participant ID. Writes the mni2t1_* files
# into $OUT/<id>/reg/ and prints one status line. It returns early, without stopping
# the script, if the T1 is missing or the work is already done. Several copies run at
# once in the background, so it only ever touches its own participant's directory.
register_one() {
  local s=$1                                    # "local": visible inside this function only
  local t1="$PROJECT/anat/$s/${s}_T1w_brain.nii.gz"
  local d="$OUT/$s/reg"
  # No T1, no registration. "[ ! -f X ]" is true when X is not an existing file. The
  # "!!" prefix flags problems in the log; the audit table will also show MISSING.
  # "return" leaves this function only; the script itself keeps going.
  if [ ! -f "$t1" ]; then
    echo "!! $s missing $t1"
    return
  fi
  # Skip participants who already have a warp, so an interrupted run can be restarted
  # with the same command. "&&" runs the second test only if the first passes; FORCE
  # defaults to 0 in 00_config.sh and "FORCE=1 bash ..." sets it for one run. The warp is
  # the done marker. Unlike Steps 0b and 5, nothing here writes to a temp name and renames
  # on completion, so if you killed a run midway and are not sure what it left behind,
  # delete that participant's reg/ directory or rerun with FORCE=1.
  if [ "$FORCE" != 1 ] && [ -f "$d/mni2t1_1Warp.nii.gz" ]; then
    echo "== $s already registered (FORCE=1 to recompute)"
    return
  fi
  mkdir -p "$d"                                 # -p: make parents too, no error if present
  # antsRegistrationSyNQuick.sh is the ANTs wrapper that runs an affine stage and then a
  # SyN (symmetric diffeomorphic) nonlinear stage, which is why we get both a .mat and a
  # warp. Its registration settings live inside the wrapper; this call only passes the
  # options below. It is what the tutorial was validated with (ANTs 2.3.5). Option by
  # option (trailing "\" continues the command on the next line):
  #   -d 3   image dimension; 3 for a volume
  #   -f     fixed image, the participant's T1: the space everything is moved INTO
  #   -m     moving image, the MNI brain template: the space the atlas files start in
  #   -o     output prefix; ANTs appends 0GenericAffine.mat, 1Warp.nii.gz and so on
  #   -n     threads for this one registration (ANTS_THREADS in 00_config.sh)
  # Fixed and moving are deliberately this way round: the forward transforms take
  # MNI-space images into the T1, which is what Step 2 applies to the seed, target and
  # atlas. Swap them and you get a T1 -> MNI warp that Step 2 cannot use.
  antsRegistrationSyNQuick.sh -d 3 \
    -f "$t1" \
    -m "$MNI_TEMPLATE" \
    -o "$d/mni2t1_" \
    -n "$ANTS_THREADS"
  # This prints even if ANTs failed partway, so trust the audit table, not this line.
  echo ">> $s registered"
}

# Launch the registrations. "${SUBJECTS[@]}" expands the array to one word per ID, and
# the quotes keep an odd ID from splitting. The trailing "&" starts register_one in the
# background and moves straight on; throttle then sleeps until fewer than ANTS_JOBS
# jobs are running, so at most ANTS_JOBS registrations are ever active at once. The log
# is shared, so output from different participants interleaves; the status lines carry
# the ID, and the audit below is the tidy summary.
for s in "${SUBJECTS[@]}"; do
  register_one "$s" &
  throttle "$ANTS_JOBS"
done
# Block until the last background registration finishes before we audit. This is a
# helper rather than a bare "wait" because "wait" would also hang on the tee process
# that start_log opened; 00_config.sh explains.
wait_for_jobs

# Audit
# One row per participant, "ok" or "MISSING" for each of the three transform files.
# present() is the helper from 00_config.sh and "$(present ...)" drops its answer into
# the printf; "\t" makes tab-separated columns that paste cleanly into a spreadsheet.
# Step 2 skips any participant whose affine or warp is MISSING, so fix those first
# (usually a missing T1 or an ANTs crash; the log has the details). The table does not
# check mni2t1_Warped.nii.gz, the QC image; that one you look at by eye. "d" is not
# "local" here because we are back at the top level of the script, not in a function.
printf "\nSubject\tAffine\tWarp\tInverseWarp\n"
for s in "${SUBJECTS[@]}"; do
  d="$OUT/$s/reg"
  printf "%s\t%s\t%s\t%s\n" "$s" \
    "$(present "$d/mni2t1_0GenericAffine.mat")" \
    "$(present "$d/mni2t1_1Warp.nii.gz")" \
    "$(present "$d/mni2t1_1InverseWarp.nii.gz")"
done
