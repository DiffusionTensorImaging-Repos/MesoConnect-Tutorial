#!/bin/bash
# =============================================================================
# MesoConnect corridor workflow: shared configuration
# =============================================================================
# Every step script sources this file. Edit this file only; the step scripts
# contain no project-specific values.
#
# What this file is.  It holds the project paths, the participant list, the tract
# definition, the tractography parameters, the covariate list and the concurrency
# settings, plus six small shell helpers the step scripts share.  Nothing in here
# computes anything; sourcing it takes a fraction of a second.
#
# How to use it.  The shell steps source it themselves.  The Python and R steps only
# see the exported variables, so run "source 00_config.sh" in your shell before calling
# them, and run it AGAIN after every edit: a sourced value stays in the shell until it is
# re-sourced, and the Python steps will happily keep using a stale TRACT or CUTOFF.
# "bash 00_config.sh" runs it in a throwaway shell and sets nothing; the shebang above
# is only there for editors and syntax checkers.
#
# Expected project layout (one directory per participant):
#   $PROJECT/anat/<subj>/<subj>_T1w_brain.nii.gz   skull-stripped T1
#   $PROJECT/dwi/<subj>/data.nii.gz, bvals, bvecs  preprocessed diffusion data
#   $PROJECT/dwi/<subj>/nodif_brain_mask.nii.gz    diffusion-space brain mask
#   $PROJECT/dwi/<subj>/mean_b0.nii.gz             background for QC images (optional)
#   $PROJECT/dwi/<subj>/fa.nii.gz                  tensor FA map
#   $PROJECT/dwi/<subj>/wm_fod_norm.mif            normalized WM FOD (written by 00b)
#   $PROJECT/noddi/<subj>/fit_*.nii.gz             NODDI maps (written by 08a)
#   $PROJECT/xfm/<subj>/str2diff.mat               FLIRT T1 -> diffusion affine
#                                                  (omit if T1 and DWI share a grid)
# Plus two files at the top of $PROJECT: subjects.txt (one ID per line) and
# covariates.csv (a Subject column plus every covariate and outcome you will model).
#
# Everything the workflow writes lands under $OUT (full table on the overview page),
# except the FOD (0b) and NODDI maps (8a), which go beside the raw data as listed above:
#   $OUT/<subj>/reg/            ANTs transforms (Step 1)
#   $OUT/<subj>/rois/           warped seed, target, atlas; corridor; exclusion mask (2, 3)
#   $OUT/<subj>/tckgen/<tract>/ raw and cleaned tractograms (4, 5, 6)
#   $OUT/qc/                    cutoff panels, tckgen summary, overlays, flags (4b, 5, 7)
#   $OUT/nodewise/              tract stats and 100-node profiles (6, 8)
#   $OUT/analysis/              one wide CSV per metric; whole-tract/quartile models (8b, 9a)
#   $OUT/permutation/           node-wise permutation results and the Explorer file (9b, 9c)
#   $OUT/logs/                  one log per shell step, appended on every run
#
# Quick sanity check after editing:
#   source 00_config.sh; echo "$OUT"; wc -l "$SUBJECTS_FILE"
#   ls "$SEED_MNI" "$TARGET_MNI" "$ATLAS_MNI" "$MNI_TEMPLATE"
# If any of those complain, fix the paths here before running Step 1.
# =============================================================================

# --- project -----------------------------------------------------------------
# "export" makes a variable visible to every program this shell starts, which is how the
# Python and R scripts read these values.  A plain VAR=... would stay inside bash.
# PROJECT and ATLAS_DIR are the two paths you set by hand; the rest are built from them.
export PROJECT="/path/to/project"
# The IDs double as directory names under anat/, dwi/, noddi/ and xfm/, and as the
# Subject column in covariates.csv, so they must match exactly (sub-01 and sub01 are two
# different participants as far as the scripts know).  read_subjects() below turns this
# file into the SUBJECTS array; the Python steps read the file themselves, because bash
# cannot export an array.
export SUBJECTS_FILE="$PROJECT/subjects.txt"     # one participant ID per line
# The atlas download (Atlas > Downloads) with its roi_maps/ and
# tracts_thresholded_binary_50/ subfolders.  Everything in it sits on the FSL MNI152
# 1 mm grid, the same space as the template Step 1 registers.
export ATLAS_DIR="/path/to/MesoConnectAtlas"     # atlas and region files, MNI 1 mm
# Keeping outputs out of the raw-data tree means a botched run can be deleted with one
# rm -rf and nothing under $PROJECT/dwi is touched.
export OUT="$PROJECT/derivatives/mesoconnect"    # everything this workflow writes
# ${FORCE:-0} means "use FORCE if it is already set and non-empty, otherwise 0".  So by
# default a participant whose output exists is skipped (a restart after a crash picks up
# where it stopped), and "FORCE=1 bash 05_tractography.sh" redoes everyone without
# editing this file.  Steps 0b, 1, 2, 3, 5, 6, 7 and 8a honour it; Steps 4, 8, 8b and 9
# recompute on every run anyway.
export FORCE="${FORCE:-0}"                        # 1 = recompute existing outputs

