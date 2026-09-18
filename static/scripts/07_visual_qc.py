#!/usr/bin/env python3
"""Step 7. Tract-density overlays of every cleaned bundle, with automatic flags.

Run in a shell where 00_config.sh has been sourced:

    source 00_config.sh
    python 07_visual_qc.py

For each participant the cleaned bundle is converted to a tract-density image
(tckmap) and drawn over the mean b = 0 image in the axial and coronal slices
that contain the most streamlines.  Flags mark bundles that need inspection in
a viewer; they do not replace review of the unflagged images.

Outputs: $OUT/qc/<TRACT>/<subj>_<TRACT>_qc.png and qc_flags.csv
"""
import os
import subprocess
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import nibabel as nib
import numpy as np
import pandas as pd


def env(name):
    if name not in os.environ:
        sys.exit(f"{name} is not set: run `source 00_config.sh` first")
    return os.environ[name]


PROJECT = Path(env("PROJECT"))
OUT = Path(env("OUT"))
TRACT = env("TRACT")
CUTOFF = env("CUTOFF")
FORCE = os.environ.get("FORCE", "0") == "1"
SUBJECTS = Path(env("SUBJECTS_FILE")).read_text().split()

MIN_VOXELS = 50         # fewer occupied voxels: LOW_COVERAGE
MAX_VOXELS = 5000       # more occupied voxels: HIGH_COVERAGE (bundle leaves the pathway)
MIN_PEAK_DENSITY = 5    # peak streamlines per voxel below this: LOW_DENSITY

QC = OUT / "qc" / TRACT
QC.mkdir(parents=True, exist_ok=True)


def flag_for(n_voxels, peak):
    if n_voxels < MIN_VOXELS:
        return "LOW_COVERAGE"
    if n_voxels > MAX_VOXELS:
        return "HIGH_COVERAGE"
    if peak < MIN_PEAK_DENSITY:
        return "LOW_DENSITY"
    return ""


def overlay(ax, background, density, title):
    ax.imshow(np.rot90(background), cmap="gray")
    ax.imshow(np.rot90(np.ma.masked_where(density <= 0, density)), cmap="hot", alpha=0.7)
    ax.set_title(title)
    ax.axis("off")


rows = []
for s in SUBJECTS:
    tck = OUT / s / "tckgen" / TRACT / f"{TRACT}_{CUTOFF}_cleaned.tck"
    template = PROJECT / "dwi" / s / "nodif_brain_mask.nii.gz"
    b0 = PROJECT / "dwi" / s / "mean_b0.nii.gz"
    png = QC / f"{s}_{TRACT}_qc.png"

    if not tck.exists():
        rows.append({"Subject": s, "Voxels": 0, "Peak_density": 0, "Flag": "MISSING"})
        print(f"[{s}] MISSING cleaned bundle")
        continue

    tdi = QC / f"_{s}_tdi.nii.gz"
    subprocess.run(["tckmap", str(tck), str(tdi), "-template", str(template),
                    "-force", "-quiet"], check=True)
    density = nib.load(str(tdi)).get_fdata()
    tdi.unlink()

    n_voxels = int((density > 0).sum())
    peak = float(density.max())
    flag = flag_for(n_voxels, peak)
    rows.append({"Subject": s, "Voxels": n_voxels, "Peak_density": peak, "Flag": flag})
    print(f"[{s}] {n_voxels} voxels, peak {peak:.0f}  {flag}")

    if png.exists() and not FORCE:
        continue
    background = nib.load(str(b0 if b0.exists() else template)).get_fdata()
    k_axial = int(np.argmax(density.sum(axis=(0, 1))))
    k_coronal = int(np.argmax(density.sum(axis=(0, 2))))
    fig, axes = plt.subplots(1, 2, figsize=(10, 5))
    overlay(axes[0], background[:, :, k_axial], density[:, :, k_axial], "Axial")
    overlay(axes[1], background[:, k_coronal, :], density[:, k_coronal, :], "Coronal")
    fig.suptitle(f"{s}  {TRACT}  cleaned" + (f"  [{flag}]" if flag else ""), fontsize=11)
    fig.tight_layout()
    fig.savefig(png, dpi=100, bbox_inches="tight")
    plt.close(fig)

flags = pd.DataFrame(rows)
flags.to_csv(QC / "qc_flags.csv", index=False)
flagged = flags[flags["Flag"] != ""]
print(f"\n{len(flagged)} of {len(flags)} participants flagged")
if len(flagged):
    print(flagged.to_string(index=False))
print(f"flags -> {QC / 'qc_flags.csv'}")
