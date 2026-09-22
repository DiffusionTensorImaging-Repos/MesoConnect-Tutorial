---
sidebar_position: 3
title: "Software"
---

# Software

Table 1 lists the software used in the workflow. The workflow depends on FSL (Jenkinson et al., 2012), ANTs (Avants et al., 2008), MRtrix3 (Tournier et al., 2019) and Python with DIPY (Garyfallidis et al., 2014) and pyAFQ (Kruper et al., 2021); AMICO (Daducci et al., 2015) is required only for neurite orientation dispersion and density imaging (NODDI) fitting and R only for the node-wise permutation test.

**Table 1**

*Software Used in the Workflow*

| Software | Use |
|---|---|
| FSL | Templates; `fslmaths`, `fslstats`, `flirt`; `probtrackx2` for the FSL route |
| ANTs | `antsRegistrationSyNQuick.sh`, `antsApplyTransforms` |
| MRtrix3 | `mrconvert`, `dwi2response`, `responsemean`, `dwi2fod`, `mtnormalise`, `tckgen`, `tckinfo`, `tckstats`, `tckmap`, `mrview` |
| Python 3 with DIPY, pyAFQ, nibabel, numpy, scipy, pandas, statsmodels, matplotlib | Cleaning, profiling, quality control, whole-tract and quartile models |
| AMICO | NODDI fitting |
| R with readr, dplyr, stringr, tibble, foreach, doParallel | `09b_nodewise_permutation.R` |
| FSLeyes, mrview or ITK-SNAP | Inspection |
| TractSeg (Wasserthal et al., 2018; optional) | Fornix and control tracts |

## Fibre orientation distribution estimation

When preprocessing ends at the tensor fit, as in the TUBRIC pipeline, the following MRtrix3 commands produce the normalized white-matter fibre orientation distribution (FOD) image required by the workflow. Response functions are estimated per participant with the unsupervised method of Dhollander et al. (2016), averaged across participants, and used for multi-shell multi-tissue constrained spherical deconvolution (Jeurissen et al., 2014) followed by intensity normalisation (Raffelt et al., 2017). The script `00b_fod_estimation.sh`, shown below, runs these commands across participants.

```bash
# 1. conversion with gradients embedded
mrconvert data.nii.gz dwi.mif -fslgrad bvecs bvals
mrconvert nodif_brain_mask.nii.gz mask.mif

# 2. tissue response functions (multi-shell)
dwi2response dhollander dwi.mif wm_response.txt gm_response.txt csf_response.txt -mask mask.mif

# 3. group-average response functions (once, across participants)
responsemean */wm_response.txt group_wm_response.txt
responsemean */gm_response.txt group_gm_response.txt
responsemean */csf_response.txt group_csf_response.txt

# 4. multi-shell multi-tissue CSD
dwi2fod msmt_csd dwi.mif group_wm_response.txt wm_fod.mif \
        group_gm_response.txt gm_fod.mif group_csf_response.txt csf_fod.mif -mask mask.mif

# 5. intensity normalisation
mtnormalise wm_fod.mif wm_fod_norm.mif gm_fod.mif gm_fod_norm.mif csf_fod.mif csf_fod_norm.mif -mask mask.mif
```

Single-shell data may use `dwi2response tournier` and `dwi2fod csd`. The corridor workflow is independent of how the FOD image was estimated.

<!-- script:00b_fod_estimation.sh -->
<details>
<summary>Script <code>00b_fod_estimation.sh</code> (189 lines)</summary>

