#!/bin/bash
# =============================================================================
# Shared configuration for the MesoConnect corridor workflow; every step script sources it.
# Inputs:  $PROJECT/{anat,dwi,noddi,xfm}/<subj>/, subjects.txt, covariates.csv, $ATLAS_DIR
# Outputs: none of its own; every step writes under $OUT
# Run:     source 00_config.sh   (FSL set up first; re-source after every edit)
# =============================================================================

# --- project -----------------------------------------------------------------
export PROJECT="/path/to/project"
export SUBJECTS_FILE="$PROJECT/subjects.txt"     # one participant ID per line
export ATLAS_DIR="/path/to/MesoConnectAtlas"     # atlas and region files, MNI 1 mm
export OUT="$PROJECT/derivatives/mesoconnect"    # everything this workflow writes
export FORCE="${FORCE:-0}"                        # 1 = recompute existing outputs

# --- tract definition (one tract per run; change these four lines and rerun Steps 2-9) ---
export TRACT="l_vta_l_hipp"                      # name used for all outputs
export SEED_MNI="$ATLAS_DIR/roi_maps/left_VTA_0.25_bin.nii.gz"
export TARGET_MNI="$ATLAS_DIR/roi_maps/HPC_L_0.5_bin.nii.gz"
export ATLAS_MNI="$ATLAS_DIR/tracts_thresholded_binary_50/\
l_vta_l_hipp_1mm_MNI_GroupMean_thr50.nii.gz"

# --- T1 -> DWI transform (Step 2): "matrix" = xfm/<subj>/str2diff.mat, "header" = same grid
export T1_TO_DWI="matrix"

# --- corridor and tractography parameters (see Reference: Parameters) --------
export DILATE_VOX=2          # corridor dilation, voxels (1-2; 4 if registration is uncertain)
export CUTOFF=0.01           # FOD amplitude cutoff selected in Step 4 (MRtrix default 0.05)
export SELECT=2500           # streamlines to retain
export SEEDS=25000000        # maximum seeding attempts
export MINLEN=35             # minimum streamline length, mm
export MAXLEN=65             # maximum streamline length, mm

# --- group-level models (Steps 8b and 9) -------------------------------------
export COVARIATES_CSV="$PROJECT/covariates.csv"  # Subject, covariates, outcomes
# Columns of covariates.csv plus Mean_length_mm and Streamline_count (Step 6, cleaned bundle)
export COVARIATES="ICV,Mean_length_mm,Streamline_count,absolute_motion,age"
export N_PERMUTATIONS=5000

# --- software and concurrency (peak load is about jobs x threads; tuned for 48 cores) ---
export MNI_TEMPLATE="$FSLDIR/data/standard/MNI152_T1_1mm_brain.nii.gz"
export ANTSPATH="${ANTSPATH:-/usr/local/ants/bin}"
export PATH="$ANTSPATH:$PATH"
export NTHREADS=8            # threads per MRtrix command
export MAXJOBS=8             # participants processed concurrently in light steps (2, 3)
export ANTS_THREADS=4        # threads per registration (Step 1)
export ANTS_JOBS=4           # registrations run concurrently (Step 1)
export FOD_JOBS=2            # FOD estimations run concurrently (Step 0b; memory-intensive)

# --- helper functions used by the step scripts -------------------------------

start_log() {
  mkdir -p "$OUT/logs"
  exec > >(tee -a "$OUT/logs/$(basename "$1").log") 2>&1
  echo "== $(date '+%F %T')  $(basename "$1")  TRACT=$TRACT"
}

read_subjects() {
  SUBJECTS=($(tr -d '\r' < "$SUBJECTS_FILE"))
  echo "== ${#SUBJECTS[@]} participants in $SUBJECTS_FILE"
}

# Block until fewer than N background jobs are running (usage: throttle N)
throttle() {
  while [ "$(jobs -r | wc -l)" -ge "$1" ]; do
    sleep 1
  done
}

# A bare "wait" hangs on bash 5.0-5.2 (it also waits for the tee started by start_log).
wait_for_jobs() {
  throttle 1
}

nvox() {
  fslstats "$1" -V | awk '{print $1}'
}

present() {
  if [ -f "$1" ]; then echo ok; else echo MISSING; fi
}