# --- tract definition (one tract per run; edit and rerun for another tract) ---
# The workflow does one tract at a time.  Step 1 (registration) is per participant and is
# reused; for a second tract change these four lines, re-source, and rerun Steps 2
# through 9.  Right hemisphere: right_VTA_0.25_bin, HPC_R_0.5_bin, r_vta_r_hipp.
# Anterior division: the anterior_l_vta_l_hipp atlas file with the same seed and target.
#
# TRACT is a label, not a lookup key.  It is spliced into every output name
# (<TRACT>_seed_diff.nii.gz, <TRACT>_<CUTOFF>.tck, <TRACT>__NDI__analysis.csv, ...),
# so pick something without spaces and keep it stable once Step 2 has run.
export TRACT="l_vta_l_hipp"                      # name used for all outputs
# The seed is the left VTA from the 7 T probabilistic atlas of Trutti et al. (2021),
# thresholded at 25% and binarized (the 0.25 in the name); the target is the left
# Harvard-Oxford hippocampus at 50%.  Both are binary masks, so Step 2 warps them with
# nearest-neighbour interpolation and re-binarizes, and its audit table checks that they
# do not overlap.
export SEED_MNI="$ATLAS_DIR/roi_maps/left_VTA_0.25_bin.nii.gz"
export TARGET_MNI="$ATLAS_DIR/roi_maps/HPC_L_0.5_bin.nii.gz"
# The group-mean tract map thresholded at 50% of participants (thr50).  Step 3 dilates
# this into the corridor.  If the warped 50% core comes out short or broken in someone,
# the 25% version of the same tract is the documented fallback (not in the current
# download; the Downloads page says to ask the atlas authors).  The trailing backslash
# only continues the string on the next line; do not put a comment between the two.
export ATLAS_MNI="$ATLAS_DIR/tracts_thresholded_binary_50/\
l_vta_l_hipp_1mm_MNI_GroupMean_thr50.nii.gz"

# --- T1 -> diffusion transform applied in Step 2 --------------------------------
#   matrix  apply $PROJECT/xfm/<subj>/str2diff.mat (a missing matrix is a missing input)
#   header  T1 and diffusion images already share a space: resample by image header only
# Step 2 takes each region MNI -> T1 with the ANTs warp, then T1 -> diffusion with FLIRT.
# "matrix" runs flirt -applyxfm -init str2diff.mat, the affine you made with FLIRT during
# preprocessing.  "header" runs flirt -applyxfm -usesqform, which takes the alignment
# from the image headers instead of a matrix file and only resamples onto the diffusion
# grid; that is the HCP-style case where the T1 was already aligned to the diffusion
# data.  Any other value makes Step 2 stop with an error before touching a participant.
export T1_TO_DWI="matrix"

# --- corridor and tractography parameters (see Reference: Parameters) --------
# How far Step 3 grows the warped atlas before inverting it into the exclusion mask; one
# fslmaths -dilM pass per voxel.  Two voxels at 2 mm isotropic worked for the example
# dataset.  Too little and the corridor clips the participant's own tract, so tracking
# stops at the wall and counts drop; too much and the corridor reaches the ventricle or
# cortex (the Step 3 page's sign of over-dilation).  Report whatever you use.
export DILATE_VOX=2          # corridor dilation, voxels (1-2; 4 if registration is uncertain)
# tckgen -cutoff.  Tracking stops where the FOD amplitude drops below this.  0.01 is far
# below the MRtrix default (0.05) and is only sane because the exclusion mask keeps
# streamlines inside the corridor; unconstrained, a cutoff this low tracks spurious
# streamlines.  Higher values failed to reach the hippocampus in some pilot participants
# and burned many more seeds (Step 4).  The value is also baked into filenames
# (<TRACT>_0.01.tck), so if you change it after Step 5 has run, Steps 6 to 8 will look
# for tractograms that do not exist.
export CUTOFF=0.01           # FOD amplitude cutoff selected in Step 4 (MRtrix default 0.05)
# tckgen -select, the number of accepted streamlines to keep before stopping.  2,500 is
# enough for stable node profiles and endpoint maps.  It is a target, not a measurement:
# a participant who stops short (say 1,800) is kept, and Step 5 lists who fell short.
export SELECT=2500           # streamlines to retain
# tckgen -seeds, the ceiling on seeding attempts before tckgen gives up on reaching
# SELECT.  MRtrix's own default (1,000 x select = 2.5 million) was sometimes not enough,
# so this is ten times that.  The example dataset used 0.5 to 2 million per run (about 4%
# of the ceiling); the smaller anterior corridor needed up to 11 million.  Raising it
# costs nothing when the target is reached early; lowering it makes more participants
# stop short.
export SEEDS=25000000        # maximum seeding attempts
# tckgen -minlength / -maxlength, in mm.  Streamlines outside this window are rejected
# outright.  35 to 65 mm was set for VTA -> hippocampus at 7 T and held at 3 T, where the
# mean lengths came out at 44 to 47 mm.  A different tract family needs its own window;
# read it off the pilot lengths that Step 4 prints rather than guessing.
export MINLEN=35             # minimum streamline length, mm
export MAXLEN=65             # maximum streamline length, mm