```bash title="00b_fod_estimation.sh"
#!/bin/bash
# =============================================================================
# Step 0b. Fibre orientation distributions (multi-shell multi-tissue CSD)
# =============================================================================
# Run once, before Step 5, when preprocessing ended at the tensor.
#   Phase 1 (per participant)  response functions: dwi2response dhollander
#   Phase 2 (group)            average response functions: responsemean
#   Phase 3 (per participant)  dwi2fod msmt_csd, then mtnormalise
# Single-shell data support two tissues only: remove the GM response and GM FOD
# arguments from the dwi2fod and mtnormalise calls.
#
# What this does. Turns each participant's preprocessed diffusion series into the
# normalized white-matter FOD image that tckgen tracks on in Steps 4 and 5. Each
# participant gets their own WM/GM/CSF response functions, those get averaged across
# the sample, and the average is what every participant's deconvolution uses. That is
# the point of the three phases: one shared set of response functions keeps FOD
# amplitudes comparable across people, and Steps 4 and 5 apply one CUTOFF (0.01 in the
# shipped config) to everyone. If your preprocessing already produced wm_fod_norm.mif,
# skip this script entirely.
#
# Needs, per participant, in $PROJECT/dwi/<ID>/:
#   data.nii.gz  bvals  bvecs  nodif_brain_mask.nii.gz
# plus the ID list in $SUBJECTS_FILE and MRtrix3 on the PATH.
#
# Writes, per participant, in $PROJECT/dwi/<ID>/:
#   dwi.mif, mask.mif                          MRtrix copies of the inputs
#   wm_response.txt gm_response.txt csf_response.txt
#   wm_fod.mif gm_fod.mif csf_fod.mif          raw FODs
#   wm_fod_norm.mif gm_fod_norm.mif csf_fod_norm.mif   after mtnormalise
# and at the group level $PROJECT/dwi/group_{wm,gm,csf}_response.txt.
# Only wm_fod_norm.mif is read downstream (04_tune_cutoff.sh, 05_tractography.sh).
# Everything else stays on disk for inspection and reruns. The log goes to
# $OUT/logs/00b_fod_estimation.sh.log.
#
# How to run: edit 00_config.sh, then
#   bash 00b_fod_estimation.sh
#   FORCE=1 bash 00b_fod_estimation.sh      # recompute everything
# Expect hours on a full sample; the three-participant validation run got from here
# through Step 8b in under an hour on four threads. Use tmux or a job scheduler.
# Safe to rerun after an interruption: participants that already finished are skipped.
#
# How to tell it worked: the audit table at the very end should say "ok" on every row,
# and there should be no "!!" lines in $OUT/logs/00b_fod_estimation.sh.log below the
# "==" date line that starts this run (the log appends, so older runs sit above it).
# Then load one or two wm_fod_norm.mif files in mrview (ODF display tool) and check
# that the FOD lobes follow the obvious white-matter bundles.
# =============================================================================
# $0 is this script's path; dirname strips the file name, so the config is found next
# to the script no matter where you run it from. $(...) drops a command's output in.
source "$(dirname "$0")/00_config.sh"
# Both from 00_config.sh: copy everything printed from here on into the log (it appends,
# so earlier runs stay in the file), and load the participant IDs into SUBJECTS.
start_log "$0"
read_subjects

# Phase 1 worker. Converts one participant's data to MRtrix format and estimates the
# three tissue response functions. Argument: participant ID. Writes dwi.mif, mask.mif
# and {wm,gm,csf}_response.txt in $PROJECT/dwi/<ID>/. It runs as a background job
# (see the Phase 1 loop), so a "return" only ends that participant's job.
estimate_response() {
  # "local" keeps these names inside the function instead of leaking into the script's
  # own variables. $1 is the first argument (the ID).
  local s=$1
  local d="$PROJECT/dwi/$s"
  local f
  # Input check. [ ! -f path ] is true when the file is absent. A missing file prints a
  # "!!" line and skips the participant instead of letting mrconvert fail mid-batch.
  for f in data.nii.gz bvals bvecs nodif_brain_mask.nii.gz; do
    if [ ! -f "$d/$f" ]; then
      echo "!! $s missing $d/$f"
      return
    fi
  done
  # Restart guard. wm_response.txt is what this script treats as "done"; skip unless the
  # run was started with FORCE=1 (00_config.sh picks it up from the environment).
  if [ "$FORCE" != 1 ] && [ -f "$d/wm_response.txt" ]; then
    echo "== $s response functions exist"
    return
  fi
  # Convert to MRtrix's .mif format with the gradient table stored in the header.
  # dwi2response and dwi2fod below read it from there, so neither needs -fslgrad.
  #   -fslgrad bvecs bvals  embed the FSL-style table (note the order: bvecs, then bvals)
  #   -force                overwrite an existing output; MRtrix refuses to otherwise
  #   -quiet                no progress bars, which would garble a log shared by 8 jobs
  mrconvert "$d/data.nii.gz" "$d/dwi.mif" -fslgrad "$d/bvecs" "$d/bvals" -force -quiet
  mrconvert "$d/nodif_brain_mask.nii.gz" "$d/mask.mif" -force -quiet
  # Unsupervised WM, GM and CSF response estimation (Dhollander et al., 2016); the three
  # outputs are in that order. -mask keeps the search inside the brain. A trailing
  # backslash continues the command on the next line.
  dwi2response dhollander "$d/dwi.mif" \
    "$d/wm_response.txt" "$d/gm_response.txt" "$d/csf_response.txt" \
    -mask "$d/mask.mif" -force -quiet
  echo ">> $s response functions"
}

# Phase 3 worker. Runs multi-shell multi-tissue CSD (Jeurissen et al., 2014) with the
# group-average response functions, then intensity normalisation. Argument: participant
# ID. Writes {wm,gm,csf}_fod.mif and {wm,gm,csf}_fod_norm.mif in $PROJECT/dwi/<ID>/.
estimate_fod() {
  local s=$1
  local d="$PROJECT/dwi/$s"
  # $g is where Phase 2 put the group_*_response.txt files.
  local g="$PROJECT/dwi"
  # Restart guard, same idea as Phase 1. wm_fod_norm.mif only exists once mtnormalise
  # finished cleanly (see the rename below), so its presence really does mean "done".
  if [ "$FORCE" != 1 ] && [ -f "$d/wm_fod_norm.mif" ]; then
    echo "== $s FOD exists"
    return
  fi
  # msmt_csd takes (response, output) pairs, one per tissue; here WM, GM, CSF. The group
  # files are used, not the participant's own, so every FOD is deconvolved the same way.
  #   -mask      only fit voxels inside the brain mask (faster, nothing fitted to air)
  #   -nthreads  threads for this one command; NTHREADS x FOD_JOBS is the peak load
  dwi2fod msmt_csd "$d/dwi.mif" \
    "$g/group_wm_response.txt"  "$d/wm_fod.mif" \
    "$g/group_gm_response.txt"  "$d/gm_fod.mif" \
    "$g/group_csf_response.txt" "$d/csf_fod.mif" \
    -mask "$d/mask.mif" -nthreads "$NTHREADS" -force -quiet
  # The normalized WM FOD marks a finished participant, so it is written under a
  # temporary name and renamed only when mtnormalise succeeds.
  # mtnormalise (Raffelt et al., 2017) takes (input, output) pairs per tissue and scales
  # them jointly so the tissue sum comes out roughly constant across the brain; that is
  # also its bias-field correction. It puts FOD amplitudes on a common scale across
  # participants, and CUTOFF (Step 4) is an amplitude threshold. "if command; then"
  # branches on the exit status, so the mv below only runs when mtnormalise returned 0.
  if mtnormalise \
    "$d/wm_fod.mif"  "$d/wm_fod_norm.partial.mif" \
    "$d/gm_fod.mif"  "$d/gm_fod_norm.mif" \
    "$d/csf_fod.mif" "$d/csf_fod_norm.mif" \
    -mask "$d/mask.mif" -force -quiet; then
    # Success: rename to the real name. mv -f overwrites without asking.
    mv -f "$d/wm_fod_norm.partial.mif" "$d/wm_fod_norm.mif"
    echo ">> $s FOD"
  else
    # Failure: drop the partial file. wm_fod_norm.mif was never written, so the next run
    # redoes this participant.
    rm -f "$d/wm_fod_norm.partial.mif"
    echo "!! $s FOD estimation failed or was interrupted"
  fi
}

# Phase 1
# "${SUBJECTS[@]}" expands the array from read_subjects to one word per ID. The trailing
# & starts the function as a background job, and throttle (00_config.sh) sleeps until
# fewer than $MAXJOBS jobs are running before the loop starts the next one. MAXJOBS is 8
# in the shipped config; this phase is light enough for that.
for s in "${SUBJECTS[@]}"; do
  estimate_response "$s" &
  throttle "$MAXJOBS"
done
# Block until the last background job finishes. Do not swap in a bare "wait": the
# logging process from start_log never exits, and bash 5.0 to 5.2 would wait on it too.
wait_for_jobs

# Phase 2
# One group-average response function per tissue; responsemean just averages the text
# files it is given. Cheap, so it reruns every time regardless of FORCE.
# The * sits outside the quotes on purpose so the shell expands it; ${tissue} needs the
# braces because $tissue_response would otherwise be read as one variable name.
# Two things worth knowing. The glob picks up every folder under $PROJECT/dwi with a
# response file, not just the IDs in $SUBJECTS_FILE, so an excluded participant still
# contributes unless the folder is moved. And adding participants later and rerunning
# changes this average, but Phase 3 skips everyone who already has wm_fod_norm.mif;
# set FORCE=1 if you want the whole sample deconvolved with the same response functions.
for tissue in wm gm csf; do
  responsemean "$PROJECT"/dwi/*/${tissue}_response.txt \
    "$PROJECT/dwi/group_${tissue}_response.txt" -force -quiet
done
echo "== group response functions written"

# Phase 3 (memory-intensive: $FOD_JOBS participants at a time)
# dwi2fod on a multi-shell series uses a lot of memory, so the concurrency is lower here
# (FOD_JOBS=2 in the shipped config, against MAXJOBS=8 above). Peak load is roughly
# NTHREADS x FOD_JOBS threads; lower one of them if the machine swaps or is shared.
for s in "${SUBJECTS[@]}"; do
  estimate_fod "$s" &
  throttle "$FOD_JOBS"
done
wait_for_jobs

# Audit
# One row per participant, "ok" or "MISSING" for the file Steps 4 and 5 need. present()
# comes from 00_config.sh; $(...) substitutes what it prints into the printf. The header
# says "Subject" because that is the column name the CSVs downstream use. A MISSING
# row here should have a matching "!!" line further up in the log.
printf "\nSubject\twm_fod_norm\n"
for s in "${SUBJECTS[@]}"; do
  printf "%s\t%s\n" "$s" "$(present "$PROJECT/dwi/$s/wm_fod_norm.mif")"
done
```

</details>
<!-- /script:00b_fod_estimation.sh -->

## FSL route

`probtrackx2` accepts the dilated corridor as a `--waypoints` mask and the exclusions as `--avoid`, with a BEDPOSTX model as input. Its output is voxel-wise connectivity rather than streamlines, so along-tract profiling is not available from it; it is appropriate when a whole-tract summary is sufficient.
