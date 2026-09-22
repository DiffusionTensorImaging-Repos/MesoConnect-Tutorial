#!/usr/bin/env python3
"""Step 7. Tract-density overlays of every cleaned bundle, with automatic flags.

Run in a shell where 00_config.sh has been sourced:

    source 00_config.sh
    python 07_visual_qc.py

For each participant the cleaned bundle is converted to a tract-density image
(tckmap) and drawn over the mean b = 0 image in the axial and coronal slices
that contain the most streamlines.  Flags mark bundles that need inspection in
a viewer; they do not replace review of the unflagged images.

Needs, per participant:
    $OUT/<subj>/tckgen/<TRACT>/<TRACT>_<CUTOFF>_cleaned.tck   written by Step 6
    $PROJECT/dwi/<subj>/nodif_brain_mask.nii.gz               grid for the TDI
    $PROJECT/dwi/<subj>/mean_b0.nii.gz                        background (optional)
MRtrix3's tckmap must be on PATH.  Everything else is Python: nibabel, numpy,
pandas and matplotlib.

Outputs: $OUT/qc/<TRACT>/<subj>_<TRACT>_qc.png and qc_flags.csv

Expect a few seconds per participant (one tckmap call on a small bundle plus one
small figure), so a full sample takes minutes and needs no tmux.  As it runs, one
line per participant prints the voxel count, the peak density and any flag; the
last lines give "N of M participants flagged" and the flagged rows.  Zero flags is
the expected result on clean data.  Open the PNGs anyway: the flags only catch
gross failures (empty, tiny or runaway bundles), not a bundle of normal size in
the wrong place.  What a good bundle looks like is described under "Criteria" on
the Step 7 page.

Rerunning: the flags and qc_flags.csv are rebuilt on every run, but an existing
PNG is left alone unless FORCE=1 (or you delete it), so a rerun after fixing one
participant is cheap.  Nothing later in the pipeline reads qc_flags.csv.  A
participant you decide to drop has to be taken out of $SUBJECTS_FILE (or of
$COVARIATES_CSV, which Step 8b joins on) by hand: Step 8 profiles everyone in
the list who has a cleaned bundle, and Step 9 models whoever survives that join.
"""
import os
import subprocess
import sys
from pathlib import Path

# Choose the file-only backend before pyplot is imported.  With the default backend
# matplotlib tries to open a window, which fails on a cluster node or over ssh with
# no display.
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import nibabel as nib
import numpy as np
import pandas as pd


# Read one variable exported by 00_config.sh, or stop with a message that says what
# to do.  sys.exit() given a string prints it to stderr and exits with status 1, so a
# forgotten `source 00_config.sh` fails loudly instead of producing paths like "/qc".
def env(name):
    if name not in os.environ:
        sys.exit(f"{name} is not set: run `source 00_config.sh` first")
    return os.environ[name]


# Settings from 00_config.sh.  CUTOFF stays a string because it is only used to build
# the file name Steps 5 and 6 used (e.g. l_vta_l_hipp_0.01_cleaned.tck).
PROJECT = Path(env("PROJECT"))
OUT = Path(env("OUT"))
TRACT = env("TRACT")
CUTOFF = env("CUTOFF")
# FORCE is optional (default "0"); only the exact string "1" makes us redraw images.
FORCE = os.environ.get("FORCE", "0") == "1"
# split() with no argument breaks on any whitespace, so CRLF line endings, blank lines
# and a missing final newline in subjects.txt are all harmless (same tolerance as
# read_subjects in the config).
SUBJECTS = Path(env("SUBJECTS_FILE")).read_text().split()

