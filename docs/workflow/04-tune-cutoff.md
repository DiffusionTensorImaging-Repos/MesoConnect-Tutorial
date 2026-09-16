---
sidebar_position: 5
title: "Step 4. Cutoff selection"
---

# Step 4. Selection of the FOD amplitude cutoff

The fibre orientation distribution (FOD) amplitude cutoff determines the minimum FOD amplitude at which tracking continues. A high cutoff terminates streamlines before they reach the target; a low cutoff, in unconstrained tracking, produces spurious streamlines. The corridor alters this trade-off. With tracking confined to the corridor, a permissive cutoff produces well-formed bundles while consuming far fewer seeds than a conservative cutoff. This behaviour should be verified for each dataset and tract family by a pilot sweep on a small number of participants, followed by tabulation and side-by-side inspection of the reconstructions.

During atlas construction at 7 T the cutoff was 0.06 for ventral tegmental area (VTA) → hippocampus and 0.08 for hippocampus → accumbens. The MRtrix3 default for FOD-based tracking is 0.05. Because lower field strength yields noisier FOD estimates, a higher cutoff (approximately 0.08) was anticipated for 3 T data. The pilot sweep did not support that expectation.

## Pilot sweep

The sweep uses five participants, four cutoffs and reduced budgets (`-select 1000`, `-seeds 5000000`); all other parameters match the production run.

```bash
bash 04_tune_cutoff.sh "s169 s4222 s4418 s606 s1000" "0.1 0.08 0.06 0.01"
```

The script reports streamlines reached, seeds consumed and mean length for each participant and cutoff. Table 1 gives the streamline counts obtained in the example dataset. At 0.1 most runs exhausted the seed budget before reaching the target. At 0.08 some participants reached the target and one stopped at 309. At 0.06 and at 0.01 all runs reached the target; the 0.01 runs consumed approximately one fifth of the seeds (about 415,000 versus 2.1 million or more at 0.06). Reaching the target in every pilot participant is a necessary condition for a cutoff; the reconstructions must also correspond to the tract, which is assessed next.

**Table 1**

*Streamlines Reached by Cutoff in the Pilot Sweep, Posterior VTA → Hippocampus*

| Participant | Hemisphere | 0.1 | 0.08 | 0.06 | 0.01 |
|---|---|---|---|---|---|
| s169 | L | 118 | 556 | 1000 | 1000 |
| s169 | R | 30 | 434 | 1000 | 1000 |
| s4222 | L | 274 | 1000 | 1000 | 1000 |
| s4222 | R | 165 | 906 | 1000 | 1000 |
| s4418 | L | 1000 | 1000 | 1000 | 1000 |
| s4418 | R | 1000 | 1000 | 1000 | 1000 |
| s606 | L | 88 | 309 | 1000 | 1000 |
| s606 | R | 731 | 1000 | 1000 | 1000 |

*Note.* Target 1,000 streamlines; seed limit 5 million. L = left; R = right.

## Side-by-side comparison

For each participant, the tract-density image (TDI) at each cutoff is rendered on the same axial and coronal slices, one column per cutoff. Dice overlap of each cutoff against the most conservative one, the number of TDI voxels, and the mean and standard deviation of streamline length are computed and summarized.

```bash
python 04b_compare_cutoffs.py "s169 s4222 s4418 s606 s1000" "0.1 0.08 0.06 0.01"
```

The script writes one panel per participant, `cutoff_summary.csv`, and a summary chart (Figures 1 and 2). In the example dataset the two cutoffs traced the same trajectory in both views. The 0.01 reconstruction was somewhat thicker (mean Dice = .66 against 0.06), mean lengths were similar (approximately 44 versus 47 mm), and the length standard deviation was slightly greater at 0.01 (7 versus 6 mm). Bundle cleaning (Step 6) removes the outlying streamlines responsible for the additional thickness; the cleaned 0.01 bundle is more compact than the uncleaned 0.06 bundle, as shown on that page.

