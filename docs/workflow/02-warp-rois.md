---
sidebar_position: 3
title: "Step 2. Region warping"
---

# Step 2. Warping the seed, target and atlas into diffusion space

Three Montreal Neurological Institute (MNI) space images are transformed for each tract: the seed region, the target region and the atlas's 50% binary map. Each passes through the nonlinear warp from Step 1 and then the linear T1 → diffusion transform. Nearest-neighbour interpolation is used at both stages because the images are labels, and the result is re-binarized.

## Procedure

```bash
# MNI -> T1 (ANTs, nonlinear)
antsApplyTransforms -d 3 -i "$ATLAS_MNI" -r "$T1" -o "$d/${TRACT}_atlas_t1.nii.gz" \
  -t "$OUT/$s/reg/mni2t1_1Warp.nii.gz" -t "$OUT/$s/reg/mni2t1_0GenericAffine.mat" -n NearestNeighbor

# T1 -> diffusion (FLIRT, linear); with T1_TO_DWI=header, -usesqform replaces -init <matrix>
flirt -in "$d/${TRACT}_atlas_t1.nii.gz" -ref "$PROJECT/dwi/$s/nodif_brain_mask.nii.gz" \
  -applyxfm -init "$PROJECT/xfm/$s/str2diff.mat" -out "$d/${TRACT}_atlas_diff.nii.gz" -interp nearestneighbour
fslmaths "$d/${TRACT}_atlas_diff.nii.gz" -thr 0.5 -bin "$d/${TRACT}_atlas_diff.nii.gz"
```

Two successive nearest-neighbour resamplings of a binary mask have negligible effect on its extent. If the probabilistic map is required in native space, it should be warped with linear interpolation and thresholded afterwards. The full script follows; it completes in seconds per participant.

<!-- script:02_warp_rois.sh -->
<details>
<summary>Script <code>02_warp_rois.sh</code> (101 lines)</summary>

```bash title="02_warp_rois.sh"
#!/bin/bash
# =============================================================================
# Step 2. Warp the seed, target and tract atlas into diffusion space
# =============================================================================
# MNI -> T1 with the Step 1 ANTs transforms, then T1 -> diffusion with FLIRT by matrix or
# by image header (T1_TO_DWI in 00_config.sh). Nearest neighbour throughout, re-binarized.
# In:  $OUT/<subj>/reg/mni2t1_*, $PROJECT/{anat,dwi,xfm}/<subj>/ (T1 brain, nodif mask, xfm)
# Out: $OUT/<subj>/rois/${TRACT}_{seed,target,atlas}_{t1,diff}.nii.gz (_t1 kept for checks)
# Run: bash 02_warp_rois.sh   (FORCE=1 bash 02_warp_rois.sh redoes finished participants)
# =============================================================================
source "$(dirname "$0")/00_config.sh"
start_log "$0"
read_subjects

# Warp one participant's seed, target and atlas; a missing input prints "!!" and returns.
warp_one() {
  local s=$1
  local d="$OUT/$s/rois"
  local t1="$PROJECT/anat/$s/${s}_T1w_brain.nii.gz"
  local ref="$PROJECT/dwi/$s/nodif_brain_mask.nii.gz"
  local warp="$OUT/$s/reg/mni2t1_1Warp.nii.gz"
  local aff="$OUT/$s/reg/mni2t1_0GenericAffine.mat"
  local mat="$PROJECT/xfm/$s/str2diff.mat"
  local name src in_t1 in_diff

  # Resume: the atlas is written last, so if it exists this participant already finished.
  if [ "$FORCE" != 1 ] && [ -f "$d/${TRACT}_atlas_diff.nii.gz" ]; then
    echo "== $s already warped"
    return
  fi
  if [ ! -f "$warp" ] || [ ! -f "$aff" ] || [ ! -f "$ref" ]; then
    echo "!! $s missing registration outputs or diffusion reference"
    return
  fi
  if [ "$T1_TO_DWI" = matrix ] && [ ! -f "$mat" ]; then
    echo "!! $s missing $mat"
    return
  fi
  mkdir -p "$d"

  for name in seed target atlas; do
    case $name in
      seed)   src=$SEED_MNI ;;
      target) src=$TARGET_MNI ;;
      atlas)  src=$ATLAS_MNI ;;
    esac
    in_t1="$d/${TRACT}_${name}_t1.nii.gz"
    in_diff="$d/${TRACT}_${name}_diff.nii.gz"

    # MNI -> T1. ANTs applies the -t stack last-listed first: affine, then warp. Do not swap.
    antsApplyTransforms -d 3 -i "$src" -r "$t1" -o "$in_t1" \
      -t "$warp" -t "$aff" -n NearestNeighbor

    # T1 -> diffusion
    if [ "$T1_TO_DWI" = matrix ]; then
      flirt -in "$in_t1" -ref "$ref" -applyxfm -init "$mat" \
        -interp nearestneighbour -out "$in_diff"
    else
      # -usesqform: alignment from the two images' sform/qform headers, no matrix file
      flirt -in "$in_t1" -ref "$ref" -applyxfm -usesqform \
        -interp nearestneighbour -out "$in_diff"
    fi
    # Guarantee a clean 0/1 mask: Step 3 adds and inverts these, Step 5 seeds from them.
    fslmaths "$in_diff" -thr 0.5 -bin "$in_diff"
  done
  echo ">> $s warped"
}

# Catch a bad T1_TO_DWI now rather than after warping everyone the wrong way.
case "$T1_TO_DWI" in
  matrix) echo "== T1 -> diffusion: applying xfm/<subj>/str2diff.mat" ;;
  header) echo "== T1 -> diffusion: resampling by image header (no matrix)" ;;
  *)      echo "!! T1_TO_DWI must be matrix or header"; exit 1 ;;
esac

# --- Warp everyone, MAXJOBS at a time ---
for s in "${SUBJECTS[@]}"; do
  warp_one "$s" &
  throttle "$MAXJOBS"
done
# Not a bare "wait": some bash versions would also wait on the start_log logger (never exits).
wait_for_jobs

# --- Audit: voxel counts and seed-target overlap (overlap must be 0) ---
tmp=$(mktemp -d)
printf "\nSubject\tseed_vox\ttarget_vox\tatlas_vox\tseed_target_overlap\n"
for s in "${SUBJECTS[@]}"; do
  d="$OUT/$s/rois"
  if [ ! -f "$d/${TRACT}_atlas_diff.nii.gz" ]; then
    printf "%s\tMISSING\n" "$s"
    continue
  fi
  # A voxel in both masks would count as "reached" in Step 5 before the streamline has moved.
  fslmaths "$d/${TRACT}_seed_diff.nii.gz" -mul "$d/${TRACT}_target_diff.nii.gz" "$tmp/overlap"
  printf "%s\t%s\t%s\t%s\t%s\n" "$s" \
    "$(nvox "$d/${TRACT}_seed_diff.nii.gz")" \
    "$(nvox "$d/${TRACT}_target_diff.nii.gz")" \
    "$(nvox "$d/${TRACT}_atlas_diff.nii.gz")" \
    "$(nvox "$tmp/overlap")"
done
rm -rf "$tmp"
```

