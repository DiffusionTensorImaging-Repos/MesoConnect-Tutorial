---
sidebar_position: 5
title: "Step 4. Cutoff selection"
---

# Step 4. Selection of the FOD amplitude cutoff

The fibre orientation distribution (FOD) amplitude cutoff determines the minimum FOD amplitude at which tracking continues. A high cutoff terminates streamlines before they reach the target; a low cutoff, in unconstrained tracking, produces spurious streamlines. The corridor alters this trade-off. With tracking confined to the corridor, a permissive cutoff produces well-formed bundles while consuming far fewer seeds than a conservative cutoff. This behaviour should be verified for each dataset and tract family by a pilot sweep on a small number of participants, followed by tabulation and side-by-side inspection of the reconstructions.

## Cutoff in routine use

The value in routine use with the corridor mask is 0.01, and it is the default in `00_config.sh`. It is the recommended starting value for any tract reconstructed with this workflow; the pilot sweep described below confirms it for a new dataset or tract family and takes under an hour. Table 1 lists the cutoffs that have been used with the atlas.

**Table 1**

*FOD Amplitude Cutoffs in Use*

| Setting | Cutoff | Outcome |
|---|---|---|
| Corridor workflow, 3 T multi-shell data (example dataset): posterior and anterior ventral tegmental area (VTA) → hippocampus | 0.01 | All 228 runs (57 participants, two tracts, two hemispheres) reached 2,500 streamlines; no participant excluded |
| Corridor workflow, VTA → accumbens (other users of the atlas) | 0.01 | Reported to reconstruct the tract |
| Atlas construction, 7 T: VTA → hippocampus and VTA → accumbens | 0.06 | Value used to build the atlas |
| Atlas construction, 7 T: hippocampus → accumbens and hippocampus → ventral pallidum | 0.08 | Value used to build the atlas |
| MRtrix3 default for FOD-based tracking | 0.05 | For reference; not used here |

*Note.* A cutoff of 0.01 is usable only with the corridor's exclusion mask. Without the mask it produces streamlines throughout the brain.

Because lower field strength yields noisier FOD estimates, a cutoff higher than the 7 T values (approximately 0.08) was anticipated for 3 T data. The pilot sweep did not support that expectation: the conservative cutoffs failed to reach the target in several participants, and 0.01 reached it in all of them with about one fifth of the seeds.

## Pilot sweep

The sweep uses five participants, four cutoffs and reduced budgets (`-select 1000`, `-seeds 5000000`); all other parameters match the production run.

```bash
bash 04_tune_cutoff.sh "sub-01 sub-02 sub-03 sub-04 sub-05" "0.1 0.08 0.06 0.01"
```

The script reports streamlines selected, streamlines generated and mean length for each participant and cutoff. `tckgen` generates one streamline per seed, so the number generated is also the number of seeds consumed. Table 2 gives the streamline counts obtained in the example dataset. At 0.1 most runs exhausted the seed budget before reaching the target. At 0.08 some participants reached the target and one stopped at 309. At 0.06 and at 0.01 all runs reached the target; the 0.01 runs consumed approximately one fifth of the seeds (about 415,000 versus 2.1 million or more at 0.06). Reaching the target in every pilot participant is a necessary condition for a cutoff; the reconstructions must also correspond to the tract, which is assessed next.

**Table 2**

*Streamlines Reached by Cutoff in the Pilot Sweep, Posterior VTA → Hippocampus*

| Participant | Hemisphere | 0.1 | 0.08 | 0.06 | 0.01 |
|---|---|---|---|---|---|
| P1 | L | 118 | 556 | 1000 | 1000 |
| P1 | R | 30 | 434 | 1000 | 1000 |
| P2 | L | 274 | 1000 | 1000 | 1000 |
| P2 | R | 165 | 906 | 1000 | 1000 |
| P3 | L | 1000 | 1000 | 1000 | 1000 |
| P3 | R | 1000 | 1000 | 1000 | 1000 |
| P4 | L | 88 | 309 | 1000 | 1000 |
| P4 | R | 731 | 1000 | 1000 | 1000 |