**Figure 1**

*Tract-Density Images at Two Cutoffs, Uncleaned*

![Tract-density images at cutoff 0.06 and 0.01](/img/cutoff_compare_s169_l.png)

*Note.* Cutoff 0.06 (left) and 0.01 (right) for one participant, left posterior VTA → hippocampus.

**Figure 2**

*Summary Statistics Across the Five Pilot Participants by Cutoff*

![Summary statistics by cutoff](/img/cutoff_stats_comparison.png)

## Selection criterion

The cutoff selected is the most permissive value that reaches the streamline target in every pilot participant and whose reconstruction matches the conservative reconstruction. In the example dataset this was 0.01. Other users of the atlas have used 0.01 for VTA → accumbens. The corridor mask is the condition that makes this value usable; the same cutoff without an exclusion mask produces streamlines throughout the brain. The sweep should be repeated for each tract family, since a cutoff selected for VTA → hippocampus is only a starting value for other pathways.

## Options not used

Anatomically constrained tractography (ACT) was evaluated during atlas construction and abandoned because the tissue segmentation's white-matter mask was too restrictive relative to the gray-matter mask and tracts did not reconstruct. The `-backtrack` and `-crop_at_gmwmi` options and custom `-angle` and `-step_size` values were left at MRtrix3 defaults. These options should be introduced only in response to a specific, observed failure.

## Scripts

<!-- script:04_tune_cutoff.sh -->
```bash title="04_tune_cutoff.sh"
#!/bin/bash
# Step 4 — Pilot the FOD cutoff on a handful of participants before the full run.
# Usage: 04_tune_cutoff.sh "s001 s002 s003 s004 s005" "0.1 0.08 0.06 0.01"
source "$(dirname "$0")/00_config.sh"; start_log "$0"
PILOT=${1:-"$(head -5 "$SUBJECTS_FILE" | tr '\n' ' ')"}; CUTOFFS=${2:-"0.1 0.08 0.06 0.01"}
printf "%-10s %-8s %-12s %-12s %-10s\n" Subject Cutoff Streamlines Seeds MeanLen_mm
for s in $PILOT; do d="$OUT/$s/rois"; o="$OUT/$s/tckgen/$TRACT"; mkdir -p "$o"
  for c in $CUTOFFS; do
    tckgen "$PROJECT/dwi/$s/wm_fod_norm.mif" "$o/${TRACT}_pilot_${c}.tck" \
      -seed_image "$d/${TRACT}_seed_diff.nii.gz" -seed_unidirectional \
      -include "$d/${TRACT}_target_diff.nii.gz" -exclude "$d/${TRACT}_exclusion_mask.nii.gz" \
      -select 1000 -seeds 5000000 -cutoff "$c" -minlength "$MINLEN" -maxlength "$MAXLEN" -stop -nthreads "$NTHREADS" -force -quiet
    n=$(tckinfo "$o/${TRACT}_pilot_${c}.tck" | awk '/^ *count:/{print $2}'); sd=$(tckinfo "$o/${TRACT}_pilot_${c}.tck" | awk '/total_count:/{print $2}')
    ml=$(tckstats "$o/${TRACT}_pilot_${c}.tck" -quiet | awk '/mean/{print $2; exit}')
    printf "%-10s %-8s %-12s %-12s %-10s\n" "$s" "$c" "$n" "$sd" "$ml"
  done
done
echo "Select the most permissive cutoff that reaches the streamline target in every pilot participant."
```
<!-- /script:04_tune_cutoff.sh -->

<!-- script:04b_compare_cutoffs.py -->
```python title="04b_compare_cutoffs.py"
#!/usr/bin/env python3
"""Step 4b — Cutoff pilot comparison: side-by-side tract-density images, Dice, lengths.

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
# summary chart: streamline count, seeds used, length SD per cutoff (mean over pilot participants)
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
```
<!-- /script:04b_compare_cutoffs.py -->