</details>
<!-- /script:02_warp_rois.sh -->

## Verification

The script ends with a per-participant table of the voxel counts of the warped seed, target and atlas and of the seed–target overlap, which must be zero; participants with missing outputs are listed as such. Voxel counts far from the sample mean (more than two standard deviations is a useful criterion) indicate a failed registration and call for inspection of that participant. Table 1 gives the counts obtained in the example dataset. In that dataset image dimensions, binariness and laterality (left-hemisphere regions located in the left hemisphere) were also checked for every participant, and a cross-correlation below .60 between the warped template and the T1 image was flagged; two participants scored .59 and were retained after visual inspection. These additional checks are not part of the distributed script.

**Table 1**

*Voxel Counts of Warped Regions in the Example Dataset (N = 57), VTA → Hippocampus*

| Region | Minimum | *M* | Maximum | *SD* |
|---|---|---|---|---|
| VTA (L / R) | 32 / 34 | 44 / 44 | 56 / 56 | 5.5 / 5.2 |
| Hippocampus (L / R) | 308 / 332 | 395 / 407 | 497 / 493 | 33 / 34 |
| Atlas, 50% (L / R) | 107 / 99 | 126 / 123 | 146 / 149 | 9.9 / 10.6 |

*Note.* VTA = ventral tegmental area; L = left; R = right.

Visual inspection is performed for every participant by overlaying each warped region on the mean *b* = 0 image. Three views are informative: a whole-brain view for gross placement, a magnified view (5×) around the region for voxel-level placement, and an orthogonal render for the record (Figures 1 to 3). The VTA should lie in the ventral midbrain anterior to the red nucleus near the midline and occupy a small number of voxels; placement in the cerebral peduncle, pons or outside the brainstem indicates a failed registration. The hippocampus should follow the medial temporal lobe along the floor of the lateral ventricle; overlap with the ventricle or placement in white matter indicates an error. The atlas should form a narrow corridor from the VTA through the midbrain to the target. A region located in ventricle, white matter or cortex, a region with zero voxels, or a left-hemisphere region on the right returns the participant to Step 1.

**Figure 1**

*Warped Left VTA Seed Region Over the Mean b = 0 Image*

![Whole-brain view of the warped left VTA](/img/fig_vta_wholebrain.png)
![Magnified view of the warped left VTA](/img/fig_vta_magnified.png)

*Note.* Whole-brain view (top) and magnified view (bottom), example dataset.

**Figure 2**

*Warped Left Hippocampus Target and Left VTA → Hippocampus Atlas*

![Magnified view of the warped left hippocampus](/img/fig_hippocampus_magnified.png)
![Magnified view of the warped left atlas](/img/fig_atlas_magnified.png)

*Note.* Hippocampus (top) and atlas at the 50% threshold (bottom), magnified views.

**Figure 3**

*Orthogonal Render of the Warped Regions*

![Orthogonal render with VTA, hippocampus and atlas](/img/fig_regions_ortho.png)

*Note.* VTA in yellow, hippocampus in red, atlas in green.

For the anterior hippocampus tract the same procedure is repeated with the anterior atlas file; the seed and target regions are shared (Figure 4).

**Figure 4**

*Warped Anterior VTA → Hippocampus Atlas in Diffusion Space*

![Warped anterior atlas](/img/fig_anterior_atlas_warped.png)

*Note.* Atlas in red over the mean *b* = 0 image. Left: axial view. Right: coronal view.
