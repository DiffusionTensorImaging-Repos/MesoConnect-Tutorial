#!/usr/bin/env python3
"""Step 4b. Compare pilot tractograms from 04_tune_cutoff.sh to pick CUTOFF for 00_config.sh.

Inputs:  $OUT/<subj>/tckgen/<TRACT>/<TRACT>_pilot_<cutoff>.tck
         $PROJECT/dwi/<subj>/nodif_brain_mask.nii.gz and mean_b0.nii.gz (optional)
Outputs: $OUT/qc/<TRACT>_cutoff_pilot/<subj>_cutoff_compare.png
         $OUT/qc/<TRACT>_cutoff_pilot/cutoff_summary.csv and cutoff_summary.png
Run:     source 00_config.sh
         python 04b_compare_cutoffs.py "sub-01 sub-02 sub-03" "0.1 0.08 0.06 0.01"
         Both arguments optional; list the most conservative cutoff first (Dice reference).
"""
import os
import subprocess
import sys
from pathlib import Path

# File-only backend: this usually runs on a cluster node with no display.
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import nibabel as nib
import numpy as np
import pandas as pd


# Read one variable exported by 00_config.sh; fail clearly if it was not sourced.
def env(name):
    if name not in os.environ:
        sys.exit(f"{name} is not set: run `source 00_config.sh` first")
    return os.environ[name]


PROJECT = Path(env("PROJECT"))
OUT = Path(env("OUT"))
TRACT = env("TRACT")

if len(sys.argv) > 1:
    PILOT = sys.argv[1].split()
else:
    PILOT = Path(env("SUBJECTS_FILE")).read_text().split()[:5]
# Cutoffs stay strings: "0.1" has to match the file name 04_tune_cutoff.sh wrote.
CUTOFFS = sys.argv[2].split() if len(sys.argv) > 2 else ["0.1", "0.08", "0.06", "0.01"]
REFERENCE = CUTOFFS[0]          # most conservative cutoff: reference for Dice overlap

QC = OUT / "qc" / f"{TRACT}_cutoff_pilot"
QC.mkdir(parents=True, exist_ok=True)


# Run a command and return its stdout; check=True so a damaged .tck stops the script.
def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout


def tck_summary(tck):
    """Streamlines selected, generated (selected plus rejected), mean and SD of length (mm)."""
    info = {}
    for line in run(["tckinfo", str(tck)]).splitlines():
        key, _, value = line.strip().partition(":")
        info[key] = value.strip()
    # "count" is what tckgen kept; "total_count" is everything it generated (one per seed).
    count = int(info.get("count", 0))
    generated = int(info.get("total_count", 0))
    if count == 0:
        return count, generated, np.nan, np.nan
    # -output mean/std: print that one number only, so the whole stdout casts to float.
    mean = float(run(["tckstats", str(tck), "-output", "mean", "-quiet"]))
    sd = float(run(["tckstats", str(tck), "-output", "std", "-quiet"]))
    return count, generated, mean, sd


def density_mask(tck, template, scratch):
    """Binary mask of the voxels visited by at least one streamline."""
    # tckmap: tract-density image; -template puts it on the brain mask's voxel grid.
    run(["tckmap", str(tck), str(scratch), "-template", str(template), "-force", "-quiet"])
    # Binarise at zero so a sparse stray branch counts as much as the core.
    mask = nib.load(str(scratch)).get_fdata() > 0
    scratch.unlink()
    return mask


# Dice overlap of two boolean masks; NaN when both are empty.
def dice(a, b):
    total = a.sum() + b.sum()
    return 2 * np.logical_and(a, b).sum() / total if total else np.nan


# One slice: grey background with the tract mask drawn on top.
def overlay(ax, background, mask, title):
    ax.imshow(np.rot90(background), cmap="gray")
    ax.imshow(np.rot90(np.ma.masked_where(~mask, mask.astype(float))),
              cmap="autumn", alpha=0.8, vmin=0, vmax=1)
    ax.set_title(title, fontsize=10)
    ax.axis("off")


