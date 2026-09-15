#!/usr/bin/env python3
"""Step 4b — LOOK at the cutoff pilot: side-by-side tract-density images, Dice, lengths.

Run after 04_tune_cutoff.sh.  For each pilot subject it renders one row per view (axial,
coronal) with one column per cutoff, and writes a summary CSV + bar chart of streamline
count, seeds used, Dice overlap against the reference (most conservative) cutoff, and
mean/SD streamline length.  Usage:
    python 04b_compare_cutoffs.py "s001 s002 s003" "0.1 0.08 0.06 0.01"
"""
import os, sys, subprocess, csv
from pathlib import Path
import numpy as np, nibabel as nib, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt

PROJECT = Path(os.environ["PROJECT"]); OUT = Path(os.environ["OUT"]); TRACT = os.environ["TRACT"]
PILOT = sys.argv[1].split() if len(sys.argv) > 1 else [l.strip() for l in open(os.environ["SUBJECTS_FILE"])][:5]
CUTOFFS = sys.argv[2].split() if len(sys.argv) > 2 else ["0.1", "0.08", "0.06", "0.01"]
REF = CUTOFFS[0]                                   # most conservative = reference for Dice
qc = OUT / "qc" / f"{TRACT}_cutoff_pilot"; qc.mkdir(parents=True, exist_ok=True)

def tck_stats(tck):
    info = subprocess.run(["tckinfo", str(tck)], capture_output=True, text=True).stdout
    n = next((int(l.split()[1]) for l in info.splitlines() if l.strip().startswith("count:")), 0)
    seeds = next((int(l.split()[1]) for l in info.splitlines() if "total_count:" in l), 0)
    st = subprocess.run(["tckstats", str(tck), "-quiet"], capture_output=True, text=True).stdout
    mean = sd = np.nan
    for l in st.splitlines():
        if l.strip().lower().startswith("mean"): mean = float(l.split()[1])
        if l.strip().lower().startswith("std"):  sd = float(l.split()[1])
    return n, seeds, mean, sd

def tdi(tck, ref, out):
    subprocess.run(["tckmap", str(tck), str(out), "-template", str(ref), "-force", "-quiet"], check=True)
    return nib.load(str(out)).get_fdata()

rows = []
for s in PILOT:
    ref_img = PROJECT / "dwi" / s / "nodif_brain_mask.nii.gz"; bg_f = PROJECT / "dwi" / s / "mean_b0.nii.gz"
    bg = nib.load(str(bg_f if bg_f.exists() else ref_img)).get_fdata()
    maps = {}
    for c in CUTOFFS:
        tck = OUT / s / "tckgen" / TRACT / f"{TRACT}_pilot_{c}.tck"
        if not tck.exists(): print(f"[{s}] missing cutoff {c}"); continue
        maps[c] = tdi(tck, ref_img, qc / f"_{s}_{c}_tdi.nii.gz") > 0
        n, seeds, mean, sd = tck_stats(tck)
        dice = np.nan
        if REF in maps and c != REF:
            a, b = maps[REF], maps[c]; dice = 2 * (a & b).sum() / max(a.sum() + b.sum(), 1)
        rows.append(dict(subject=s, cutoff=c, streamlines=n, seeds_used=seeds, voxels=int(maps[c].sum()),
                         dice_vs_ref=round(float(dice), 3) if not np.isnan(dice) else "", mean_len_mm=mean, sd_len_mm=sd))
    if not maps: continue
    any_map = np.logical_or.reduce(list(maps.values()))
    ax_i = int(np.argmax(any_map.sum(axis=(0, 1)))); co_i = int(np.argmax(any_map.sum(axis=(0, 2))))
    fig, axes = plt.subplots(2, len(maps), figsize=(3.2 * len(maps), 6.4), squeeze=False)
    fig.suptitle(f"{s} · {TRACT} · cutoff sweep (uncleaned)", fontweight="bold")
    for j, (c, m) in enumerate(maps.items()):
        for i, (b, t, lab) in enumerate([(bg[:, :, ax_i], m[:, :, ax_i], "axial"), (bg[:, co_i, :], m[:, co_i, :], "coronal")]):
            ax = axes[i][j]; ax.imshow(np.rot90(b), cmap="gray"); ax.imshow(np.rot90(np.ma.masked_where(~t, t.astype(float))), cmap="hot", alpha=.7)
            ax.set_title(f"cutoff {c}" if i == 0 else lab, fontsize=10); ax.axis("off")
    plt.tight_layout(); plt.savefig(qc / f"{s}_cutoff_compare.png", dpi=110, bbox_inches="tight"); plt.close()
    for f in qc.glob(f"_{s}_*_tdi.nii.gz"): f.unlink()
    print(f"[{s}] wrote {s}_cutoff_compare.png")

with open(qc / "cutoff_summary.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
# summary chart: streamline count, seeds used, length SD per cutoff (mean over pilot subjects)
import collections
agg = collections.defaultdict(lambda: collections.defaultdict(list))
for r in rows:
    for k in ("streamlines", "seeds_used", "sd_len_mm", "voxels"):
        if r[k] not in ("", None) and not (isinstance(r[k], float) and np.isnan(r[k])): agg[r["cutoff"]][k].append(r[k])
fig, axes = plt.subplots(1, 4, figsize=(15, 3.6))
for ax, (k, title) in zip(axes, [("streamlines", "streamlines reached"), ("seeds_used", "seeds used"), ("voxels", "TDI voxels"), ("sd_len_mm", "length SD (mm)")]):
    ax.bar(list(agg), [np.mean(agg[c][k]) for c in agg], color="#3A6B8C"); ax.set_title(title); ax.set_xlabel("FOD cutoff")
plt.tight_layout(); plt.savefig(qc / "cutoff_summary.png", dpi=110); plt.close()
print("summary ->", qc / "cutoff_summary.csv", "and cutoff_summary.png")
