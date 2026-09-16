#!/bin/bash
# ============================================================
# MesoConnect corridor workflow — shared configuration
# ============================================================
# Source this file at the top of every step script:  source 00_config.sh
# Edit ONLY this file to point the workflow at the project.
# ------------------------------------------------------------
# Project root. Expected layout (per subject):
#   $PROJECT/anat/<subj>/<subj>_T1w_brain.nii.gz        skull-stripped T1
#   $PROJECT/dwi/<subj>/wm_fod_norm.mif                  normalized WM FOD (MRtrix)
#   $PROJECT/dwi/<subj>/nodif_brain_mask.nii.gz          diffusion-space brain mask
#   $PROJECT/dwi/<subj>/fa.nii.gz  (and NODDI maps)      scalar maps to profile
#   $PROJECT/xfm/<subj>/str2diff.mat                     FLIRT T1->diffusion (omit if T1 and DWI share a grid)
export PROJECT="/path/to/project"
export SUBJECTS_FILE="$PROJECT/subjects.txt"          # one subject ID per line
export ATLAS_DIR="/path/to/MesoConnectAtlas"           # downloaded atlas + ROI files (MNI 1mm)
export OUT="$PROJECT/derivatives/mesoconnect"          # everything this workflow writes
export COVARIATES_CSV="$PROJECT/covariates.csv"        # Subject + covariates + outcomes, one row per participant
# raw diffusion inputs, used only by 00b (FOD estimation) and 08a (NODDI fit)
export DWI_NII='$PROJECT/dwi/$s/data.nii.gz'; export BVALS='$PROJECT/dwi/$s/bvals'; export BVECS='$PROJECT/dwi/$s/bvecs'
export FORCE=0               # 1 = recompute outputs that already exist

# --- tract definition (one tract per run; re-source with different values for another tract) ---
export TRACT="l_vta_l_hipp"                                   # output name
export SEED_MNI="$ATLAS_DIR/roi_maps/left_VTA_0.25_bin.nii.gz"      # seed ROI, MNI 1mm, binary
export TARGET_MNI="$ATLAS_DIR/roi_maps/HPC_L_0.5_bin.nii.gz"        # target ROI, MNI 1mm, binary
export ATLAS_MNI="$ATLAS_DIR/tracts_thresholded_binary_50/l_vta_l_hipp_1mm_MNI_GroupMean_thr50.nii.gz"

# --- tractography parameters (see reference/parameters) ---
export DILATE_VOX=2          # corridor dilation in voxels (1-2 typical; 4 if registration is uncertain)
export CUTOFF=0.01           # FOD amplitude cutoff; 0.01 works with the corridor mask (MRtrix default 0.05)
export SELECT=2500           # streamlines to keep
export SEEDS=25000000        # max seeding attempts
export MINLEN=35             # mm
export MAXLEN=65             # mm
export NTHREADS=8

# --- software ---
export MNI_TEMPLATE="$FSLDIR/data/standard/MNI152_T1_1mm_brain.nii.gz"
export ANTSPATH="${ANTSPATH:-/usr/local/ants/bin}"; export PATH="$ANTSPATH:$PATH"
export MAXJOBS=8             # parallel subjects for lightweight steps

# --- logging: every step script calls this once after sourcing the config ---
start_log(){ mkdir -p "$OUT/logs"; exec > >(tee -a "$OUT/logs/$(basename "$1").log") 2>&1; echo "== $(date '+%F %T') $(basename "$1") TRACT=$TRACT =="; }
