---
sidebar_position: 7
title: "Step 6. Bundle cleaning"
---

# Step 6. Bundle cleaning

Some streamlines within the corridor follow atypical trajectories. Cleaning is performed with `clean_bundle` from pyAFQ (Kruper et al., 2021), which implements the procedure of Yeatman et al. (2012): each streamline is resampled to 100 points, its Mahalanobis distance from the bundle's mean trajectory is computed, and streamlines exceeding a distance threshold or a length threshold are removed iteratively (Table 1).

## Procedure

**Table 1**

*Cleaning Parameters*

| Parameter | Value | Meaning |
|---|---|---|
| `n_points` | 100 | Resampling prior to comparison. |
| `clean_rounds` | 5 | Maximum iterations; stops earlier when no streamlines are removed. |
| `distance_threshold` | 3 | Streamlines more than 3 *SD* (Mahalanobis) from the bundle centroid are removed. |
| `length_threshold` | 2 | Streamlines longer than the mean length by more than 2 *SD* are removed. |
| `stat` | `mean` | Centroid statistic. |
| `core_only` | 0 | Distance is computed over the full length of each streamline. pyAFQ 3 and later default to the middle 60%; the script sets 0 so that results do not depend on the installed version. |

```python
from AFQ.recognition.cleaning import clean_bundle
cleaned, keep = clean_bundle(sft, n_points=100, clean_rounds=5,
                             distance_threshold=3, length_threshold=2,
                             stat="mean", core_only=0, return_idx=True)
```

The `core_only` argument exists in pyAFQ 3 and later; the script omits it under earlier versions, whose behaviour it reproduces. In pyAFQ 1.3.2 and earlier the function is imported from `AFQ.segmentation`; the script tries both locations.

The full script follows. It requires pyAFQ and DIPY; on older systems `pip` may require the `zipp` package to be upgraded first.

<!-- script:06_clean_bundles.py -->
<details>
<summary>Script <code>06_clean_bundles.py</code> (141 lines)</summary>

