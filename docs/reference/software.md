---
sidebar_position: 3
title: "Software"
---

# Software

**Table 1.** *Software used in the workflow.*

| Software | Use |
|---|---|
| FSL (Jenkinson et al., 2012) | Templates; `fslmaths`, `fslstats`, `flirt`; `probtrackx2` for the FSL route |
| ANTs (Avants et al., 2008) | `antsRegistrationSyNQuick.sh`, `antsApplyTransforms` |
| MRtrix3 (Tournier et al., 2019) | `mrconvert`, `dwi2response`, `responsemean`, `dwi2fod`, `mtnormalise`, `tckgen`, `tckinfo`, `tckstats`, `tckmap`, `mrview` |
| Python 3 with DIPY (Garyfallidis et al., 2014), pyAFQ (Kruper et al., 2021), nibabel, numpy, pandas, matplotlib | Cleaning, profiling, quality control, helper scripts |
| AMICO (Daducci et al., 2015) | NODDI fitting |
| R | `permutation_one.R` |
| FSLeyes, mrview or ITK-SNAP | Inspection |
| TractSeg (Wasserthal et al., 2018; optional) | Fornix and control tracts |

## Fibre orientation distribution estimation

When preprocessing ends at the tensor fit, as in the TUBRIC pipeline, the following MRtrix3 commands produce the normalized white-matter FOD image required by the workflow; the script [`00b_fod_estimation.sh`](pathname:///MesoConnect-Tutorial/scripts/00b_fod_estimation.sh) runs them across participants.

## Script

<!-- script:00b_fod_estimation.sh -->
<details>
<summary><code>00b_fod_estimation.sh</code> (25 lines)</summary>

```bash title="00b_fod_estimation.sh"
#!/bin/bash
# Step 0b — Fibre orientation distributions (run once, before step 5, if preprocessing ended at the tensor).
# Per participant: mrconvert -> dwi2response (dhollander); then group-average responses; then dwi2fod msmt_csd -> mtnormalise.
source "$(dirname "$0")/00_config.sh"; start_log "$0"
phase1(){ s=$1; d="$PROJECT/dwi/$s"; dwi=$(eval echo "$DWI_NII"); bval=$(eval echo "$BVALS"); bvec=$(eval echo "$BVECS")
  [[ -f "$dwi" && -f "$bval" && -f "$bvec" && -f "$d/nodif_brain_mask.nii.gz" ]] || { echo "!! $s missing dwi/bvals/bvecs/mask"; return; }
  [[ "$FORCE" = 1 || ! -f "$d/wm_response.txt" ]] || { echo "== $s responses exist"; return; }
  mrconvert "$dwi" "$d/dwi.mif" -fslgrad "$bvec" "$bval" -force -quiet
  mrconvert "$d/nodif_brain_mask.nii.gz" "$d/mask.mif" -force -quiet
  dwi2response dhollander "$d/dwi.mif" "$d/wm_response.txt" "$d/gm_response.txt" "$d/csf_response.txt" -mask "$d/mask.mif" -force -quiet
  echo ">> $s responses"; }
phase3(){ s=$1; d="$PROJECT/dwi/$s"
  [[ "$FORCE" = 1 || ! -f "$d/wm_fod_norm.mif" ]] || { echo "== $s FOD exists"; return; }
  dwi2fod msmt_csd "$d/dwi.mif" "$PROJECT/dwi/group_wm_response.txt" "$d/wm_fod.mif" \
    "$PROJECT/dwi/group_gm_response.txt" "$d/gm_fod.mif" "$PROJECT/dwi/group_csf_response.txt" "$d/csf_fod.mif" -mask "$d/mask.mif" -nthreads "$NTHREADS" -force -quiet
  mtnormalise "$d/wm_fod.mif" "$d/wm_fod_norm.mif" "$d/gm_fod.mif" "$d/gm_fod_norm.mif" "$d/csf_fod.mif" "$d/csf_fod_norm.mif" -mask "$d/mask.mif" -force -quiet
  echo ">> $s FOD"; }
export -f phase1 phase3
while read -r s; do phase1 "$s" & while [ "$(jobs -r | wc -l)" -ge "$MAXJOBS" ]; do sleep 2; done; done < "$SUBJECTS_FILE"; wait
responsemean "$PROJECT"/dwi/*/wm_response.txt  "$PROJECT/dwi/group_wm_response.txt"  -force -quiet
responsemean "$PROJECT"/dwi/*/gm_response.txt  "$PROJECT/dwi/group_gm_response.txt"  -force -quiet
responsemean "$PROJECT"/dwi/*/csf_response.txt "$PROJECT/dwi/group_csf_response.txt" -force -quiet
echo "== group response functions written"
while read -r s; do phase3 "$s" & while [ "$(jobs -r | wc -l)" -ge 2 ]; do sleep 5; done; done < "$SUBJECTS_FILE"; wait
printf "\nSubject\twm_fod_norm\n"; while read -r s; do printf "%s\t%s\n" "$s" "$( [ -f "$PROJECT/dwi/$s/wm_fod_norm.mif" ] && echo ok || echo MISSING )"; done < "$SUBJECTS_FILE"
```

</details>
<!-- /script:00b_fod_estimation.sh -->
 Response functions are estimated per participant with the unsupervised method of Dhollander et al. (2016), averaged across participants, and used for multi-shell multi-tissue constrained spherical deconvolution (Jeurissen et al., 2014) followed by intensity normalisation (Raffelt et al., 2017).

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

## FSL route

`probtrackx2` accepts the dilated corridor as a `--waypoints` mask and the exclusions as `--avoid`, with a BEDPOSTX model as input. Its output is voxel-wise connectivity rather than streamlines, so along-tract profiling is not available from it; it is appropriate when a whole-tract summary is sufficient.
