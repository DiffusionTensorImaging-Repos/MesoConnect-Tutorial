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

When preprocessing ends at the tensor fit, as in the TUBRIC pipeline, the following MRtrix3 commands produce the normalized white-matter FOD image required by the workflow. Response functions are estimated per participant with the unsupervised method of Dhollander et al. (2016), averaged across participants, and used for multi-shell multi-tissue constrained spherical deconvolution (Jeurissen et al., 2014) followed by intensity normalisation (Raffelt et al., 2017).

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