# --- group-level models (Steps 8b and 9) -------------------------------------
# One row per participant, a Subject column whose values match subjects.txt, and one
# column per covariate and outcome.  Step 8b joins it to the tract statistics from Step 6
# and the 100-node profiles from Step 8 to make $OUT/analysis/<TRACT>__<METRIC>__
# analysis.csv.  A participant missing from this file drops out of that join; Step 8b
# prints who that was.
export COVARIATES_CSV="$PROJECT/covariates.csv"  # Subject, covariates, outcomes
# Model covariates: columns of $COVARIATES_CSV, plus Mean_length_mm and
# Streamline_count, which Step 6 computes from the cleaned bundle of this tract.
# Comma-separated, no spaces.  Steps 9a and 9b split on the comma and look each name up
# as a column, so a typo fails there ("columns not found"), not here.  The same list is
# used at every resolution (whole tract, quartiles, nodes) so the models are comparable.
# Streamline_count is the one to think about: it correlates strongly with NDI (r = .63
# to .87 in the example dataset), which eats residual variance.  Decide before looking
# at results whether it stays in, and report both specifications.
export COVARIATES="ICV,Mean_length_mm,Streamline_count,absolute_motion,age"
# Freedman-Lane permutations in Step 9b: the reduced-model residuals are shuffled this
# many times, all 100 nodes are refitted each time, and the largest cluster per shuffle
# forms the null for cluster extent.  Cluster p values are proportions of these draws,
# so fewer permutations means coarser p values (the smallest is 1/N) and a noisier
# extent threshold; more means proportionally longer runs (a few minutes per call on one
# core at 5,000).  The R script seeds its RNG, so a rerun with the same N is identical.
export N_PERMUTATIONS=5000

# --- software and concurrency ------------------------------------------------
# Step 1 registers this skull-stripped 1 mm MNI brain (moving) to the participant's
# skull-stripped T1 (fixed); both must be brain-only, since a stripped image against a
# whole-head template biases the registration.  $FSLDIR is set by FSL's own setup
# script, so FSL has to be configured in the shell before this file is sourced; if it
# is not, the path silently becomes /data/standard/... and Step 1 fails.
export MNI_TEMPLATE="$FSLDIR/data/standard/MNI152_T1_1mm_brain.nii.gz"
# Same ${var:-default} trick as FORCE: keep an ANTSPATH the shell already has, otherwise
# assume the usual install location.  Then put it at the front of PATH so
# antsRegistrationSyNQuick.sh and antsApplyTransforms resolve.  ANTSPATH is exported on
# its own as well, not just folded into PATH, since the ANTs shell wrappers can look it
# up directly.
export ANTSPATH="${ANTSPATH:-/usr/local/ants/bin}"
export PATH="$ANTSPATH:$PATH"
# Peak load is roughly threads x concurrent participants; lower these on a shared machine.
# These were tuned for a 48-core node.  Worked out: Step 1 runs ANTS_JOBS x ANTS_THREADS
# = 16 threads, the FOD phase of Step 0b runs FOD_JOBS x NTHREADS = 16, and Step 5 is
# serial so it peaks at NTHREADS = 8.  On a workstation scale them down so that jobs x
# threads stays within the cores you can spare.  Steps 0b, 1 and 5 take hours on a full
# sample whatever you choose; run them under tmux or a scheduler.
#
# Passed as -nthreads to dwi2fod (0b) and tckgen (4, 5).  Step 5 at eight threads took
# about 2 min per participant and hemisphere at 3 T.  NODDI fitting (8a) does not read
# this; it uses NODDI_NTHREADS (default 4).
export NTHREADS=8            # threads per MRtrix command
# How many participants the light steps (warping, corridor building) run at once via
# throttle() below.  Step 0b phase 1 (response functions) uses it too.
export MAXJOBS=8             # participants processed concurrently in light steps (2, 3)
# antsRegistrationSyNQuick.sh -n (threads) and how many registrations run side by side.
# Each registration is roughly 10 to 15 min at four threads.
export ANTS_THREADS=4        # threads per registration (Step 1)
export ANTS_JOBS=4           # registrations run concurrently (Step 1)
# Multi-shell dwi2fod is the memory-hungry step, so this is kept low on purpose; raise
# it only after watching memory use on your machine with a couple of participants.
export FOD_JOBS=2            # FOD estimations run concurrently (Step 0b; memory-intensive)

