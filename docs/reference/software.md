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
<summary>Script <code>00b_fod_estimation.sh</code> (83 lines)</summary>

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
# =============================================================================
source "$(dirname "$0")/00_config.sh"
start_log "$0"

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
  mrconvert "$d/data.nii.gz" "$d/dwi.mif" -fslgrad "$d/bvecs" "$d/bvals" -force -quiet
  mrconvert "$d/nodif_brain_mask.nii.gz" "$d/mask.mif" -force -quiet
  dwi2response dhollander "$d/dwi.mif" \
    "$d/wm_response.txt" "$d/gm_response.txt" "$d/csf_response.txt" \
    -mask "$d/mask.mif" -force -quiet
  echo ">> $s response functions"
}

estimate_fod() {
  local s=$1
  local d="$PROJECT/dwi/$s"
  local g="$PROJECT/dwi"
  if [ "$FORCE" != 1 ] && [ -f "$d/wm_fod_norm.mif" ]; then
    echo "== $s FOD exists"
    return
  fi
  dwi2fod msmt_csd "$d/dwi.mif" \
    "$g/group_wm_response.txt"  "$d/wm_fod.mif" \
    "$g/group_gm_response.txt"  "$d/gm_fod.mif" \
    "$g/group_csf_response.txt" "$d/csf_fod.mif" \
    -mask "$d/mask.mif" -nthreads "$NTHREADS" -force -quiet
  mtnormalise \
    "$d/wm_fod.mif"  "$d/wm_fod_norm.mif" \
    "$d/gm_fod.mif"  "$d/gm_fod_norm.mif" \
    "$d/csf_fod.mif" "$d/csf_fod_norm.mif" \
    -mask "$d/mask.mif" -force -quiet
  echo ">> $s FOD"
}

# Phase 1
while read -r s; do
  estimate_response "$s" &
  throttle "$MAXJOBS"
done < "$SUBJECTS_FILE"
wait

# Phase 2
for tissue in wm gm csf; do
  responsemean "$PROJECT"/dwi/*/${tissue}_response.txt \
    "$PROJECT/dwi/group_${tissue}_response.txt" -force -quiet
done
echo "== group response functions written"

# Phase 3 (memory-intensive: $FOD_JOBS participants at a time)
while read -r s; do
  estimate_fod "$s" &
  throttle "$FOD_JOBS"
done < "$SUBJECTS_FILE"
wait

# Audit
printf "\nSubject\twm_fod_norm\n"
while read -r s; do
  printf "%s\t%s\n" "$s" "$(present "$PROJECT/dwi/$s/wm_fod_norm.mif")"
done < "$SUBJECTS_FILE"
```

</details>
<!-- /script:00b_fod_estimation.sh -->

## FSL route

`probtrackx2` accepts the dilated corridor as a `--waypoints` mask and the exclusions as `--avoid`, with a BEDPOSTX model as input. Its output is voxel-wise connectivity rather than streamlines, so along-tract profiling is not available from it; it is appropriate when a whole-tract summary is sufficient.
