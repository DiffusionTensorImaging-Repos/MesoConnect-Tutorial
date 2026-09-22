#!/bin/bash
# =============================================================================
# Step 3. Build the corridor and its exclusion mask
# =============================================================================
# Dilate the warped atlas, add the seed and target, binarize (inclusion zone),
# then invert.  The inverted image is the single exclusion mask given to tckgen:
# every voxel outside the corridor terminates and discards a streamline.
#
# This is the whole trick of the corridor workflow.  The atlas itself was built
# with a dozen or so separately prepared exclusion regions per tract (listed on
# the atlas Tracts page); here one mask cut from the warped atlas does that job,
# and anything that strays out of it is thrown away.
#
# Needs, per participant, in $OUT/<participant>/rois/ (all written by Step 2):
#   <TRACT>_atlas_diff.nii.gz    50% group atlas, 0/1, on the diffusion grid
#   <TRACT>_seed_diff.nii.gz     seed region, 0/1, diffusion grid
#   <TRACT>_target_diff.nii.gz   target region, 0/1, diffusion grid
# Writes, into the same directory:
#   <TRACT>_atlas_dilated.nii.gz   atlas grown by DILATE_VOX voxels
#   <TRACT>_inclusion_zone.nii.gz  dilated atlas + seed + target, 0/1 (the corridor)
#   <TRACT>_exclusion_mask.nii.gz  the corridor inverted: 1 = forbidden
# Steps 4 and 5 hand <TRACT>_exclusion_mask.nii.gz to tckgen as -exclude.  The
# inclusion zone is only for the audit below and for eyeballing in a viewer (the
# figure on the Step 3 page); no later script reads it.
#
# Run:  bash 03_build_corridor_mask.sh          (after Step 2; FORCE=1 to redo all)
# Light step: a handful of fslmaths calls per participant, each on a small mask,
# so a full sample takes minutes.  Output is copied to
# $OUT/logs/03_build_corridor_mask.sh.log.
#
# What to look at: the audit table at the end.  seed_excluded and target_excluded
# must be 0 for every participant, and corridor_vox should be similar across
# participants (1,526 to 1,934 at 2 mm for the posterior tract in the example
# data; about 1,400 for the anterior).  The corridor is under 1% of the brain by
# design, so a generic coverage check will flag it; ignore that.  Then open one
# inclusion zone over the mean b=0 and check it runs seed to target without
# touching ventricle or cortex (that means too much dilation or a bad
# registration).
# =============================================================================
# $(...) runs a command and pastes its output in place.  $0 is this script's own
# path, so dirname "$0" is the folder it lives in: the config is found next to the
# script no matter where you call it from.  "source" runs the config inside this
# shell, which is how its exports and helper functions (start_log, read_subjects,
# throttle, wait_for_jobs, nvox) become available here.
source "$(dirname "$0")/00_config.sh"
# From here on everything printed also lands in $OUT/logs/03_build_corridor_mask.sh.log
start_log "$0"
# Fills the SUBJECTS array from $SUBJECTS_FILE, one ID per line
read_subjects

# One -dilM pass (3 x 3 x 3 kernel) per voxel of requested dilation
# The script repeats -dilM once per voxel rather than changing the kernel, so
# DILATE_VOX=2 gives " -dilM -dilM".  With that kernel, each pass on a 0/1 image
# turns every zero voxel touching the mask (face, edge or corner) into a 1, so N
# passes grow it by N voxels in every direction.  for ((...)) is bash's C-style
# counting loop.
#
# Why 2: the 50% atlas is already a bit wider than most participants' core, so two
# voxels (4 mm at 2 mm isotropic) is enough slack for registration error.  Use 1 if
# registration is tight and pilot bundles look loose; 4 only as a sensitivity run
# when registration is doubtful.  Too wide and the corridor reaches ventricle or
# cortex; too narrow and tckgen struggles to reach its streamline target.  Report
# whichever value you use.
DILATE_ARGS=""
for ((i = 0; i < DILATE_VOX; i++)); do
  DILATE_ARGS="$DILATE_ARGS -dilM"
done