*Note.* Target 1,000 streamlines; seed limit 5 million. P1 to P4 = pilot participants with all four cutoffs completed; the fifth pilot participant was run at 0.06 and 0.01 only and reached the target at both. L = left; R = right.

## Side-by-side comparison

For each participant, the tract-density image (TDI) at each cutoff is rendered on the same axial and coronal slices, one column per cutoff. Dice overlap of each cutoff against the most conservative one, the number of TDI voxels, and the mean and standard deviation of streamline length are computed and summarized.

```bash
python 04b_compare_cutoffs.py "sub-01 sub-02 sub-03 sub-04 sub-05" "0.1 0.08 0.06 0.01"
```

The script writes one panel per participant, `cutoff_summary.csv`, and a summary chart (Figures 1 and 2). In the example dataset the two cutoffs traced the same trajectory in both views. The 0.01 reconstruction was somewhat thicker (mean Dice = .66 against 0.06), mean lengths were similar (approximately 44 versus 47 mm), and the length standard deviation was slightly greater at 0.01 (7 versus 6 mm). Bundle cleaning (Step 6) removes the outlying streamlines responsible for the additional thickness; the cleaned 0.01 bundle is more compact than the uncleaned 0.06 bundle, as shown on that page.

**Figure 1**

*Tract-Density Images at Two Cutoffs, Uncleaned*

![Tract-density images at cutoff 0.06 and 0.01](/img/fig_cutoff_comparison.png)

*Note.* Cutoff 0.06 (left) and 0.01 (right) for one participant, left posterior VTA → hippocampus.

**Figure 2**

*Summary Statistics by Cutoff Across the Pilot Participants*

![Summary statistics by cutoff](/img/fig_cutoff_summary.png)

*Note.* Bars are grouped by pilot participant and hemisphere. Left: mean streamline length. Middle: Dice overlap between cutoffs. Right: standard deviation of streamline length.

## Selection criterion

The cutoff selected is the most permissive value that reaches the streamline target in every pilot participant and whose reconstruction matches the conservative reconstruction. In the example dataset this was 0.01, the value in routine use (Table 1). A higher value is warranted only when the 0.01 reconstruction departs from the conservative reconstruction in the side-by-side images, for example by filling the corridor rather than following the tract; the next value in Table 1 (0.06) is then tried. The sweep should be repeated for each tract family, since a cutoff confirmed for VTA → hippocampus is a starting value for other pathways.

## Options not used

Anatomically constrained tractography (ACT) was evaluated during atlas construction and abandoned because the tissue segmentation's white-matter mask was too restrictive relative to the gray-matter mask and tracts did not reconstruct. The `-backtrack` and `-crop_at_gmwmi` options and custom `-angle` and `-step_size` values were left at MRtrix3 defaults. These options should be introduced only in response to a specific, observed failure.

## Scripts

<!-- script:04_tune_cutoff.sh -->
<details>
<summary>Script <code>04_tune_cutoff.sh</code> (147 lines)</summary>

