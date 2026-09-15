---
sidebar_position: 7
title: "6. Clean the bundles"
---

# 6. Clean the bundles

Even inside the corridor some streamlines take odd routes. pyAFQ's `clean_bundle` resamples every streamline to 100 points, computes each one's Mahalanobis distance from the bundle's mean shape, and drops outliers iteratively, along with streamlines whose length is far from the mean.

| Parameter | Value | Meaning |
|---|---|---|
| `n_points` | 100 | Resample before comparison. |
| `clean_rounds` | 5 | Iterate up to five times or until nothing is removed. |
| `distance_threshold` | 3 | Drop streamlines more than 3 SD (Mahalanobis) from the bundle centroid. |
| `length_threshold` | 2 | Drop streamlines more than 2 SD from the mean length. |
| `stat` | `mean` | Centroid statistic. |

```python
from AFQ.recognition.cleaning import clean_bundle
cleaned, keep = clean_bundle(sft, n_points=100, clean_rounds=5,
                             distance_threshold=3, length_threshold=2,
                             stat="mean", return_idx=True)
```

Script: [`06_clean_bundles.py`](pathname:///MesoConnect-Tutorial/scripts/06_clean_bundles.py). Needs `pyAFQ` and `dipy`; if `pip` complains about `zipp` on an older system, upgrade it.

## What retention looks like

Example dataset: 26% to 58% of streamlines retained, mean 39%, lowest cleaned count 659. That is typical for these thresholds. Every subject kept hundreds of streamlines, which is what the corridor buys you: the raw tracts are clean enough that aggressive cleaning does not empty them.

The comparison the cutoff step promised. Left: 0.06, uncleaned (1,000 streamlines). Middle: 0.01, uncleaned (2,500). Right: 0.01, cleaned (824). The cleaned permissive bundle is tighter than the conservative one:

![Three-way comparison](/img/cleaned_compare_s169_l.png)

Length SD per condition across the pilot subjects, cleaned 0.01 in green:

![Cleaned statistics](/img/cleaned_stats_comparison.png)

Cleaned bundles land at roughly 3.5 to 4.5 mm length SD against 5 to 7 mm for either uncleaned option.

## When a tract has two bundles

Some tracts sometimes reconstruct as two distinct bundles rather than one with outliers. VTA → hippocampus has a ventral secondary bundle in a subset of subjects; hippocampus → accumbens does this often. Mahalanobis cleaning on the mixture keeps the wrong one or a blend. The fix used in atlas construction: cluster first with QuickBundles (threshold 5 mm, streamlines resampled to 100 points), clean each of the two largest clusters separately, then look at both and keep the anatomically correct one. Set `QB_SPLIT = True` in the script to get `_qb_cluster1_cleaned.tck` and `_qb_cluster2_cleaned.tck` per subject, and record which was chosen per subject in your manifest.

In the 3 T example the corridor plus cleaning was enough for VTA → hippocampus and the split was not needed.

## Audit

Cleaned file exists and has more than zero streamlines, for every subject. Print before and after counts and the retention percentage; a subject retaining under 15% or over 80% is worth a look.