# Flag thresholds (Table 1 on the Step 7 page; also listed under Reference:
# Parameters).  They catch gross failures only.  In the example dataset the whole
# corridor was under 2,000 voxels (Step 3 page), and tckgen -exclude keeps every
# streamline inside it, so a bundle occupying 5,000 voxels means the corridor or the
# exclusion mask went wrong; check that participant's corridor size in the Step 3 log
# and the warped regions from Step 2.  Fewer than 50 means almost nothing survived
# tractography or cleaning.  All of a participant's streamlines run through one narrow
# corridor, so the busiest voxel should hold far more than 5 of them; a peak below 5
# means they are spread thin or very few are left.  All three counts depend on voxel
# size and on DILATE_VOX, so revisit them if your data or corridor differ much from the
# example's.
MIN_VOXELS = 50         # fewer occupied voxels: LOW_COVERAGE
MAX_VOXELS = 5000       # more occupied voxels: HIGH_COVERAGE (bundle leaves the pathway)
MIN_PEAK_DENSITY = 5    # peak streamlines per voxel below this: LOW_DENSITY

# One QC folder per tract.  parents=True also creates $OUT/qc the first time;
# exist_ok=True keeps reruns quiet.
QC = OUT / "qc" / TRACT
QC.mkdir(parents=True, exist_ok=True)


# Turn the two numbers measured from the TDI into one flag string.
#   n_voxels  number of voxels with at least one streamline
#   peak      largest number of streamlines through any single voxel
# The checks run in order and the first hit wins, so an empty bundle reports
# LOW_COVERAGE rather than LOW_DENSITY.  Returns "" for a bundle that passes; the CSV
# and the summary at the end both rely on that empty string.
def flag_for(n_voxels, peak):
    if n_voxels < MIN_VOXELS:
        return "LOW_COVERAGE"
    if n_voxels > MAX_VOXELS:
        return "HIGH_COVERAGE"
    if peak < MIN_PEAK_DENSITY:
        return "LOW_DENSITY"
    return ""


# Draw one panel: the b0 slice in grey with the density slice on top in "hot".
#   ax          matplotlib axes to draw into
#   background  2-D slice of the b0 (or mask) image
#   density     2-D slice of the TDI, same grid
#   title       panel label ("Axial" or "Coronal")
# imshow alone would run the first array axis down the page; np.rot90 turns the slice so
# its second axis runs up the page, which with the usual storage order (x left-right,
# y front-back, z bottom-top) puts anterior at the top of the axial panel and superior
# at the top of the coronal one.  Left-right is whatever order the file is stored in,
# so do not read hemisphere off these panels; use a viewer for that.  Voxels with no
# streamlines are masked rather than drawn as black so the anatomy shows through, and
# alpha=0.7 keeps the b0 visible under the bundle.  axis("off") drops the ticks and
# frame; voxel indices mean nothing here.
def overlay(ax, background, density, title):
    ax.imshow(np.rot90(background), cmap="gray")
    ax.imshow(np.rot90(np.ma.masked_where(density <= 0, density)), cmap="hot", alpha=0.7)
    ax.set_title(title)
    ax.axis("off")


