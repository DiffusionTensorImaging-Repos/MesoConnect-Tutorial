---
sidebar_position: 3
title: "Software"
---

# Software

| Software | Needed for |
|---|---|
| FSL | templates, `fslmaths`, `fslstats`, `flirt`; `probtrackx2` if you go the FSL route |
| ANTs | `antsRegistrationSyNQuick.sh`, `antsApplyTransforms` |
| MRtrix3 | `mrconvert`, `dwi2response`, `responsemean`, `dwi2fod`, `mtnormalise`, `tckgen`, `tckinfo`, `tckstats`, `tckmap`, `mrview` |
| Python 3 with DIPY, pyAFQ, nibabel, numpy, pandas, matplotlib | cleaning, profiling, QC, the helper scripts |
| AMICO (`dmri-amico`) | NODDI fitting |
| R | `permutation_one.R` |
| FSLeyes, mrview or ITK-SNAP | looking |
| TractSeg (optional) | fornix and control tracts |

## From a tensor-ready dataset to a FOD

If your preprocessing ended at `dtifit` (the TUBRIC tutorial does), these are the MRtrix steps that produce `wm_fod_norm.mif`. Run per subject, then average the response functions across subjects before `dwi2fod`.

```bash
# 1. convert with gradients embedded
mrconvert data.nii.gz dwi.mif -fslgrad bvecs bvals
mrconvert nodif_brain_mask.nii.gz mask.mif

# 2. tissue response functions (multi-shell)
dwi2response dhollander dwi.mif wm_response.txt gm_response.txt csf_response.txt -mask mask.mif

# 3. group-average response functions (once, across subjects)
responsemean */wm_response.txt group_wm_response.txt
responsemean */gm_response.txt group_gm_response.txt
responsemean */csf_response.txt group_csf_response.txt

# 4. multi-shell multi-tissue CSD
dwi2fod msmt_csd dwi.mif group_wm_response.txt wm_fod.mif \
        group_gm_response.txt gm_fod.mif group_csf_response.txt csf_fod.mif -mask mask.mif

# 5. intensity normalisation
mtnormalise wm_fod.mif wm_fod_norm.mif gm_fod.mif gm_fod_norm.mif csf_fod.mif csf_fod_norm.mif -mask mask.mif
```

Single-shell data can use `dwi2response tournier` and `dwi2fod csd`; the corridor workflow does not care how the FOD was made.

## The FSL route

`probtrackx2` accepts the dilated corridor as a `--waypoints` mask and the exclusions as `--avoid`, with a BEDPOSTX model as input. It produces voxel-wise connectivity, not streamlines, so node-wise profiling is not available from it; use it only if a whole-tract summary is all you need.
