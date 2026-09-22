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