# --- helper functions used by the step scripts -------------------------------
# A function is "name() { ... }"; inside it, $1 is the first argument.  These exist once
# the file is sourced, so you can call them from an interactive shell too, except
# start_log, which would redirect your terminal.

# Append everything the calling script prints to $OUT/logs/<script>.log.
# Argument: the script path, which every step passes as "$0" (its own name).
# "exec > file" with no command re-points the whole shell's stdout for the rest of the
# run.  ">(tee -a ...)" is process substitution: bash starts tee in the background and
# hands us a path that feeds it; tee -a appends to the log AND echoes to the terminal;
# 2>&1 sends stderr down the same pipe so tool warnings are captured too.  $(...) runs
# a command and pastes its output in place; basename strips the directory, so
# 05_tractography.sh logs to $OUT/logs/05_tractography.sh.log.  Logs accumulate across
# reruns; the "==" line with the date and TRACT marks where each run starts.
start_log() {
  mkdir -p "$OUT/logs"
  exec > >(tee -a "$OUT/logs/$(basename "$1").log") 2>&1
  echo "== $(date '+%F %T')  $(basename "$1")  TRACT=$TRACT"
}

# Participant IDs as the array SUBJECTS.  Tolerates CRLF line endings, blank lines
# and a missing final newline, none of which a "while read" loop handles.
# tr -d '\r' strips the carriage returns a Windows editor leaves behind; the unquoted
# $(...) inside ( ) is then split on whitespace into array elements, which is what makes
# blank lines and a missing newline harmless (and why IDs must not contain spaces).
# The step scripts loop with for s in "${SUBJECTS[@]}" (every element, one word each);
# Step 4 takes the first five as pilots with ${SUBJECTS[*]:0:5}; ${#SUBJECTS[@]} is the
# element count.  Not exported: the Python steps re-read $SUBJECTS_FILE themselves.
read_subjects() {
  SUBJECTS=($(tr -d '\r' < "$SUBJECTS_FILE"))
  echo "== ${#SUBJECTS[@]} participants in $SUBJECTS_FILE"
}

# Block until fewer than N background jobs are running.  Usage: throttle N
# The step scripts launch one participant in the background with "work "$s" &" and call
# throttle right after, so at most N participants run at once.  "jobs -r" lists this
# shell's running background jobs, wc -l counts the lines, and -ge is >= for integers.
# Polling once a second is plenty for jobs that take minutes.
throttle() {
  while [ "$(jobs -r | wc -l)" -ge "$1" ]; do
    sleep 1
  done
}

# Block until every background job has finished.  A bare "wait" must not be used:
# bash 5.0 to 5.2 would also wait for the logging process started by start_log,
# which never exits while the script is running.
# (That is the stall recorded on the Scripts reference page: the shell steps hung at the
# end of their first participant loop.)  throttle 1 waits until zero jobs are running,
# which is the same thing without that problem.  Every parallel step calls this before
# printing its audit table.
wait_for_jobs() {
  throttle 1
}

# Number of non-zero voxels in an image.
# Argument: a NIfTI path.  fslstats -V prints two numbers, the non-zero voxel count and
# the same volume in mm3; awk '{print $1}' keeps the first field.  Steps 2 and 3 use it
# for their audit tables (seed, target and atlas sizes, seed-target overlap, corridor
# size), where a 0 or a count wildly unlike the rest of the sample is the first sign of
# a bad registration.
nvox() {
  fslstats "$1" -V | awk '{print $1}'
}

# "ok" if the file exists, otherwise "MISSING"; used in the audit tables.
# [ -f path ] is true for an existing regular file.  Steps 0b and 1 print one row per
# participant with this, so the end of the log tells you who to rerun.
present() {
  if [ -f "$1" ]; then echo ok; else echo MISSING; fi
}
