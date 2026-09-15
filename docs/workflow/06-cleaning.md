---
sidebar_position: 7
title: "6. Bundle cleaning"
---

# 6. Bundle cleaning

Some streamlines inside the corridor follow atypical routes. pyAFQ's `clean_bundle` resamples each streamline to 100 points, computes its Mahalanobis distance from the bundle's mean shape, and removes outliers iteratively, together with streamlines whose length is far from the mean.

| Parameter | Value | Meaning |
|---|---|---|
| `n_points` | 100 | Resampling before comparison. |
| `clean_rounds` | 5 | Iterate up to five times or until no streamlines are removed. |
| `distance_threshold` | 3 | Remove streamlines more than 3 SD (Mahalanobis) from the bundle centroid. |
| `length_threshold` | 2 | Remove streamlines more than 2 SD from the mean length. |
| `stat` | `mean` | Centroid statistic. |

```python
from AFQ.recognition.cleaning import clean_bundle
cleaned, keep = clean_bundle(sft, n_points=100, clean_rounds=5,
                             distance_threshold=3, length_threshold=2,
                             stat="mean", return_idx=True)
```

Script: [`06_clean_bundles.py`](pathname:///MesoConnect-Tutorial/scripts/06_clean_bundles.py). Requires `pyAFQ` and `dipy`. On older systems `pip` may require `zipp` to be upgraded first.

## Retention

Example dataset: 26% to 58% of streamlines retained, mean 39%, lowest cleaned count 659. These values are typical for the thresholds above. Every subject retained several hundred streamlines.

The comparison referred to on the cutoff page. Left: 0.06, uncleaned (1,000 streamlines). Middle: 0.01, uncleaned (2,500). Right: 0.01, cleaned (824). The cleaned 0.01 bundle is more compact than the uncleaned 0.06 bundle:

![Three-way comparison](/img/cleaned_compare_s169_l.png)

Length SD per condition across the pilot subjects, cleaned 0.01 in green:

![Cleaned statistics](/img/cleaned_stats_comparison.png)

Cleaned bundles had a length SD of roughly 3.5 to 4.5 mm; both uncleaned options had 5 to 7 mm.

## Tracts with two bundles

Some tracts reconstruct as two distinct bundles rather than one bundle with outliers. VTA → hippocampus has a ventral secondary bundle in a subset of subjects; hippocampus → accumbens frequently produces two. Mahalanobis cleaning applied to the mixture retains the wrong bundle or a blend. The procedure used in atlas construction: cluster with QuickBundles (threshold 5 mm, streamlines resampled to 100 points), clean the two largest clusters separately, inspect both, and keep the anatomically correct one. Set `QB_SPLIT = True` in the script to write `_qb_cluster1_cleaned.tck` and `_qb_cluster2_cleaned.tck` per subject, and record the selection per subject in the manifest.

In the 3 T example dataset the corridor and cleaning were sufficient for VTA → hippocampus and the split was not used.

## Audit

Cleaned file exists with more than zero streamlines for every subject. Print the before and after counts and the retention percentage. Retention below 15% or above 80% warrants inspection.
