---
sidebar_position: 4
title: "Downloads"
---

# Downloads

## Complete atlas

The MesoConnect Atlas is distributed as one package, [MesoConnect_Atlas.zip](pathname:///MesoConnect-Tutorial/downloads/MesoConnect_Atlas.zip) (3.4 MB). The canonical copy and the individual files are in the atlas authors' [GitHub repository](https://github.com/blelliott23/MesoConnect); the copy served here is identical (SHA-256 [checksum file](pathname:///MesoConnect-Tutorial/downloads/MesoConnect_Atlas.zip.sha256)).

The package contains the 28 atlas maps (seven pathways, two hemispheres, two map types), `mesoconnect_subject_counts.csv`, the FSL MNI152 1 mm brain template (Montreal Neurological Institute, MNI) used as the spatial reference, a README and the licence notice:

```
MesoConnect_Atlas/
  README.md   LICENSE   mesoconnect_subject_counts.csv
  templates/MNI152_T1_1mm_brain.nii.gz
  inferior_vta_nac/   superior_vta_nac/   vta_amygdala/   vta_anterior_hpc/
  vta_posterior_hpc/  hpc_nac_vp/         vp_vta/
```

Each pathway folder holds four files named `{hemisphere}_{pathway}_mni152_1mm_{map_type}.nii.gz`, for example `vta_posterior_hpc/left_vta_posterior_hpc_mni152_1mm_thr50.nii.gz`. Table 1 gives the two map types. All maps are on the FSL MNI152 1 mm grid (182 × 218 × 182 voxels, 1 mm isotropic) as compressed NIfTI-1.

**Table 1**

*Map Types in the Atlas Package*

| File suffix | Contents | Use |
|---|---|---|
| `_overlap_prop.nii.gz` | Probabilistic map. Each voxel holds the proportion of contributing participants whose binarized tract included it (0 to 1). | Visualization, custom thresholds, probability-weighted extraction |
| `_thr50.nii.gz` | Binary map. A voxel is 1 when the tract was present in at least half of the contributing participants. | Corridor construction (this tutorial), whole-tract extraction |

*Note.* `mesoconnect_subject_counts.csv` gives the number of contributing participants for every pathway and hemisphere, the denominator of the corresponding overlap-proportion map. Binary maps are warped with nearest-neighbour interpolation. A map at another threshold is made from the overlap-proportion map and kept outside the package folders, for example `fslmaths left_vta_posterior_hpc_mni152_1mm_overlap_prop.nii.gz -thr 0.25 -bin derived/left_vta_posterior_hpc_thr25.nii.gz`.

The package's terms are scoped by material: the Human Connectome Project (HCP)-derived maps and participant counts fall under the WU-Minn HCP Consortium Open Access Data Use Terms, the documentation under CC BY 4.0, and the MNI152 template under the FSL licence; the `LICENSE` file in the package gives the full notice.

## Seed and target regions

The atlas package does not redistribute the third-party regions used as seeds and targets during atlas construction (Harvard–Oxford hippocampus, amygdala and nucleus accumbens; the ventral tegmental area (VTA) of Trutti et al., 2021; the ventral pallidum of Pauli et al., 2018). The atlas authors' [region-of-interest resources page](https://github.com/blelliott23/MesoConnect/blob/main/ROI_RESOURCES.md) gives the download locations, thresholds and citations. The four regions used for the VTA → hippocampus example on this site are provided here (Table 2), thresholded and binarized on the same MNI 1 mm grid.

**Table 2**

*Seed and Target Regions Distributed With This Site*

| File | Hemisphere | Contents |
|---|---|---|
| [left_VTA_0.25_bin.nii.gz](pathname:///MesoConnect-Tutorial/atlas/left_VTA_0.25_bin.nii.gz) | Left | VTA seed (Trutti et al., 2021; 25% threshold) |
| [right_VTA_0.25_bin.nii.gz](pathname:///MesoConnect-Tutorial/atlas/right_VTA_0.25_bin.nii.gz) | Right | VTA seed (Trutti et al., 2021; 25% threshold) |
| [HPC_L_0.5_bin.nii.gz](pathname:///MesoConnect-Tutorial/atlas/HPC_L_0.5_bin.nii.gz) | Left | Hippocampus target (Harvard–Oxford; 50% threshold) |
| [HPC_R_0.5_bin.nii.gz](pathname:///MesoConnect-Tutorial/atlas/HPC_R_0.5_bin.nii.gz) | Right | Hippocampus target (Harvard–Oxford; 50% threshold) |

## Setting up the files for the scripts

The scripts expect the unzipped package as `ATLAS_DIR`, with the seed and target regions in a `roi_maps` folder inside it. The following commands produce that layout for the VTA → hippocampus example.

```bash
curl -sSLO "https://diffusiontensorimaging-repos.github.io/MesoConnect-Tutorial/downloads/MesoConnect_Atlas.zip"
unzip -q MesoConnect_Atlas.zip
mkdir -p MesoConnect_Atlas/roi_maps
base="https://diffusiontensorimaging-repos.github.io/MesoConnect-Tutorial/atlas"
for f in left_VTA_0.25_bin right_VTA_0.25_bin HPC_L_0.5_bin HPC_R_0.5_bin; do
  curl -sSL "$base/$f.nii.gz" -o "MesoConnect_Atlas/roi_maps/$f.nii.gz"
done
```

In `00_config.sh`, `ATLAS_DIR` then points at `MesoConnect_Atlas`, and the atlas map of a tract is named by its package path, for example `$ATLAS_DIR/vta_posterior_hpc/left_vta_posterior_hpc_mni152_1mm_thr50.nii.gz`.

## Source atlases

- Trutti et al. (2021): probabilistic VTA in MNI space; threshold at 25% for a seed region.
- Pauli et al. (2018): subcortical atlas including the ventral pallidum, VTA and substantia nigra.
- Harvard–Oxford subcortical atlas (Frazier et al., 2005; Makris et al., 2006), distributed with FSL: hippocampus, amygdala, accumbens, caudate, putamen, thalamus.
- Murty et al. (2014): functional–anatomical substantia nigra/VTA masks, a comparison resource for the dopaminergic midbrain.
- MNI152 templates (FSL, `$FSLDIR/data/standard`): the 1 mm brain image and brain mask used for registration.
