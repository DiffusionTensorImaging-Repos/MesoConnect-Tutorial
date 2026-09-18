#!/bin/bash
# =============================================================================
# MesoConnect corridor workflow: shared configuration
# =============================================================================
# Every step script sources this file. Edit this file only; the step scripts
# contain no project-specific values.
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
# =============================================================================

# --- project -----------------------------------------------------------------
export PROJECT="/path/to/project"
export SUBJECTS_FILE="$PROJECT/subjects.txt"     # one participant ID per line
export ATLAS_DIR="/path/to/MesoConnectAtlas"     # atlas and region files, MNI 1 mm
export OUT="$PROJECT/derivatives/mesoconnect"    # everything this workflow writes
export FORCE=0                                   # 1 = recompute existing outputs

# --- tract definition (one tract per run; edit and rerun for another tract) ---
export TRACT="l_vta_l_hipp"                      # name used for all outputs
export SEED_MNI="$ATLAS_DIR/roi_maps/left_VTA_0.25_bin.nii.gz"
export TARGET_MNI="$ATLAS_DIR/roi_maps/HPC_L_0.5_bin.nii.gz"
export ATLAS_MNI="$ATLAS_DIR/tracts_thresholded_binary_50/\
l_vta_l_hipp_1mm_MNI_GroupMean_thr50.nii.gz"

# --- corridor and tractography parameters (see Reference: Parameters) --------
export DILATE_VOX=2          # corridor dilation, voxels (1-2; 4 if registration is uncertain)
export CUTOFF=0.01           # FOD amplitude cutoff selected in Step 4 (MRtrix default 0.05)
export SELECT=2500           # streamlines to retain
export SEEDS=25000000        # maximum seeding attempts
export MINLEN=35             # minimum streamline length, mm
export MAXLEN=65             # maximum streamline length, mm

# --- group-level models (Steps 8b and 9) -------------------------------------
export COVARIATES_CSV="$PROJECT/covariates.csv"  # Subject, covariates, outcomes
# Model covariates: columns of $COVARIATES_CSV, plus Mean_length_mm and
# Streamline_count, which Step 6 computes from the cleaned bundle of this tract.
export COVARIATES="ICV,Mean_length_mm,Streamline_count,absolute_motion,age"
export N_PERMUTATIONS=5000

# --- software and concurrency ------------------------------------------------
export MNI_TEMPLATE="$FSLDIR/data/standard/MNI152_T1_1mm_brain.nii.gz"
export ANTSPATH="${ANTSPATH:-/usr/local/ants/bin}"
export PATH="$ANTSPATH:$PATH"
# Peak load is roughly threads x concurrent participants; lower these on a shared machine.
export NTHREADS=8            # threads per MRtrix command
export MAXJOBS=8             # participants processed concurrently in light steps (2, 3)
export ANTS_THREADS=4        # threads per registration (Step 1)
export ANTS_JOBS=4           # registrations run concurrently (Step 1)
export FOD_JOBS=2            # FOD estimations run concurrently (Step 0b; memory-intensive)

# --- helper functions used by the step scripts -------------------------------

# Append everything the calling script prints to $OUT/logs/<script>.log.
start_log() {
  mkdir -p "$OUT/logs"
  exec > >(tee -a "$OUT/logs/$(basename "$1").log") 2>&1
  echo "== $(date '+%F %T')  $(basename "$1")  TRACT=$TRACT"
}

# Block until fewer than N background jobs are running.  Usage: throttle N
throttle() {
  while [ "$(jobs -r | wc -l)" -ge "$1" ]; do
    sleep 1
  done
}

# Number of non-zero voxels in an image.
nvox() {
  fslstats "$1" -V | awk '{print $1}'
}

# "ok" if the file exists, otherwise "MISSING"; used in the audit tables.
present() {
  if [ -f "$1" ]; then echo ok; else echo MISSING; fi
}