rows = []
for s in PILOT:
    # The mean b0 is optional in the project layout, so fall back to the brain mask.
    template = PROJECT / "dwi" / s / "nodif_brain_mask.nii.gz"
    b0 = PROJECT / "dwi" / s / "mean_b0.nii.gz"
    background = nib.load(str(b0 if b0.exists() else template)).get_fdata()

    masks = {}
    for c in CUTOFFS:
        # A missing tractogram is skipped, not fatal, so a partial sweep still plots.
        tck = OUT / s / "tckgen" / TRACT / f"{TRACT}_pilot_{c}.tck"
        if not tck.exists():
            print(f"[{s}] cutoff {c}: no tractogram (run 04_tune_cutoff.sh)")
            continue
        count, generated, mean, sd = tck_summary(tck)
        masks[c] = density_mask(tck, template, QC / f"_{s}_{c}_tdi.nii.gz")
        rows.append({
            "subject": s, "cutoff": c, "selected": count, "generated": generated,
            "voxels": int(masks[c].sum()), "mean_len_mm": mean, "sd_len_mm": sd,
        })
    if not masks:
        continue

    # Dice against the reference; rows holds every participant so far, hence the ID filter.
    for row in rows:
        if row["subject"] == s and REFERENCE in masks:
            row["dice_vs_reference"] = round(dice(masks[REFERENCE], masks[row["cutoff"]]), 3)

    # One slice for every column: the fullest axial and coronal slice of the union.
    union = np.logical_or.reduce(list(masks.values()))
    k_axial = int(np.argmax(union.sum(axis=(0, 1))))
    k_coronal = int(np.argmax(union.sum(axis=(0, 2))))

    fig, axes = plt.subplots(2, len(masks), figsize=(3.2 * len(masks), 6.4), squeeze=False)
    for j, (c, mask) in enumerate(masks.items()):
        overlay(axes[0][j], background[:, :, k_axial], mask[:, :, k_axial],
                f"Axial, cutoff {c}")
        overlay(axes[1][j], background[:, k_coronal, :], mask[:, k_coronal, :],
                f"Coronal, cutoff {c}")
    # "uncleaned" is deliberate: judge the path, not the width; Step 6 trims the excess.
    fig.suptitle(f"{s}  {TRACT}  pilot cutoffs (uncleaned)", fontsize=11)
    fig.tight_layout()
    fig.savefig(QC / f"{s}_cutoff_compare.png", dpi=110, bbox_inches="tight")
    plt.close(fig)
    print(f"[{s}] wrote {s}_cutoff_compare.png")

if not rows:
    sys.exit("no pilot tractograms found")

summary = pd.DataFrame(rows)
summary.to_csv(QC / "cutoff_summary.csv", index=False)

# Mean across pilot participants, one bar per cutoff; Dice is in the CSV only.
panels = [("selected", "Streamlines selected"), ("generated", "Streamlines generated"),
          ("voxels", "Occupied voxels"), ("sd_len_mm", "SD of length (mm)")]
# sort=False keeps command-line order; sorted as strings, "0.1" would land after "0.08".
means = summary.groupby("cutoff", sort=False)[[k for k, _ in panels]].mean()
fig, axes = plt.subplots(1, len(panels), figsize=(15, 3.6))
for ax, (key, title) in zip(axes, panels):
    ax.bar(means.index.astype(str), means[key], color="#3A6B8C")
    ax.set_title(title)
    ax.set_xlabel("FOD amplitude cutoff")
fig.tight_layout()
fig.savefig(QC / "cutoff_summary.png", dpi=110)
plt.close(fig)

print(summary.to_string(index=False))
print(f"\nsummary -> {QC / 'cutoff_summary.csv'} and cutoff_summary.png")