```python title="06_clean_bundles.py"
#!/usr/bin/env python3
"""Step 6. Clean each participant's raw corridor tractogram with pyAFQ, then rebuild the
covariate table (streamline count and mean length of every cleaned bundle).
Inputs:  $OUT/<subj>/tckgen/<TRACT>/<TRACT>_<CUTOFF>.tck      raw tractogram from Step 5
         $PROJECT/dwi/<subj>/nodif_brain_mask.nii.gz           reference grid for the .tck
         $SUBJECTS_FILE                                        one participant ID per line
Outputs: $OUT/<subj>/tckgen/<TRACT>/<TRACT>_<CUTOFF>_cleaned.tck
         $OUT/nodewise/<TRACT>_tract_stats.csv
Run:     source 00_config.sh && python 06_clean_bundles.py
         FORCE=1 in the shell redoes participants whose cleaned bundle already exists.
"""
import inspect   # used once, to ask the installed clean_bundle whether it takes core_only
import os
import sys
from pathlib import Path

import pandas as pd
# clean_bundle moved between pyAFQ releases; try the current location, then the old one.
try:
    from AFQ.recognition.cleaning import clean_bundle
except ImportError:                       # pyAFQ 1.3.2 and earlier
    from AFQ.segmentation import clean_bundle
from dipy.io.stateful_tractogram import StatefulTractogram
from dipy.io.streamline import load_tractogram, save_tractogram
from dipy.segment.clustering import QuickBundles
from dipy.segment.featurespeed import ResampleFeature
from dipy.segment.metricspeed import AveragePointwiseEuclideanMetric
from dipy.tracking.streamline import length   # per-streamline length, for the table


# One variable exported by 00_config.sh, or stop with a pointer to source it.
def env(name):
    if name not in os.environ:
        sys.exit(f"{name} is not set: run `source 00_config.sh` first")
    return os.environ[name]


# --- Settings from 00_config.sh ---
PROJECT = Path(env("PROJECT"))
OUT = Path(env("OUT"))
TRACT = env("TRACT")
CUTOFF = env("CUTOFF")   # stays a string; it is only ever used in file names
FORCE = os.environ.get("FORCE", "0") == "1"
SUBJECTS = Path(env("SUBJECTS_FILE")).read_text().split()

# --- Cleaning thresholds (Table 1 on the Step 6 page; not in 00_config.sh) ---
N_POINTS = 100          # resampling for the Mahalanobis distance
CLEAN_ROUNDS = 5        # maximum cleaning iterations
DISTANCE_SD = 3         # Mahalanobis distance threshold, SD
LENGTH_SD = 2           # length threshold, SD above the mean
QB_SPLIT = False        # True: split into two bundles before cleaning
QB_THRESHOLD_MM = 5.0   # QuickBundles distance threshold


CLEAN_ARGS = dict(n_points=N_POINTS, clean_rounds=CLEAN_ROUNDS, stat="mean",
                  distance_threshold=DISTANCE_SD, length_threshold=LENGTH_SD)
# pyAFQ 3+ measures the distance over the middle 60% of each streamline by default;
# core_only=0 restores the full-length computation; pass it only if this pyAFQ knows it.
if "core_only" in inspect.signature(clean_bundle).parameters:
    CLEAN_ARGS["core_only"] = 0


# Clean one tractogram.  We rebuild the result from the kept indices rather than use the
# copy pyAFQ returns, so the output stays in the input's space under every pyAFQ version.
def clean(sft):
    _, keep = clean_bundle(sft, return_idx=True, **CLEAN_ARGS)
    return StatefulTractogram.from_sft(sft.streamlines[keep], sft)


# Load a .tck on the participant's brain-mask grid (a .tck carries no image grid of its own).
# bbox_valid_check=False: do not refuse a streamline that grazes the volume edge.
def load(tck, reference):
    return load_tractogram(str(tck), str(reference), bbox_valid_check=False)


# --- Pass 1: clean every participant that still needs it ---
for s in SUBJECTS:
    tdir = OUT / s / "tckgen" / TRACT
    raw = tdir / f"{TRACT}_{CUTOFF}.tck"
    out = tdir / f"{TRACT}_{CUTOFF}_cleaned.tck"
    reference = PROJECT / "dwi" / s / "nodif_brain_mask.nii.gz"

    # Step 5 renames its output at the end, so a raw file at this path is always complete.
    if not raw.exists():
        print(f"[{s}] SKIP: no tractogram from Step 5")
        continue
    if out.exists() and not FORCE:
        print(f"[{s}] cleaned bundle exists")
        continue
    sft = load(raw, reference)
    n_raw = len(sft.streamlines)
    if n_raw == 0:
        print(f"[{s}] SKIP: 0 streamlines")
        continue

    if not QB_SPLIT:
        cleaned = clean(sft)
        save_tractogram(cleaned, str(out), bbox_valid_check=False)
        n_clean = len(cleaned.streamlines)
        print(f"[{s}] {n_raw} -> {n_clean} streamlines ({100 * n_clean / n_raw:.0f}% retained)")
        continue

    # Two-bundle path: cluster with QuickBundles and clean the two largest clusters separately.
    metric = AveragePointwiseEuclideanMetric(ResampleFeature(nb_points=N_POINTS))
    clusters = QuickBundles(threshold=QB_THRESHOLD_MM, metric=metric).cluster(sft.streamlines)
    largest = sorted(clusters, key=len, reverse=True)[:2]
    for i, cluster in enumerate(largest, start=1):
        part = StatefulTractogram.from_sft(sft.streamlines[cluster.indices], sft)
        cleaned = clean(part)
        name = f"{TRACT}_{CUTOFF}_cluster{i}_cleaned.tck"
        save_tractogram(cleaned, str(tdir / name), bbox_valid_check=False)
        print(f"[{s}] cluster {i}: {len(cluster)} -> {len(cleaned.streamlines)} streamlines")
    # Nothing goes to _cleaned.tck here: copy the right cluster to it by hand, then rerun.
    print(f"[{s}] inspect both clusters; copy the correct one to {out.name}")

# --- Pass 2: covariate table from the cleaned bundles (rebuilt every run) ---
# A separate loop so the table also covers participants skipped above or copied in by hand.
rows = []
for s in SUBJECTS:
    tdir = OUT / s / "tckgen" / TRACT
    raw = tdir / f"{TRACT}_{CUTOFF}.tck"
    out = tdir / f"{TRACT}_{CUTOFF}_cleaned.tck"
    if not out.exists():
        continue
    reference = PROJECT / "dwi" / s / "nodif_brain_mask.nii.gz"
    lengths = length(load(out, reference).streamlines)
    n_raw = len(load(raw, reference).streamlines) if raw.exists() else float("nan")
    # Streamline_count and Mean_length_mm feed the Step 9 models; the other two are QC only.
    rows.append({
        "Subject": s,
        "Streamline_count": len(lengths),
        "Mean_length_mm": round(float(lengths.mean()), 3) if len(lengths) else float("nan"),
        "Count_uncleaned": n_raw,
        "Retention_pct": round(100 * len(lengths) / n_raw, 1) if n_raw else float("nan"),
    })

table = OUT / "nodewise" / f"{TRACT}_tract_stats.csv"
table.parent.mkdir(parents=True, exist_ok=True)
pd.DataFrame(rows).to_csv(table, index=False)
print(f"\n{len(rows)} of {len(SUBJECTS)} participants have a cleaned bundle")
print(f"covariate table -> {table}")
```