```bash title="04_tune_cutoff.sh"
#!/bin/bash
# =============================================================================
# Step 4. Pilot sweep of the FOD amplitude cutoff
# =============================================================================
# Runs reduced-budget tractography at several cutoffs in a few participants.
# "Selected" is the number of streamlines that met every criterion; "Generated" is
# the number tckgen had to generate (selected plus rejected) to obtain them.  tckgen
# generates one streamline per seed, so it is also the number of seeds consumed.
#
# Why this exists.  The cutoff is the minimum FOD amplitude at which tckgen keeps
# tracking.  Too high and streamlines die before the target; too low and, without a
# corridor, they wander all over the brain.  Inside the corridor a very low cutoff
# (0.01, the default in 00_config.sh) reached the target in every pilot participant of
# the example dataset with about a fifth of the seeds 0.06 needed, and later in all 57
# at the production budget.  That has to be checked again on each new dataset or tract
# family, which is what this sweep is for.
#
# Needs, per pilot participant (Steps 0b, 2 and 3 must have run for them):
#   $PROJECT/dwi/<s>/wm_fod_norm.mif               normalized WM FOD (Step 0b)
#   $OUT/<s>/rois/<TRACT>_seed_diff.nii.gz         seed region in diffusion space (Step 2)
#   $OUT/<s>/rois/<TRACT>_target_diff.nii.gz       target region in diffusion space (Step 2)
#   $OUT/<s>/rois/<TRACT>_exclusion_mask.nii.gz    inverted corridor (Step 3)
# Writes:
#   $OUT/<s>/tckgen/<TRACT>/<TRACT>_pilot_<cutoff>.tck   one tractogram per cutoff
#   $OUT/logs/04_tune_cutoff.sh.log                       the table below, kept on disk
# Usage:
#   bash 04_tune_cutoff.sh "sub-01 sub-02 sub-03 sub-04 sub-05" "0.1 0.08 0.06 0.01"
# Defaults: the first five participants in $SUBJECTS_FILE and the four cutoffs above.
# Runtime: under an hour for five participants and four cutoffs at the default NTHREADS.
# Expect the high cutoffs to take longest, since they burn the whole 5 million seed
# budget without reaching 1000; 0.01 used about 415,000 seeds in the example dataset.
# What to look for.  A cutoff is a candidate only if Selected reaches 1000 in every
# pilot participant.  Selected below 1000 with Generated at or near the 5 million seed
# limit means the budget ran out.  MeanLen_mm should be similar across cutoffs and sit
# well inside MINLEN and MAXLEN; for a new tract family set the bounds from these means.
# Follow with 04b_compare_cutoffs.py for the side-by-side images and summary table.
# Then put the chosen value in CUTOFF in 00_config.sh; Step 5 reads it from there.
# =============================================================================
# 00_config.sh holds every project-specific value (paths, TRACT, MINLEN, NTHREADS...).
# "source" runs it in this shell so its exports are visible here.  $(...) substitutes a
# command's output; dirname "$0" is the directory this script lives in, so the config is
# found no matter which directory you run from.
source "$(dirname "$0")/00_config.sh"
# Two helpers from 00_config.sh.  start_log copies everything printed below into
# $OUT/logs/04_tune_cutoff.sh.log (via tee) while still showing it on screen, so the
# table survives after the terminal is closed.  read_subjects fills the SUBJECTS array
# with the IDs in $SUBJECTS_FILE.
start_log "$0"
read_subjects

# Arguments, with defaults.  ${1:-default} means "use the first argument if it was given
# and non-empty, otherwise the default".  ${SUBJECTS[*]:0:5} slices the array (offset 0,
# length 5) and joins the five IDs into one space-separated string, the same shape as a
# quoted list passed on the command line.
PILOT=${1:-${SUBJECTS[*]:0:5}}
# Order matters downstream: 04b_compare_cutoffs.py takes the first cutoff as the
# conservative reference for its Dice overlap, so list the highest cutoff first.
CUTOFFS=${2:-"0.1 0.08 0.06 0.01"}
# Reduced budgets so the sweep is cheap; everything else matches the Step 5 production
# run (SELECT=2500, SEEDS=25000000 in 00_config.sh).  1000 streamlines is enough to see
# whether a cutoff reaches the target and what the bundle looks like.  5 million seeds
# is the ceiling on attempts, so a cutoff that cannot get there still stops in bounded
# time; tckgen's own default would be 1000 x select, i.e. 1 million here.
PILOT_SELECT=1000
PILOT_SEEDS=5000000

# Header row of the results table.  printf with %-12s pads each field to a fixed width,
# left-justified, so the rows line up in the log.
printf "%-12s %-8s %-12s %-12s %-12s\n" Subject Cutoff Selected Generated MeanLen_mm
# $PILOT is deliberately unquoted: the shell splits the string on spaces, giving one loop
# iteration per participant ID.
for s in $PILOT; do
  rois="$OUT/$s/rois"
  tdir="$OUT/$s/tckgen/$TRACT"
  # [ ! -f file ] is true when the file does not exist.  The exclusion mask is the last
  # image Step 3 writes, so if it is missing the corridor is not ready; skip this
  # participant ("continue" jumps to the next one) rather than let tckgen fail.
  # The FOD image is not checked here.  If it is missing, tckgen fails, the row comes
  # out with blank counts and NA, and the error message is in the log.
  if [ ! -f "$rois/${TRACT}_exclusion_mask.nii.gz" ]; then
    echo "!! $s missing corridor (run Steps 2 and 3)"
    continue
  fi
  # mkdir -p creates parent directories as needed and is silent if it already exists.
  mkdir -p "$tdir"
  for c in $CUTOFFS; do
    # The cutoff goes in the file name, so the pilot runs sit side by side in the same
    # directory Step 5 will use later but never collide with the production tractogram
    # (<TRACT>_<CUTOFF>.tck).  04b_compare_cutoffs.py looks for exactly this name.
    tck="$tdir/${TRACT}_pilot_${c}.tck"
    # Same tckgen options as Step 5 apart from the budget, the cutoff and -quiet.
    # Comments cannot go between the backslash-continued lines, so they are explained here:
    #   -algorithm iFOD2      probabilistic tracking on the FOD; the tckgen default,
    #                         spelled out so nobody has to guess
    #   -seed_image           start every streamline inside the warped seed region
    #   -seed_unidirectional  track away from the seed in one direction only, not both
    #   -include              keep a streamline only if it reaches the target region
    #   -exclude              discard a streamline the moment it enters this image, which
    #                         is the inverted corridor, i.e. the moment it leaves the
    #                         corridor.  This single exclusion region is what makes a
    #                         0.01 cutoff usable at all.
    #   -select / -seeds      stop at 1000 accepted streamlines or 5 million seeds,
    #                         whichever comes first
    #   -cutoff               the value under test (MRtrix default 0.05)
    #   -minlength/-maxlength length bounds in mm (35 and 65 for VTA -> hippocampus)
    #   -stop                 end the streamline on entering the target instead of
    #                         letting it run on past it
    #   -nthreads             threads for this one command (NTHREADS in 00_config.sh)
    #   -force                overwrite a .tck left by an earlier sweep; there is no
    #                         skip-if-exists here, a rerun simply redoes everything
    #   -quiet                suppress the progress output, so the log holds the table
    #                         and not twenty progress bars
    tckgen "$PROJECT/dwi/$s/wm_fod_norm.mif" "$tck" \
      -algorithm iFOD2 \
      -seed_image "$rois/${TRACT}_seed_diff.nii.gz" -seed_unidirectional \
      -include "$rois/${TRACT}_target_diff.nii.gz" \
      -exclude "$rois/${TRACT}_exclusion_mask.nii.gz" \
      -select "$PILOT_SELECT" -seeds "$PILOT_SEEDS" -cutoff "$c" \
      -minlength "$MINLEN" -maxlength "$MAXLEN" -stop \
      -nthreads "$NTHREADS" -force -quiet
    # tckinfo prints the .tck header as "key: value" lines.  awk keeps the line whose
    # first field ($1) is the key we want and prints the second field, the number.
    # count = streamlines written (selected); total_count = streamlines generated,
    # including the ones rejected by the include, exclude and length rules.
    count=$(tckinfo "$tck" | awk '$1 == "count:" {print $2}')
    generated=$(tckinfo "$tck" | awk '$1 == "total_count:" {print $2}')
    # Mean streamline length in mm.  tckstats -output mean prints just that number, and
    # -quiet keeps progress messages out of the log; awk '{print $1}' takes the first
    # field in case anything trails it.  ${count:-0} substitutes 0 when count is empty
    # (tckinfo failed) so the -gt test does not choke on an empty string.  A run that
    # selected nothing has no lengths to average, hence NA.
    if [ "${count:-0}" -gt 0 ]; then
      meanlen=$(tckstats "$tck" -output mean -quiet | awk '{print $1}')
    else
      meanlen=NA
    fi
    # One table row per participant and cutoff, same widths as the header.
    printf "%-12s %-8s %-12s %-12s %-12s\n" "$s" "$c" "$count" "$generated" "$meanlen"
  done
done
# Reaching 1000 everywhere rules cutoffs out but does not pick one: a permissive cutoff
# can also fill the corridor instead of following the tract.  04b renders the density
# images side by side and reports Dice against the most conservative cutoff; the pick is
# the most permissive value that both reaches the target in everyone and matches that
# picture.  In the example dataset that was 0.01.
echo "Reaching the streamline target in every pilot participant is necessary but not"
echo "sufficient: compare the reconstructions with 04b_compare_cutoffs.py before choosing."
```

