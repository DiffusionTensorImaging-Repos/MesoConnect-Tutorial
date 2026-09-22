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
<summary>Script <code>02_warp_rois.sh</code> (175 lines)</summary>

```bash title="02_warp_rois.sh"
#!/bin/bash
# =============================================================================
# Step 2. Warp the seed, target and tract atlas into diffusion space
# =============================================================================
# MNI -> T1 with the ANTs transforms from Step 1, then T1 -> diffusion with FLIRT,
# using the matrix or the image header according to T1_TO_DWI in 00_config.sh.
# Nearest-neighbour interpolation throughout; outputs are re-binarized.
#
# Three MNI-space label images go through this for every participant: the seed, the
# target and the atlas's 50% binary map (SEED_MNI, TARGET_MNI and ATLAS_MNI in
# 00_config.sh).  They are 0/1 masks, which is why both resamplings use nearest
# neighbour: linear interpolation would smear the edges into fractions and shift the
# boundary wherever we threshold.  If you ever need the probabilistic atlas in native
# space instead, warp it with linear interpolation and threshold afterwards.
#
# Needs, per participant <subj>:
#   $OUT/<subj>/reg/mni2t1_0GenericAffine.mat     written by Step 1
#   $OUT/<subj>/reg/mni2t1_1Warp.nii.gz           written by Step 1
#   $PROJECT/anat/<subj>/<subj>_T1w_brain.nii.gz  skull-stripped T1 (grid for stage 1)
#   $PROJECT/dwi/<subj>/nodif_brain_mask.nii.gz   diffusion grid the output lands on
#   $PROJECT/xfm/<subj>/str2diff.mat              only when T1_TO_DWI=matrix
# Writes, per participant, into $OUT/<subj>/rois/:
#   ${TRACT}_{seed,target,atlas}_t1.nii.gz        T1-space intermediates (kept for checks)
#   ${TRACT}_{seed,target,atlas}_diff.nii.gz      diffusion space, binary; the real outputs
# Run:   bash 02_warp_rois.sh          (FORCE=1 bash 02_warp_rois.sh redoes everyone)
# Time:  seconds per participant, MAXJOBS participants at a time.
# Check: the audit table at the end of the log ($OUT/logs/02_warp_rois.sh.log).  Every
# row should have non-zero seed, target and atlas counts of similar size across the
# sample, and seed_target_overlap must be 0.  Then look at the _diff images over the
# mean b=0 (the tutorial page shows what good placement looks like).  Step 3 reads the
# three _diff files to build the corridor; Step 5 seeds from seed_diff and includes
# target_diff.
# =============================================================================
# 00_config.sh sits next to this script.  $(...) runs a command and pastes its output in
# place; $0 is the path you invoked the script by and dirname strips the file name off
# it, so this finds the config next to the script file no matter which directory you
# call it from.  "source" runs the file in this same shell, which is what makes its
# exports and helper functions available below.
source "$(dirname "$0")/00_config.sh"
# From here on everything printed also lands in $OUT/logs/02_warp_rois.sh.log.
start_log "$0"
# Fills the SUBJECTS array from $SUBJECTS_FILE (one ID per line).
read_subjects

# Warp one participant.  Argument: the participant ID.  Writes the six files listed in
# the header into $OUT/<subj>/rois/ and prints one status line.  A missing input prints
# a "!!" line and returns, so one broken participant never stops the whole run.
warp_one() {
  # "local" keeps these names inside this call instead of leaking into the rest of the
  # script (the audit loop at the bottom reuses d and s).  Each backgrounded call below
  # is its own process anyway, so this is hygiene, not a fix for a race.
  # $1 is the first argument handed to the function.
  local s=$1
  local d="$OUT/$s/rois"
  local t1="$PROJECT/anat/$s/${s}_T1w_brain.nii.gz"
  local ref="$PROJECT/dwi/$s/nodif_brain_mask.nii.gz"
  local warp="$OUT/$s/reg/mni2t1_1Warp.nii.gz"
  local aff="$OUT/$s/reg/mni2t1_0GenericAffine.mat"
  local mat="$PROJECT/xfm/$s/str2diff.mat"
  local name src in_t1 in_diff

  # Resume logic.  The atlas is the last of the three files written, so if it exists this
  # participant finished on an earlier run and we skip.  FORCE=1 overrides that.
  # [ -f X ] is true when X exists as a regular file; && means both tests must pass.
  if [ "$FORCE" != 1 ] && [ -f "$d/${TRACT}_atlas_diff.nii.gz" ]; then
    echo "== $s already warped"
    return
  fi
  # Step 1 must have produced both transforms, and we need the diffusion mask as the
  # output grid.  "||" chains the tests: any one of them missing is enough to skip.
  if [ ! -f "$warp" ] || [ ! -f "$aff" ] || [ ! -f "$ref" ]; then
    echo "!! $s missing registration outputs or diffusion reference"
    return
  fi
  # The FLIRT matrix is only an input in matrix mode; header mode does not use it.
  if [ "$T1_TO_DWI" = matrix ] && [ ! -f "$mat" ]; then
    echo "!! $s missing $mat"
    return
  fi
  mkdir -p "$d"

  # The same two-stage warp for each of the three images; only the source differs.
  for name in seed target atlas; do
    # case/esac is the shell's switch statement: pick the MNI source for this name.
    case $name in
      seed)   src=$SEED_MNI ;;
      target) src=$TARGET_MNI ;;
      atlas)  src=$ATLAS_MNI ;;
    esac
    in_t1="$d/${TRACT}_${name}_t1.nii.gz"
    in_diff="$d/${TRACT}_${name}_diff.nii.gz"

    # Stage 1, MNI -> T1, with the registration from Step 1.
    #   -d 3               3-D image
    #   -i / -o            input in MNI space, output in T1 space
    #   -r "$t1"           reference: the output takes this image's grid (size, spacing)
    #   -t warp -t aff     the two Step 1 transforms.  ANTs treats -t as a stack and
    #                      applies the last one listed first, so the affine goes on
    #                      before the warp.  That is the order the Step 1 outputs are
    #                      meant to be combined in; do not swap them
    #   -n NearestNeighbor label image: never average 0s and 1s into fractions
    antsApplyTransforms -d 3 -i "$src" -r "$t1" -o "$in_t1" \
      -t "$warp" -t "$aff" -n NearestNeighbor

    # Stage 2, T1 -> diffusion, with FLIRT.  -applyxfm means resample with the given
    # transform and do not estimate a new one.  -ref sets the output grid (the diffusion
    # brain mask), and -interp nearestneighbour is there for the same reason as above.
    if [ "$T1_TO_DWI" = matrix ]; then
      # -init "$mat" is the T1 -> diffusion affine your preprocessing already estimated.
      flirt -in "$in_t1" -ref "$ref" -applyxfm -init "$mat" \
        -interp nearestneighbour -out "$in_diff"
    else
      # T1 and diffusion share a space: resample onto the diffusion grid by header.
      # -usesqform takes the alignment from the two images' sform/qform headers instead
      # of a matrix file, so this branch is only right when they already line up.
      flirt -in "$in_t1" -ref "$ref" -applyxfm -usesqform \
        -interp nearestneighbour -out "$in_diff"
    fi
    # Belt and braces.  Nearest neighbour should already give 0/1, but -thr 0.5 (zero
    # anything below 0.5) then -bin (set what is left to 1) guarantees a clean binary
    # mask.  Step 3 adds and inverts these and Step 5 seeds from them, so 0/1 matters.
    fslmaths "$in_diff" -thr 0.5 -bin "$in_diff"
  done
  echo ">> $s warped"
}

# Say which T1 -> diffusion mode this run uses, and stop now on a typo in 00_config.sh
# rather than after warping everyone the wrong way.  "*)" is the catch-all branch.
case "$T1_TO_DWI" in
  matrix) echo "== T1 -> diffusion: applying xfm/<subj>/str2diff.mat" ;;
  header) echo "== T1 -> diffusion: resampling by image header (no matrix)" ;;
  *)      echo "!! T1_TO_DWI must be matrix or header"; exit 1 ;;
esac

# Run the participants MAXJOBS at a time.  "${SUBJECTS[@]}" expands to every ID as its own
# word.  The trailing "&" sends warp_one to the background so the loop moves straight on;
# throttle (00_config.sh) then blocks whenever MAXJOBS copies are already running.
for s in "${SUBJECTS[@]}"; do
  warp_one "$s" &
  throttle "$MAXJOBS"
done
# Waits for every background warp_one.  Do not swap this for a bare "wait": on some bash
# versions that also waits on the logging process from start_log, which never exits.
wait_for_jobs

# Audit: voxel counts and seed-target overlap (the overlap must be 0)
# One tab-separated row per participant so the table pastes straight into a spreadsheet.
# mktemp -d makes a fresh empty scratch directory for the overlap image; removed at the
# end.
tmp=$(mktemp -d)
printf "\nSubject\tseed_vox\ttarget_vox\tatlas_vox\tseed_target_overlap\n"
for s in "${SUBJECTS[@]}"; do
  d="$OUT/$s/rois"
  # A participant skipped above shows up as MISSING instead of handing fslstats files
  # that do not exist.  "continue" jumps to the next participant.
  if [ ! -f "$d/${TRACT}_atlas_diff.nii.gz" ]; then
    printf "%s\tMISSING\n" "$s"
    continue
  fi
  # seed x target is 1 only where both masks are 1.  Any non-zero count means the two
  # regions touch after warping.  Step 5 seeds inside seed_diff and keeps a streamline
  # only once it reaches target_diff (-include, -stop), so a voxel in both would count
  # as "reached" before the streamline has gone anywhere.
  fslmaths "$d/${TRACT}_seed_diff.nii.gz" -mul "$d/${TRACT}_target_diff.nii.gz" "$tmp/overlap"
  # nvox (00_config.sh) is fslstats -V, first column: the number of non-zero voxels.
  # Read the counts against each other, not against a fixed number.  One far from the
  # rest (more than 2 SD is a good rule) points to a bad Step 1 registration for that
  # participant; look at the _t1 and _diff images before going on.
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