</details>
<!-- /script:06_clean_bundles.py -->

## Retention

With the thresholds in Table 1, cleaning typically retains 25% to 60% of streamlines, several hundred per participant. Figures 1 and 2 present the comparison referred to in Step 4: the cleaned 0.01 bundle is more compact than the uncleaned 0.06 bundle, with length standard deviations of approximately 3.5 to 4.5 mm for cleaned bundles against 5 to 7 mm for either uncleaned condition.

**Figure 1**

*Effect of Cutoff and Cleaning on One Bundle*

![Three-way comparison of cutoff and cleaning](/img/fig_cleaning_comparison.png)

*Note.* Left: cutoff 0.06, uncleaned (1,000 streamlines). Middle: cutoff 0.01, uncleaned (2,500). Right: cutoff 0.01, cleaned (824). One participant, left posterior VTA → hippocampus. VTA = ventral tegmental area.

**Figure 2**

*Standard Deviation of Streamline Length by Condition Across the Five Pilot Participants*

![Length standard deviation by condition](/img/fig_cleaning_length_sd.png)

*Note.* Bars are grouped by pilot participant and hemisphere. Cleaned 0.01 in green.

## Tracts with two bundles

Some tracts reconstruct as two distinct bundles rather than a single bundle with outliers. VTA → hippocampus has a ventral secondary bundle in a subset of participants, and hippocampus → accumbens frequently produces two bundles. Mahalanobis cleaning applied to such a mixture retains the wrong bundle or a blend. The procedure used during atlas construction clusters the streamlines with QuickBundles (Garyfallidis et al., 2012; threshold 5 mm, streamlines resampled to 100 points), cleans the two largest clusters separately, and retains the anatomically correct one after inspection. Setting `QB_SPLIT = True` in the script produces `_cluster1_cleaned.tck` and `_cluster2_cleaned.tck` per participant. The correct cluster is copied to `<tract>_<cutoff>_cleaned.tck` and the script is run again to rebuild the covariate table; the selection should be recorded per participant in the manifest. In the example dataset the corridor and cleaning were sufficient for VTA → hippocampus and the division was not required.

## Verification

The cleaned file must exist and contain more than zero streamlines for every participant. Counts before and after cleaning and the retention percentage are reported; retention below 15% or above 80% warrants inspection. The script also writes `$OUT/nodewise/<tract>_tract_stats.csv`, which holds the streamline count and mean length of each cleaned bundle (`Streamline_count`, `Mean_length_mm`). Both index reconstruction quality, vary across participants, and are entered as covariates in Step 9.
