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
<summary>Script <code>06_clean_bundles.py</code> (278 lines)</summary>

```python title="06_clean_bundles.py"
#!/usr/bin/env python3
"""Step 6. Bundle cleaning (pyAFQ) and the cleaned-bundle covariate table.

What it does
    Takes the raw corridor tractogram that Step 5 wrote for each participant, drops the
    streamlines that stray from the bundle core or run unusually long, and saves what
    is left as the cleaned bundle.  It then rebuilds one CSV holding the streamline
    count and mean length of every cleaned bundle; those two numbers are the
    reconstruction-quality covariates in the Step 9 models.

Run in a shell where 00_config.sh has been sourced:

    source 00_config.sh
    python 06_clean_bundles.py

    Needs pyAFQ and DIPY importable in that Python (see the Step 6 page for the zipp
    hiccup on older systems).  Participants run one after another.  No timing was
    recorded, but there is no MRtrix call here, only pyAFQ on 2,500 streamlines, so
    expect minutes for a full sample, not the hours Step 5 takes.  A participant whose
    cleaned bundle already exists is skipped; FORCE=1 in the shell redoes them.  The
    thresholds live in this file, not 00_config.sh.

Inputs (must exist before running)
    $OUT/<subj>/tckgen/<TRACT>/<TRACT>_<CUTOFF>.tck   raw tractogram from Step 5
    $PROJECT/dwi/<subj>/nodif_brain_mask.nii.gz       reference grid for loading the .tck
    $SUBJECTS_FILE                                    one participant ID per line

Each tractogram from Step 5 is cleaned with AFQ.recognition.cleaning.clean_bundle:
streamlines are resampled to 100 points, and those farther than DISTANCE_SD from
the bundle core (Mahalanobis distance), or longer than the mean length by more than
LENGTH_SD, are removed, for up to CLEAN_ROUNDS iterations.

Some tracts reconstruct as two distinct bundles in a subset of participants.
With QB_SPLIT = True the tractogram is first divided with QuickBundles, the two
largest clusters are cleaned separately, and the anatomically correct cluster is
chosen by inspection and copied to <TRACT>_<CUTOFF>_cleaned.tck.  Rerun the
script afterwards to rebuild the covariate table.

Outputs
    $OUT/<subj>/tckgen/<TRACT>/<TRACT>_<CUTOFF>_cleaned.tck
        Step 7 draws this as a tract-density overlay; Step 8 profiles FA/NODDI along it.
    $OUT/nodewise/<TRACT>_tract_stats.csv
        Subject, Streamline_count, Mean_length_mm (cleaned bundle; model covariates),
        Count_uncleaned, Retention_pct
        Step 8b merges Streamline_count and Mean_length_mm into the analysis file that
        the Step 9 models read (they are listed in COVARIATES in 00_config.sh).

How to tell it worked
    One "<raw> -> <clean> streamlines (xx% retained)" line per participant, then
    "N of N participants have a cleaned bundle".  On the example dataset retention was
    26-58%; anything under 15% or over 80% is worth opening in a viewer.  A SKIP line
    is a participant Step 5 never finished (or whose tractogram is empty), and the
    final count should equal the participant total minus the SKIP lines.
"""
import inspect   # used once, to ask the installed clean_bundle whether it takes core_only
import os
import sys
from pathlib import Path

import pandas as pd
# clean_bundle moved between pyAFQ releases.  Try the current location first and fall
# back to the old one, so the same script runs against either install.
try:
    from AFQ.recognition.cleaning import clean_bundle
except ImportError:                       # pyAFQ 1.3.2 and earlier
    from AFQ.segmentation import clean_bundle
# DIPY handles the file I/O and the geometry.  A StatefulTractogram is a set of
# streamlines plus the reference image grid they sit in; that is what lets DIPY move
# between mm and voxel coordinates without guessing.
from dipy.io.stateful_tractogram import StatefulTractogram
from dipy.io.streamline import load_tractogram, save_tractogram
# These three are only used on the QB_SPLIT = True path.
from dipy.segment.clustering import QuickBundles
from dipy.segment.featurespeed import ResampleFeature
from dipy.segment.metricspeed import AveragePointwiseEuclideanMetric
from dipy.tracking.streamline import length   # per-streamline length, for the table


# Fetch one variable exported by 00_config.sh, or stop with a message that says what
# to do.  Python cannot source the config itself; it relies on the shell having
# exported everything, and a missing variable almost always means the source step
# was skipped or the config was edited without being sourced again.
def env(name):
    if name not in os.environ:
        sys.exit(f"{name} is not set: run `source 00_config.sh` first")
    return os.environ[name]


# Project settings from 00_config.sh.  Paths become Path objects so the "/" joins
# below read like the shell scripts.
PROJECT = Path(env("PROJECT"))
OUT = Path(env("OUT"))
TRACT = env("TRACT")
CUTOFF = env("CUTOFF")   # stays a string; it is only ever used in file names
# FORCE=1 in the shell means redo participants whose cleaned bundle already exists.
# Anything other than the exact string "1" counts as off.
FORCE = os.environ.get("FORCE", "0") == "1"
# str.split() with no argument splits on any run of whitespace, so this copes with
# CRLF line endings, blank lines and a missing final newline, the same as the
# read_subjects helper in 00_config.sh does for the shell scripts.
SUBJECTS = Path(env("SUBJECTS_FILE")).read_text().split()

# Cleaning settings (Table 1 on the Step 6 page).  They are not in 00_config.sh; if you
# change one, change it here and note it in the manifest.
#
# N_POINTS: each streamline is resampled to this many points before the Mahalanobis
# distance is computed, so the bundle core is a mean position at each of 100 nodes.
# It matches the 100 nodes profiled in Step 8, which is convenient but not required.
N_POINTS = 100          # resampling for the Mahalanobis distance
# CLEAN_ROUNDS: cleaning is iterative because removing outliers moves the mean and
# tightens the SD, which can expose new outliers.  pyAFQ stops early once a round
# removes nothing, so this is a ceiling, not a fixed number of passes.
CLEAN_ROUNDS = 5        # maximum cleaning iterations
# DISTANCE_SD: a streamline whose Mahalanobis distance from the core exceeds this many
# SD is dropped.  Lower is stricter (fewer, tighter streamlines); higher keeps more of
# the raw tract, outliers included.  The Table 1 set as a whole gave 26-58% retention.
DISTANCE_SD = 3         # Mahalanobis distance threshold, SD
# LENGTH_SD: drop streamlines longer than the mean by more than this many SD.  It is
# one-sided (long only): the long ones are typically loops or detours on the way to
# the target.  Short streamlines were already cut by -minlength in Step 5.
LENGTH_SD = 2           # length threshold, SD above the mean
# QB_SPLIT: leave False unless the raw tractograms clearly hold two separate bundles
# (hippocampus -> accumbens does this often; VTA -> hippocampus did not need it in
# the example data).  Mahalanobis cleaning of a two-bundle mixture keeps the wrong one
# or a blend, so the split has to come first.  See "Tracts with two bundles" on the page.
QB_SPLIT = False        # True: split into two bundles before cleaning
# QB_THRESHOLD_MM: a streamline joins an existing cluster when its distance to that
# cluster's centroid is under this; otherwise it starts a new one.  Smaller means more,
# finer clusters.  5 mm with 100-point resampling is the setting used in atlas construction.
QB_THRESHOLD_MM = 5.0   # QuickBundles distance threshold


# Keyword arguments handed to clean_bundle on every call.  stat="mean" is the centroid
# statistic: the core is the mean position at each node (Table 1 on the page).
CLEAN_ARGS = dict(n_points=N_POINTS, clean_rounds=CLEAN_ROUNDS, stat="mean",
                  distance_threshold=DISTANCE_SD, length_threshold=LENGTH_SD)
# pyAFQ 3 and later compute the distance over the middle 60% of each streamline by
# default; core_only=0 restores the full-length computation of earlier versions.
# The argument is only passed when the installed clean_bundle knows it; an older
# pyAFQ would otherwise choke on the unknown keyword.  inspect.signature reads the real
# signature at run time, so this works whichever import succeeded above.
if "core_only" in inspect.signature(clean_bundle).parameters:
    CLEAN_ARGS["core_only"] = 0


# Run clean_bundle on one StatefulTractogram and hand back the cleaned bundle as a new
# StatefulTractogram in the same space as the input.  return_idx=True makes pyAFQ
# return the indices of the streamlines it kept alongside its own cleaned tractogram;
# we discard the latter (the "_") and rebuild from the indices ourselves.
def clean(sft):
    # The cleaned bundle is rebuilt from the retained indices, so that its coordinate
    # space is that of the input under every pyAFQ version.
    # (We do not rely on which space the installed pyAFQ hands its own copy back in; a
    # .tck saved in the wrong space lands in the wrong place when Step 7 overlays it.)
    _, keep = clean_bundle(sft, return_idx=True, **CLEAN_ARGS)
    # from_sft copies the reference grid, space and origin of the input onto the subset.
    return StatefulTractogram.from_sft(sft.streamlines[keep], sft)


# Load a .tck with the participant's brain mask as the reference image.  A .tck carries
# streamline coordinates but no image grid, so DIPY needs a NIfTI from the same
# diffusion space to attach an affine and dimensions.  Any image on that grid would
# do; the mask is the one every participant is required to have (00_config.sh layout).
# bbox_valid_check=False stops DIPY refusing the file if any point maps to a voxel
# coordinate below 0 or past the last voxel.  We would rather load a streamline that
# grazes the volume edge than have the run stop on it.
def load(tck, reference):
    return load_tractogram(str(tck), str(reference), bbox_valid_check=False)


# Pass 1: clean every participant that still needs it.
for s in SUBJECTS:
    # Same layout Step 5 used: one tckgen/<TRACT> folder per participant.
    tdir = OUT / s / "tckgen" / TRACT
    raw = tdir / f"{TRACT}_{CUTOFF}.tck"
    out = tdir / f"{TRACT}_{CUTOFF}_cleaned.tck"
    reference = PROJECT / "dwi" / s / "nodif_brain_mask.nii.gz"

    # Resume logic.  No raw tractogram means Step 5 did not finish this participant
    # (Step 5 writes to a temporary name and renames at the end, so a half-written
    # file never sits at this path).  An existing cleaned bundle is skipped unless
    # FORCE=1, which is what makes an interrupted run restartable with the same command.
    if not raw.exists():
        print(f"[{s}] SKIP: no tractogram from Step 5")
        continue
    if out.exists() and not FORCE:
        print(f"[{s}] cleaned bundle exists")
        continue
    sft = load(raw, reference)
    n_raw = len(sft.streamlines)
    # Zero streamlines means Step 5 ran but nothing passed every rule (its summary lists
    # that participant with count 0 and length NA).  Nothing to clean; skip, and the
    # table at the end will simply have no row for them.
    if n_raw == 0:
        print(f"[{s}] SKIP: 0 streamlines")
        continue

    # Usual path: clean the whole tractogram as one bundle and write it out.
    # bbox_valid_check=False on save for the same reason as on load.
    if not QB_SPLIT:
        cleaned = clean(sft)
        save_tractogram(cleaned, str(out), bbox_valid_check=False)
        n_clean = len(cleaned.streamlines)
        # This retention line is what you scan after the run.  26-58% on the example
        # data; under 15% or over 80% means open this participant in a viewer.
        print(f"[{s}] {n_raw} -> {n_clean} streamlines ({100 * n_clean / n_raw:.0f}% retained)")
        continue

    # Two-bundle path (QB_SPLIT = True).  QuickBundles walks the streamlines once,
    # assigning each to the nearest cluster within QB_THRESHOLD_MM of its centroid or
    # starting a new cluster.  The metric is the average distance between matching
    # points after both streamlines are resampled to N_POINTS.  The metric itself does
    # not try the flipped order, but QuickBundles does before assigning, so a bundle
    # whose streamlines are stored in mixed directions still lands in one cluster
    # (checked on a synthetic bundle with half of it reversed; Step 8 relies on this too).
    metric = AveragePointwiseEuclideanMetric(ResampleFeature(nb_points=N_POINTS))
    clusters = QuickBundles(threshold=QB_THRESHOLD_MM, metric=metric).cluster(sft.streamlines)
    # Keep the two clusters with the most streamlines (len(cluster) is that count);
    # anything smaller is treated as stray and ignored.
    largest = sorted(clusters, key=len, reverse=True)[:2]
    # Clean each of the two on its own and save as _cluster1_ (the bigger one) and
    # _cluster2_.  cluster.indices are positions in the original tractogram, so from_sft
    # carries the space over exactly as clean() does.
    for i, cluster in enumerate(largest, start=1):
        part = StatefulTractogram.from_sft(sft.streamlines[cluster.indices], sft)
        cleaned = clean(part)
        name = f"{TRACT}_{CUTOFF}_cluster{i}_cleaned.tck"
        save_tractogram(cleaned, str(tdir / name), bbox_valid_check=False)
        print(f"[{s}] cluster {i}: {len(cluster)} -> {len(cleaned.streamlines)} streamlines")
    # Nothing is written to the _cleaned.tck name in this mode.  Look at both clusters
    # in a viewer (the Step 7 page has the mrview -tractography.load and fsleyes lines),
    # copy the anatomically right one to that name, note the choice in the manifest, and
    # rerun this script for the table.
    print(f"[{s}] inspect both clusters; copy the correct one to {out.name}")

# Covariate table from the cleaned bundles (rebuilt on every run)
# Pass 2 is a separate loop rather than rows collected in pass 1 so that the table
# also covers participants skipped above as already done, and picks up any
# _cleaned.tck copied in by hand after a QB split.
rows = []
for s in SUBJECTS:
    tdir = OUT / s / "tckgen" / TRACT
    raw = tdir / f"{TRACT}_{CUTOFF}.tck"
    out = tdir / f"{TRACT}_{CUTOFF}_cleaned.tck"
    # No cleaned bundle, no row.  Step 8b merges on Subject, so that participant simply
    # drops out of the analysis file rather than appearing with blanks.
    if not out.exists():
        continue
    reference = PROJECT / "dwi" / s / "nodif_brain_mask.nii.gz"
    # length() returns one value per streamline, in mm because load_tractogram puts
    # streamlines in RAS mm space by default.  The raw file is reloaded only to count
    # it; NaN if it has been deleted since.
    lengths = length(load(out, reference).streamlines)
    n_raw = len(load(raw, reference).streamlines) if raw.exists() else float("nan")
    rows.append({
        "Subject": s,
        # Streamline_count and Mean_length_mm are the two reconstruction-quality
        # covariates in the Step 9 models (COVARIATES in 00_config.sh).  Both index how
        # well the tract reconstructed and vary across participants, so the models
        # adjust for them rather than analyse them.
        "Streamline_count": len(lengths),
        "Mean_length_mm": round(float(lengths.mean()), 3) if len(lengths) else float("nan"),
        # QC columns only; neither enters a model.  Retention_pct is the ratio pass 1
        # printed, to one decimal, kept here so it survives in a file.
        "Count_uncleaned": n_raw,
        "Retention_pct": round(100 * len(lengths) / n_raw, 1) if n_raw else float("nan"),
    })

# Write the table next to the other node-wise inputs.  mkdir(parents=True,
# exist_ok=True) is the Python spelling of mkdir -p.  index=False keeps pandas from
# writing its row numbers as an extra unnamed first column.
table = OUT / "nodewise" / f"{TRACT}_tract_stats.csv"
table.parent.mkdir(parents=True, exist_ok=True)
pd.DataFrame(rows).to_csv(table, index=False)
# The last two lines are the summary to check: the count should equal the participant
# total minus the SKIP lines above, and the path is what Step 8b reads next.
print(f"\n{len(rows)} of {len(SUBJECTS)} participants have a cleaned bundle")
print(f"covariate table -> {table}")
```

</details>
<!-- /script:06_clean_bundles.py -->

## Retention

In the example dataset, cleaning retained 26% to 58% of streamlines (*M* = 39%), with a minimum cleaned count of 659. These values are typical for the thresholds in Table 1, and every participant retained several hundred streamlines. Figures 1 and 2 present the comparison referred to in Step 4: the cleaned 0.01 bundle is more compact than the uncleaned 0.06 bundle, with length standard deviations of approximately 3.5 to 4.5 mm for cleaned bundles against 5 to 7 mm for either uncleaned condition.

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
