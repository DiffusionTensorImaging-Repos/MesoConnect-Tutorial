---
sidebar_position: 7
title: "6. Bundle cleaning"
---

# Step 6. Bundle cleaning

Some streamlines within the corridor follow atypical trajectories. Cleaning is performed with `clean_bundle` from pyAFQ (Kruper et al., 2021), which implements the procedure of Yeatman et al. (2012): each streamline is resampled to 100 points, its Mahalanobis distance from the bundle's mean trajectory is computed, and streamlines exceeding a distance threshold or a length threshold are removed iteratively.

## Procedure

**Table 1.** *Cleaning parameters.*

| Parameter | Value | Meaning |
|---|---|---|
| `n_points` | 100 | Resampling prior to comparison. |
| `clean_rounds` | 5 | Maximum iterations; stops earlier when no streamlines are removed. |
| `distance_threshold` | 3 | Streamlines more than 3 SD (Mahalanobis) from the bundle centroid are removed. |
| `length_threshold` | 2 | Streamlines more than 2 SD from the mean length are removed. |
| `stat` | `mean` | Centroid statistic. |

```python
from AFQ.recognition.cleaning import clean_bundle
cleaned, keep = clean_bundle(sft, n_points=100, clean_rounds=5,
                             distance_threshold=3, length_threshold=2,
                             stat="mean", return_idx=True)
```

The corresponding script is [`06_clean_bundles.py`](pathname:///MesoConnect-Tutorial/scripts/06_clean_bundles.py). It requires pyAFQ and DIPY; on older systems `pip` may require the `zipp` package to be upgraded first.

## Retention

In the example dataset, cleaning retained 26% to 58% of streamlines (M = 39%), with a minimum cleaned count of 659. These values are typical for the thresholds in Table 1, and every participant retained several hundred streamlines. Figures 1 and 2 present the comparison referred to in step 4: the cleaned 0.01 bundle is more compact than the uncleaned 0.06 bundle, with length standard deviations of approximately 3.5 to 4.5 mm for cleaned bundles against 5 to 7 mm for either uncleaned condition.

![Three-way comparison](/img/cleaned_compare_s169_l.png)

*Figure 1.* Left: cutoff 0.06, uncleaned (1,000 streamlines). Middle: cutoff 0.01, uncleaned (2,500). Right: cutoff 0.01, cleaned (824). One participant, left posterior VTA → hippocampus.

![Cleaned statistics](/img/cleaned_stats_comparison.png)

*Figure 2.* Standard deviation of streamline length by condition across the five pilot participants; cleaned 0.01 in green.

## Tracts with two bundles

Some tracts reconstruct as two distinct bundles rather than a single bundle with outliers. VTA → hippocampus has a ventral secondary bundle in a subset of participants, and hippocampus → accumbens frequently produces two bundles. Mahalanobis cleaning applied to such a mixture retains the wrong bundle or a blend. The procedure used during atlas construction clusters the streamlines with QuickBundles (Garyfallidis et al., 2012; threshold 5 mm, streamlines resampled to 100 points), cleans the two largest clusters separately, and retains the anatomically correct one after inspection. Setting `QB_SPLIT = True` in the script produces `_qb_cluster1_cleaned.tck` and `_qb_cluster2_cleaned.tck` per participant; the selection should be recorded per participant in the manifest. In the example dataset the corridor and cleaning were sufficient for VTA → hippocampus and the division was not required.

## Verification

The cleaned file must exist and contain more than zero streamlines for every participant. Counts before and after cleaning and the retention percentage are reported; retention below 15% or above 80% warrants inspection.