# Main loop.  Every participant gets a row in rows whatever happens to them, so
# qc_flags.csv always lists the whole sample.
rows = []
for s in SUBJECTS:
    # Inputs for this participant.  The brain mask doubles as the tckmap template so
    # the TDI lands on the diffusion grid; mean_b0 is only used for the picture.
    tck = OUT / s / "tckgen" / TRACT / f"{TRACT}_{CUTOFF}_cleaned.tck"
    template = PROJECT / "dwi" / s / "nodif_brain_mask.nii.gz"
    b0 = PROJECT / "dwi" / s / "mean_b0.nii.gz"
    png = QC / f"{s}_{TRACT}_qc.png"

    # No cleaned bundle (Step 5 or 6 produced nothing for this participant): record it
    # and move on rather than crash, so one bad participant does not block the rest.
    if not tck.exists():
        rows.append({"Subject": s, "Voxels": 0, "Peak_density": 0, "Flag": "MISSING"})
        print(f"[{s}] MISSING cleaned bundle")
        continue

    # Streamlines to voxels.  tckmap's default output is the tract-density image (TDI):
    # each voxel holds the number of streamlines that pass through it.
    #   -template  put the output on this image's voxel grid, so the TDI overlays the
    #              b0 and mask voxel for voxel
    #   -force     overwrite the scratch file if an interrupted run left one behind
    #   -quiet     no progress bar or info messages in the output
    # The scratch file is deleted as soon as the array is in memory; the leading "_"
    # just marks it as temporary if a crash leaves it behind.  check=True turns a
    # non-zero exit from tckmap (a bad .tck, say) into an exception so the script stops
    # instead of carrying on with no data.  If tckmap is not on PATH at all, subprocess
    # raises FileNotFoundError on its own.
    tdi = QC / f"_{s}_tdi.nii.gz"
    subprocess.run(["tckmap", str(tck), str(tdi), "-template", str(template),
                    "-force", "-quiet"], check=True)
    density = nib.load(str(tdi)).get_fdata()
    tdi.unlink()

    # The two numbers the flags rest on: how many voxels the bundle touches at all, and
    # how many streamlines share the busiest voxel.  Printed per participant so an
    # outlier that still clears the thresholds is visible as it scrolls by.
    n_voxels = int((density > 0).sum())
    peak = float(density.max())
    flag = flag_for(n_voxels, peak)
    rows.append({"Subject": s, "Voxels": n_voxels, "Peak_density": peak, "Flag": flag})
    print(f"[{s}] {n_voxels} voxels, peak {peak:.0f}  {flag}")

    # Resume.  The flag above was recomputed regardless; the picture is only redrawn
    # when it is missing or FORCE=1.  Delete one PNG to regenerate just that one.
    if png.exists() and not FORCE:
        continue
    # mean_b0 is optional in the project layout.  Fall back to the brain mask, which
    # gives a flat white silhouette but still shows whether the bundle sits inside it.
    background = nib.load(str(b0 if b0.exists() else template)).get_fdata()
    # Pick the slices with the most streamline hits.  Summing over axes 0 and 1 leaves
    # one total per z index (axial slices); summing over 0 and 2 leaves one per y index
    # (coronal).  This assumes the usual storage order (x left-right, y front-back,
    # z bottom-top).  If yours differs the panels are mislabelled; the flags are fine.
    k_axial = int(np.argmax(density.sum(axis=(0, 1))))
    k_coronal = int(np.argmax(density.sum(axis=(0, 2))))
    # Two panels side by side, 10 x 5 inches; at the 100 dpi used below that is about
    # 1000 x 500 px, enough to skim in a thumbnail browser.
    fig, axes = plt.subplots(1, 2, figsize=(10, 5))
    overlay(axes[0], background[:, :, k_axial], density[:, :, k_axial], "Axial")
    overlay(axes[1], background[:, k_coronal, :], density[:, k_coronal, :], "Coronal")
    # The flag goes into the title so it is visible when skimming the images without
    # the CSV open.
    fig.suptitle(f"{s}  {TRACT}  cleaned" + (f"  [{flag}]" if flag else ""), fontsize=11)
    fig.tight_layout()
    # bbox_inches="tight" trims the white margin.  plt.close matters inside a loop:
    # pyplot keeps every figure alive until it is closed, and a long sample would eat
    # memory (matplotlib starts warning at 20 open figures).
    fig.savefig(png, dpi=100, bbox_inches="tight")
    plt.close(fig)

# Write the flag table and print a summary.  index=False drops pandas' row numbers so
# the CSV has just Subject, Voxels, Peak_density and Flag.  Anything with a non-empty
# Flag counts as flagged, so MISSING participants show up in the summary too.
flags = pd.DataFrame(rows)
flags.to_csv(QC / "qc_flags.csv", index=False)
flagged = flags[flags["Flag"] != ""]
print(f"\n{len(flagged)} of {len(flags)} participants flagged")
if len(flagged):
    print(flagged.to_string(index=False))
print(f"flags -> {QC / 'qc_flags.csv'}")
