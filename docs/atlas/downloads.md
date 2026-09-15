---
sidebar_position: 3
title: "Downloads"
---

# Downloads

## Files on this site

The VTA → hippocampus files used in the example dataset. All are in FSL MNI152 1 mm space and binary unless marked. Right-click and save, or use the `curl` block below.

| File | Contents |
|---|---|
| [left_VTA_0.25_bin.nii.gz](pathname:///MesoConnect-Tutorial/atlas/left_VTA_0.25_bin.nii.gz) · [right_VTA_0.25_bin.nii.gz](pathname:///MesoConnect-Tutorial/atlas/right_VTA_0.25_bin.nii.gz) | VTA seeds (Trutti, 25%) |
| [HPC_L_0.5_bin.nii.gz](pathname:///MesoConnect-Tutorial/atlas/HPC_L_0.5_bin.nii.gz) · [HPC_R_0.5_bin.nii.gz](pathname:///MesoConnect-Tutorial/atlas/HPC_R_0.5_bin.nii.gz) | Hippocampus targets (Harvard–Oxford, 50%) |
| [l_vta_l_hipp_1mm_MNI_GroupMean_thr50.nii.gz](pathname:///MesoConnect-Tutorial/atlas/l_vta_l_hipp_1mm_MNI_GroupMean_thr50.nii.gz) · [r_…](pathname:///MesoConnect-Tutorial/atlas/r_vta_r_hipp_1mm_MNI_GroupMean_thr50.nii.gz) | Posterior VTA → hippocampus atlas, 50% threshold |
| [l_vta_l_hipp_1mm_MNI_GroupMean_OverlapProp.nii.gz](pathname:///MesoConnect-Tutorial/atlas/l_vta_l_hipp_1mm_MNI_GroupMean_OverlapProp.nii.gz) · [r_…](pathname:///MesoConnect-Tutorial/atlas/r_vta_r_hipp_1mm_MNI_GroupMean_OverlapProp.nii.gz) | Posterior VTA → hippocampus, probabilistic |
| [anterior_l_vta_l_hipp_1mm_MNI_GroupMean_thr50.nii.gz](pathname:///MesoConnect-Tutorial/atlas/anterior_l_vta_l_hipp_1mm_MNI_GroupMean_thr50.nii.gz) · [anterior_r_…](pathname:///MesoConnect-Tutorial/atlas/anterior_r_vta_r_hipp_1mm_MNI_GroupMean_thr50.nii.gz) | Anterior VTA → hippocampus atlas, 50% threshold |

```bash
mkdir -p MesoConnectAtlas && cd MesoConnectAtlas
for f in left_VTA_0.25_bin right_VTA_0.25_bin HPC_L_0.5_bin HPC_R_0.5_bin \
         l_vta_l_hipp_1mm_MNI_GroupMean_thr50 r_vta_r_hipp_1mm_MNI_GroupMean_thr50 \
         l_vta_l_hipp_1mm_MNI_GroupMean_OverlapProp r_vta_r_hipp_1mm_MNI_GroupMean_OverlapProp \
         anterior_l_vta_l_hipp_1mm_MNI_GroupMean_thr50 anterior_r_vta_r_hipp_1mm_MNI_GroupMean_thr50; do
  curl -sSLO "https://diffusiontensorimaging-repos.github.io/MesoConnect-Tutorial/atlas/$f.nii.gz"
done
```

## Full release

The complete package will follow the layout below and will be archived with a versioned DOI. The remaining families (amygdala, accumbens divisions, ventral pallidum, hippocampus → accumbens, hippocampus → ventral pallidum, fornix divisions), the count maps, the 25% and 75% thresholds, the endpoint maps and the exclusion masks are available from the atlas authors until then.

```
MesoConnectAtlas_v1.0/
  Atlases/FSL_MNI152_1mm/
    tracts_probabilistic/            *_GroupMean_OverlapProp.nii.gz
    tracts_thresholded_binary_25/    *_thr25.nii.gz
    tracts_thresholded_binary_50/    *_thr50.nii.gz
    tracts_thresholded_binary_75/    *_thr75.nii.gz
    tracts_overlap_count/            *_GroupOverlapCount.nii.gz
    endpoint_maps/  roi_maps/  exclusion_masks/
  Atlases/HCP_T1_1p05mm/fornix_split_current_space/
  Scripts/   Examples/   Metadata/   Documentation/
```

## Public ROI sources

- **Trutti et al. 7 T VTA atlas**: probabilistic VTA in MNI space; threshold at 25% for a seed.
- **Pauli et al. subcortical atlas**: ventral pallidum; alternative VTA and SN.
- **Harvard–Oxford subcortical atlas** (FSL): hippocampus, amygdala, accumbens, caudate, putamen, thalamus.
- **Tziortzi et al. connectivity-based striatal parcellation**: limbic striatum as an accumbens definition.
- **Murty et al. SN/VTA masks**: functional–anatomical dopaminergic midbrain.
- **TractSeg**: fornix and major white-matter tracts.
- **MNI152 templates** (FSL `$FSLDIR/data/standard`): the 1 mm brain and brain mask used for registration.
