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

The [Diffusion MRI Preprocessing tutorial](https://diffusiontensorimaging-repos.github.io/Diffusion-MRI-Preprocessing/docs/intro) covers this as its Steps 11 and 12 ([response functions](https://diffusiontensorimaging-repos.github.io/Diffusion-MRI-Preprocessing/docs/pipeline/response-functions), [FOD estimation](https://diffusiontensorimaging-repos.github.io/Diffusion-MRI-Preprocessing/docs/pipeline/fod-estimation)) and is the fuller description. The commands are repeated here for readers whose preprocessing ended at the tensor fit and who arrive without a `wm_fod_norm.mif`.

Response functions are estimated per participant with the unsupervised method of Dhollander et al. (2016), averaged across participants, and used for multi-shell multi-tissue constrained spherical deconvolution (Jeurissen et al., 2014) followed by intensity normalisation (Raffelt et al., 2017). The group average ties the cohort together: adding participants later changes it, so their fibre orientation distributions are comparable with the earlier ones only if every participant is refitted. The script `00b_fod_estimation.sh`, shown below, runs these commands across participants.

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
<summary>Script <code>00b_fod_estimation.sh</code> (96 lines)</summary>

```bash title="00b_fod_estimation.sh"
#!/bin/bash
# =============================================================================
# Step 0b. Fibre orientation distributions (multi-shell multi-tissue CSD)
# =============================================================================
# Estimates per-participant response functions, averages them across the sample and
# deconvolves everyone with that average, so FOD amplitudes and CUTOFF are comparable.
# Inputs:  $PROJECT/dwi/<ID>/{data.nii.gz,bvals,bvecs,nodif_brain_mask.nii.gz}
# Outputs: $PROJECT/dwi/<ID>/{wm,gm,csf}_fod_norm.mif and $PROJECT/dwi/group_*_response.txt
# Run:     bash 00b_fod_estimation.sh   (FORCE=1 redoes everything; hours, use tmux)
# =============================================================================
source "$(dirname "$0")/00_config.sh"
start_log "$0"
read_subjects

# Phase 1 worker: convert one participant to .mif and estimate WM, GM and CSF responses.
estimate_response() {
  local s=$1
  local d="$PROJECT/dwi/$s"
  local f
  for f in data.nii.gz bvals bvecs nodif_brain_mask.nii.gz; do
    if [ ! -f "$d/$f" ]; then
      echo "!! $s missing $d/$f"
      return
    fi
  done
  if [ "$FORCE" != 1 ] && [ -f "$d/wm_response.txt" ]; then
    echo "== $s response functions exist"
    return
  fi
  # -fslgrad bvecs bvals: put the gradient table in the header, so later steps need no -fslgrad.
  mrconvert "$d/data.nii.gz" "$d/dwi.mif" -fslgrad "$d/bvecs" "$d/bvals" -force -quiet
  mrconvert "$d/nodif_brain_mask.nii.gz" "$d/mask.mif" -force -quiet
  # dhollander: unsupervised WM, GM and CSF response estimation.
  dwi2response dhollander "$d/dwi.mif" \
    "$d/wm_response.txt" "$d/gm_response.txt" "$d/csf_response.txt" \
    -mask "$d/mask.mif" -force -quiet
  echo ">> $s response functions"
}

# Phase 3 worker: msmt-CSD with the group-average responses, then mtnormalise.
estimate_fod() {
  local s=$1
  local d="$PROJECT/dwi/$s"
  local g="$PROJECT/dwi"
  if [ "$FORCE" != 1 ] && [ -f "$d/wm_fod_norm.mif" ]; then
    echo "== $s FOD exists"
    return
  fi
  # Group responses, not the participant's own, so every FOD is deconvolved the same way.
  dwi2fod msmt_csd "$d/dwi.mif" \
    "$g/group_wm_response.txt"  "$d/wm_fod.mif" \
    "$g/group_gm_response.txt"  "$d/gm_fod.mif" \
    "$g/group_csf_response.txt" "$d/csf_fod.mif" \
    -mask "$d/mask.mif" -nthreads "$NTHREADS" -force -quiet
  # wm_fod_norm.mif means "done", so write a temp name and rename only if mtnormalise succeeds.
  if mtnormalise \
    "$d/wm_fod.mif"  "$d/wm_fod_norm.partial.mif" \
    "$d/gm_fod.mif"  "$d/gm_fod_norm.mif" \
    "$d/csf_fod.mif" "$d/csf_fod_norm.mif" \
    -mask "$d/mask.mif" -force -quiet; then
    mv -f "$d/wm_fod_norm.partial.mif" "$d/wm_fod_norm.mif"
    echo ">> $s FOD"
  else
    rm -f "$d/wm_fod_norm.partial.mif"
    echo "!! $s FOD estimation failed or was interrupted"
  fi
}

# --- Phase 1: response functions, $MAXJOBS participants at a time ---
for s in "${SUBJECTS[@]}"; do
  estimate_response "$s" &
  throttle "$MAXJOBS"
done
# Not a bare "wait": the start_log logger never exits and bash 5.0-5.2 would wait on it too.
wait_for_jobs

# --- Phase 2: group-average response functions ---
# No FORCE guard (cheap). The glob takes every folder in $PROJECT/dwi, not just $SUBJECTS_FILE.
for tissue in wm gm csf; do
  responsemean "$PROJECT"/dwi/*/${tissue}_response.txt \
    "$PROJECT/dwi/group_${tissue}_response.txt" -force -quiet
done
echo "== group response functions written"

# --- Phase 3: CSD + normalisation, $FOD_JOBS at a time (dwi2fod is memory-heavy) ---
for s in "${SUBJECTS[@]}"; do
  estimate_fod "$s" &
  throttle "$FOD_JOBS"
done
wait_for_jobs

# --- Audit: ok or MISSING for the file Steps 4 and 5 track on ---
printf "\nSubject\twm_fod_norm\n"
for s in "${SUBJECTS[@]}"; do
  printf "%s\t%s\n" "$s" "$(present "$PROJECT/dwi/$s/wm_fod_norm.mif")"
done
```

</details>
<!-- /script:00b_fod_estimation.sh -->

## FSL route

`probtrackx2` accepts the dilated corridor as a `--waypoints` mask and the exclusions as `--avoid`, with a BEDPOSTX model as input. Its output is voxel-wise connectivity rather than streamlines, so along-tract profiling is not available from it; it is appropriate when a whole-tract summary is sufficient.