# build_one <participant ID>
# Builds the three corridor images for one participant under
# $OUT/<participant>/rois/.  Skips a participant whose mask already exists
# (unless FORCE=1) and prints a "!!" line when Step 2's atlas is missing.  Prints
# one line per participant; returns nothing.  It is launched in the background
# below, so it runs in its own copy of the shell: all it can do is write files and
# print, nothing it sets is visible to the main script.
build_one() {
  # "local" scopes a variable to this function call, so these names cannot leak
  # into or collide with the script's globals (the audit loop below also uses d).
  # $1 is the first argument passed to the function.
  local s=$1
  local d="$OUT/$s/rois"
  # [ -f path ] is true when the file exists.  Restart-safe: the exclusion mask is
  # the last file written, so if it is there this participant is done and a re-run
  # only fills in the gaps.  FORCE=1 (exported by 00_config.sh) overrides that.
  # "return" leaves the function right here.
  if [ "$FORCE" != 1 ] && [ -f "$d/${TRACT}_exclusion_mask.nii.gz" ]; then
    echo "== $s corridor exists"
    return
  fi
  # No warped atlas means Step 2 did not finish for this participant.  Say so and
  # move on instead of letting fslmaths die with a less helpful message.
  if [ ! -f "$d/${TRACT}_atlas_diff.nii.gz" ]; then
    echo "!! $s missing warped atlas (run Step 2)"
    return
  fi
  # $DILATE_ARGS is intentionally unquoted so that it expands to separate options
  # (quoted, bash would hand fslmaths " -dilM -dilM" as one unknown option).
  # Output: the atlas grown by DILATE_VOX voxels.
  fslmaths "$d/${TRACT}_atlas_diff.nii.gz" $DILATE_ARGS "$d/${TRACT}_atlas_dilated.nii.gz"
  # Corridor = dilated atlas + seed + target.  -add sums the images voxel by voxel
  # (a voxel in both atlas and seed becomes 2), then -bin sets every non-zero
  # voxel to 1.  The seed and target have to go in here, before the inversion:
  # leave them out and the corridor ends short of them, so tracking stops at the
  # boundary and never reaches the target.
  fslmaths "$d/${TRACT}_atlas_dilated.nii.gz" \
    -add "$d/${TRACT}_seed_diff.nii.gz" \
    -add "$d/${TRACT}_target_diff.nii.gz" \
    -bin "$d/${TRACT}_inclusion_zone.nii.gz"
  # -binv binarizes and inverts: 1 wherever the corridor is 0, and 0 inside it.
  # This is the file tckgen gets as -exclude in Steps 4 and 5; a streamline that
  # enters any 1 voxel is discarded.
  fslmaths "$d/${TRACT}_inclusion_zone.nii.gz" -binv "$d/${TRACT}_exclusion_mask.nii.gz"
  # nvox (00_config.sh) is fslstats -V, the number of non-zero voxels.  A quick
  # sanity number: a corridor of 0 or of half the brain is wrong either way.
  echo ">> $s corridor: $(nvox "$d/${TRACT}_inclusion_zone.nii.gz") voxels"
}

# Participants run in parallel.  "command &" starts build_one in the background
# and moves straight on; throttle (00_config.sh) then sleeps until fewer than
# MAXJOBS background jobs are running, so at most MAXJOBS participants are in
# flight at once.  "${SUBJECTS[@]}" expands the array to one word per ID.
for s in "${SUBJECTS[@]}"; do
  build_one "$s" &
  throttle "$MAXJOBS"
done
# Block until the last background job is done; the audit needs every mask on disk.
# (Not a bare "wait": see the note on wait_for_jobs in 00_config.sh.)
wait_for_jobs

# Audit: no seed or target voxel may fall inside the exclusion mask (both counts 0)
# Multiplying the exclusion mask by the seed leaves a 1 only where a seed voxel is
# forbidden; same for the target.  Anything but 0 means tckgen would discard
# streamlines the moment they start (seed) or arrive (target), so fix that
# participant before Step 4.  The table is tab-separated so it pastes straight
# into a spreadsheet, and it is in the log as well.
# mktemp -d makes a fresh, uniquely named scratch directory (under $TMPDIR or
# /tmp) so the throwaway images here never collide with anything else.
tmp=$(mktemp -d)
# printf with \t writes real tab characters; the leading \n leaves a blank line
# between the per-participant messages above and the table.
printf "\nSubject\tseed_excluded\ttarget_excluded\tcorridor_vox\n"
for s in "${SUBJECTS[@]}"; do
  d="$OUT/$s/rois"
  excl="$d/${TRACT}_exclusion_mask.nii.gz"
  # A participant skipped above (no Step 2 output) gets a MISSING row rather than
  # crashing the audit; "continue" jumps to the next participant.
  if [ ! -f "$excl" ]; then
    printf "%s\tMISSING\n" "$s"
    continue
  fi
  # -mul multiplies voxel by voxel.  The outputs are named without an extension;
  # FSL adds its own (normally .nii.gz) and fslstats, inside nvox, finds them the
  # same way.
  fslmaths "$excl" -mul "$d/${TRACT}_seed_diff.nii.gz" "$tmp/seed"
  fslmaths "$excl" -mul "$d/${TRACT}_target_diff.nii.gz" "$tmp/target"
  # One row: ID, forbidden seed voxels, forbidden target voxels, corridor size.
  # The corridor should be a small fraction of the brain, well under 20%.
  printf "%s\t%s\t%s\t%s\n" "$s" \
    "$(nvox "$tmp/seed")" \
    "$(nvox "$tmp/target")" \
    "$(nvox "$d/${TRACT}_inclusion_zone.nii.gz")"
done
# Throw the scratch directory away; the only thing worth keeping is the table.
rm -rf "$tmp"