</details>
<!-- /script:04_tune_cutoff.sh -->

<!-- script:04b_compare_cutoffs.py -->
<details>
<summary>Script <code>04b_compare_cutoffs.py</code> (262 lines)</summary>

```python title="04b_compare_cutoffs.py"
#!/usr/bin/env python3
"""Step 4b. Comparison of the pilot cutoffs.

Companion to 04_tune_cutoff.sh.  That script ran reduced-budget tckgen at several FOD
amplitude cutoffs in a few pilot participants; this one turns those tractograms into
images and a table, so the cutoff for the production run (CUTOFF in 00_config.sh, read
by 05_tractography.sh) is chosen by looking at the reconstructions and not by streamline
counts alone.  Reaching the target at a cutoff is necessary but not sufficient: the
permissive reconstruction also has to follow the same path as the conservative one.

Run in a shell where 00_config.sh has been sourced.  The script reads PROJECT, OUT, TRACT
and SUBJECTS_FILE from the environment; it does not source the file itself:

    source 00_config.sh
    python 04b_compare_cutoffs.py "sub-01 sub-02 sub-03" "0.1 0.08 0.06 0.01"

Both arguments are optional and take the same form as for 04_tune_cutoff.sh: one quoted,
space-separated list of participant IDs (default: the first five in $SUBJECTS_FILE) and
one quoted list of cutoffs (default: the four above).  Put the most conservative (highest)
cutoff first; it is the reference that the Dice overlap is measured against.

Needs, per pilot participant and cutoff:
    $OUT/<subj>/tckgen/<TRACT>/<TRACT>_pilot_<cutoff>.tck   written by 04_tune_cutoff.sh
    $PROJECT/dwi/<subj>/nodif_brain_mask.nii.gz             grid for the density images
    $PROJECT/dwi/<subj>/mean_b0.nii.gz                      image background (optional)
and tckinfo, tckstats and tckmap (MRtrix3) on the PATH.

Writes, all under $OUT/qc/<TRACT>_cutoff_pilot/:
    <subj>_cutoff_compare.png   one column per cutoff; axial row above, coronal row below
    cutoff_summary.csv          one row per participant and cutoff: streamlines selected,
                                streamlines generated, occupied voxels, Dice overlap with
                                the reference cutoff, mean and SD of streamline length
    cutoff_summary.png          selected, generated, voxels and SD of length averaged
                                over participants, one bar per cutoff (Dice and mean
                                length are in the CSV only)

Runs in minutes, not hours: each tractogram gets one tckinfo, two tckstats and one tckmap
call on at most 1000 streamlines, plus one small figure per participant (not timed; the
page only times the whole sweep).  Nothing downstream reads these files.  Look first:
keep the most permissive cutoff that reached the target in every participant and whose
tract-density image still traces the conservative one instead of filling the corridor.
Then check the CSV: Dice near 1 means the same voxels, and a jump in "voxels" or in
"sd_len_mm" at a permissive cutoff means stray streamlines.  Step 6 cleaning removes those
outliers; in the example data the cleaned 0.01 bundle came out more compact than the
uncleaned 0.06 one.  Put the value you choose in 00_config.sh as CUTOFF before Step 5.
"""
import os
import subprocess
import sys
from pathlib import Path

# Select the file-only backend before pyplot is imported.  This usually runs on a cluster
# node with no display, where the default interactive backend fails.
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import nibabel as nib
import numpy as np
import pandas as pd


# Read one variable exported by 00_config.sh and give a clear message when the reader
# forgot to source it.  sys.exit() with a string prints it to stderr and exits with 1.
def env(name):
    if name not in os.environ:
        sys.exit(f"{name} is not set: run `source 00_config.sh` first")
    return os.environ[name]


# Same PROJECT, OUT and TRACT as the shell scripts, so this finds what 04_tune_cutoff.sh wrote.
PROJECT = Path(env("PROJECT"))
OUT = Path(env("OUT"))
TRACT = env("TRACT")

# Participants come in as one string ("sub-01 sub-02") that we split on whitespace, so the
# call looks like the call to 04_tune_cutoff.sh.  With no argument, take the first five
# IDs in $SUBJECTS_FILE, which is that script's default too.
if len(sys.argv) > 1:
    PILOT = sys.argv[1].split()
else:
    PILOT = Path(env("SUBJECTS_FILE")).read_text().split()[:5]
# Cutoffs stay as strings on purpose.  They only build file names and label plots, and
# "0.1" has to match the name 04_tune_cutoff.sh used exactly; "0.10" through float() would
# come back as "0.1" and miss the file.
CUTOFFS = sys.argv[2].split() if len(sys.argv) > 2 else ["0.1", "0.08", "0.06", "0.01"]
# The first cutoff given is assumed to be the most conservative (highest).  Every other
# cutoff's density mask is compared with it by Dice.  Nothing checks the order: list 0.01
# first and the Dice column is measured against 0.01 instead.
REFERENCE = CUTOFFS[0]          # most conservative cutoff: reference for Dice overlap

# One QC folder per tract.  parents/exist_ok give it "mkdir -p" behaviour.
QC = OUT / "qc" / f"{TRACT}_cutoff_pilot"
QC.mkdir(parents=True, exist_ok=True)


# Run a command given as a list of arguments and hand back its stdout as text.
# check=True raises CalledProcessError on a non-zero exit, so a damaged .tck stops the
# script instead of quietly becoming a zero in the table.
def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout


# Count and length statistics for one tractogram.  Argument: path to a .tck file.
# Returns (selected, generated, mean length in mm, SD of length in mm).  The two lengths
# are NaN when the file holds no streamlines, since tckstats has nothing to summarise.
def tck_summary(tck):
    """Streamlines selected, streamlines generated (selected plus rejected), and the
    mean and SD of length (mm)."""
    # tckinfo prints the .tck header as "key: value" lines.  Collect them in a dict.
    # partition() splits at the first colon only, so a value with a colon in it survives.
    info = {}
    for line in run(["tckinfo", str(tck)]).splitlines():
        key, _, value = line.strip().partition(":")
        info[key] = value.strip()
    # "count" is what tckgen kept (passed -include, -exclude and the length limits);
    # "total_count" is everything it generated to get there.  tckgen makes one streamline
    # per seed, so total_count is also the number of seeds spent.  A missing key reads 0.
    count = int(info.get("count", 0))
    generated = int(info.get("total_count", 0))
    if count == 0:
        return count, generated, np.nan, np.nan
    # tckstats summarises streamline lengths.  "-output mean" (or "std") prints just that
    # one number instead of the whole table, and -quiet keeps progress messages out of the
    # way, so the entire stdout can be cast to float.
    mean = float(run(["tckstats", str(tck), "-output", "mean", "-quiet"]))
    sd = float(run(["tckstats", str(tck), "-output", "std", "-quiet"]))
    return count, generated, mean, sd


# Binary tract-density mask for one tractogram.  Arguments: the .tck, a diffusion-space
# image whose voxel grid the mask should use, and a scratch path for the temporary TDI.
# Returns a boolean 3-D array on that grid, True wherever a streamline passed through.
def density_mask(tck, template, scratch):
    """Binary mask of the voxels visited by at least one streamline."""
    # tckmap counts streamlines per voxel (a tract-density image).  -template gives the
    # output the same voxel grid and transform as the named image, so it lines up with the
    # brain mask and the mean b0.  -force overwrites a scratch file left by an earlier run.
    run(["tckmap", str(tck), str(scratch), "-template", str(template), "-force", "-quiet"])
    # Threshold at zero: we want where the tract is, not how dense it is.  A sparse stray
    # branch then counts as much as the core, which is what makes Dice sensitive to strays.
    mask = nib.load(str(scratch)).get_fdata() > 0
    # The scratch TDI (named _<subj>_<cutoff>_tdi.nii.gz in the QC folder) is deleted at
    # once; only the numbers and the PNGs are kept.
    scratch.unlink()
    return mask


# Dice overlap of two boolean masks: 2 * |A and B| / (|A| + |B|).  1 means the same voxel
# set, 0 means no shared voxel.  NaN when both masks are empty (avoids dividing by zero).
def dice(a, b):
    total = a.sum() + b.sum()
    return 2 * np.logical_and(a, b).sum() / total if total else np.nan


# Draw one 2-D slice: grey background with the tract mask in a fixed colour on top.
# Arguments: a matplotlib axis, the background slice, the boolean mask slice, a title.
def overlay(ax, background, mask, title):
    # imshow runs the first array axis down the page, so a nibabel slice would come out on
    # its side; rot90 turns it the usual way up (second array axis pointing up the page).
    ax.imshow(np.rot90(background), cmap="gray")
    # Masked pixels are drawn transparent, so only the tract colours the background.
    # vmin/vmax fix the colour scale, so the mask (all ones) gets the same colour in every
    # panel rather than whatever autoscaling would pick.
    ax.imshow(np.rot90(np.ma.masked_where(~mask, mask.astype(float))),
              cmap="autumn", alpha=0.8, vmin=0, vmax=1)
    ax.set_title(title, fontsize=10)
    ax.axis("off")


# One dict per participant and cutoff; becomes cutoff_summary.csv at the end.
rows = []
for s in PILOT:
    # The brain mask sets the voxel grid for every tckmap call.  The mean b0 is a nicer
    # background but is optional in the project layout, so fall back to the mask itself.
    template = PROJECT / "dwi" / s / "nodif_brain_mask.nii.gz"
    b0 = PROJECT / "dwi" / s / "mean_b0.nii.gz"
    background = nib.load(str(b0 if b0.exists() else template)).get_fdata()

    # Density masks for this participant, keyed by cutoff string, in command-line order.
    masks = {}
    for c in CUTOFFS:
        # Name written by 04_tune_cutoff.sh.  A missing tractogram is reported and skipped
        # rather than fatal, so a partial sweep (say, one cutoff not yet run) still plots.
        tck = OUT / s / "tckgen" / TRACT / f"{TRACT}_pilot_{c}.tck"
        if not tck.exists():
            print(f"[{s}] cutoff {c}: no tractogram (run 04_tune_cutoff.sh)")
            continue
        count, generated, mean, sd = tck_summary(tck)
        masks[c] = density_mask(tck, template, QC / f"_{s}_{c}_tdi.nii.gz")
        # "voxels" is the TDI footprint.  A permissive cutoff that fills the corridor
        # instead of following the tract shows up here as a jump over the other cutoffs.
        rows.append({
            "subject": s, "cutoff": c, "selected": count, "generated": generated,
            "voxels": int(masks[c].sum()), "mean_len_mm": mean, "sd_len_mm": sd,
        })
    # No tractogram at any cutoff: nothing to draw for this participant.
    if not masks:
        continue

    # Dice overlap of every cutoff with the reference cutoff
    # rows holds every participant so far, hence the filter on the participant ID.  If the
    # reference tractogram is missing for this participant the key is never set and pandas
    # leaves the CSV cell empty.  The reference against itself scores 1 by construction.
    for row in rows:
        if row["subject"] == s and REFERENCE in masks:
            row["dice_vs_reference"] = round(dice(masks[REFERENCE], masks[row["cutoff"]]), 3)

    # Slices through the densest part of the union of all cutoffs
    # The same slice is used for every column, so the columns can be compared by eye.
    # Summing over axes (0, 1) leaves one voxel count per axial slice (third axis); over
    # (0, 2) one per coronal slice (second axis).  argmax picks the fullest of each.
    union = np.logical_or.reduce(list(masks.values()))
    k_axial = int(np.argmax(union.sum(axis=(0, 1))))
    k_coronal = int(np.argmax(union.sum(axis=(0, 2))))

    # Two rows (axial, coronal) by one column per cutoff that had a tractogram; the width
    # grows with the number of columns.  squeeze=False keeps axes a 2-D array even when
    # there is a single cutoff, so axes[0][j] below works in every case.
    fig, axes = plt.subplots(2, len(masks), figsize=(3.2 * len(masks), 6.4), squeeze=False)
    for j, (c, mask) in enumerate(masks.items()):
        overlay(axes[0][j], background[:, :, k_axial], mask[:, :, k_axial],
                f"Axial, cutoff {c}")
        overlay(axes[1][j], background[:, k_coronal, :], mask[:, k_coronal, :],
                f"Coronal, cutoff {c}")
    # "uncleaned" in the title is deliberate: these are raw tckgen outputs.  Much of the
    # extra thickness at a permissive cutoff is what Step 6 removes, so judge the path,
    # not the width.  bbox_inches="tight" trims the white margin around the figure.
    fig.suptitle(f"{s}  {TRACT}  pilot cutoffs (uncleaned)", fontsize=11)
    fig.tight_layout()
    fig.savefig(QC / f"{s}_cutoff_compare.png", dpi=110, bbox_inches="tight")
    # Close each figure explicitly; otherwise matplotlib keeps them all in memory.
    plt.close(fig)
    print(f"[{s}] wrote {s}_cutoff_compare.png")

# Every pilot participant was skipped.  Usually 04_tune_cutoff.sh has not been run yet, or
# TRACT in 00_config.sh no longer names the tract it was run for.
if not rows:
    sys.exit("no pilot tractograms found")

# The per-participant table.  Cutoffs are written as typed ("0.1", not 0.1).
summary = pd.DataFrame(rows)
summary.to_csv(QC / "cutoff_summary.csv", index=False)

# Mean across pilot participants, one bar per cutoff
# Four panels as (CSV column, panel title).  Dice is not charted; read it from the CSV.
panels = [("selected", "Streamlines selected"), ("generated", "Streamlines generated"),
          ("voxels", "Occupied voxels"), ("sd_len_mm", "SD of length (mm)")]
# sort=False keeps the cutoffs in command-line order; sorted as strings, "0.1" would land
# after "0.08".  mean() skips the NaN lengths of any empty tractogram.
means = summary.groupby("cutoff", sort=False)[[k for k, _ in panels]].mean()
fig, axes = plt.subplots(1, len(panels), figsize=(15, 3.6))
for ax, (key, title) in zip(axes, panels):
    ax.bar(means.index.astype(str), means[key], color="#3A6B8C")
    ax.set_title(title)
    ax.set_xlabel("FOD amplitude cutoff")
fig.tight_layout()
fig.savefig(QC / "cutoff_summary.png", dpi=110)
plt.close(fig)

# Echo the whole table so it lands in the terminal and in any log the run is tee'd into.
print(summary.to_string(index=False))
print(f"\nsummary -> {QC / 'cutoff_summary.csv'} and cutoff_summary.png")
```

</details>
<!-- /script:04b_compare_cutoffs.py -->
