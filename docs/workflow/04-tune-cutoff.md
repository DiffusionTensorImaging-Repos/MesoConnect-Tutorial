---
sidebar_position: 5
title: "4. Cutoff selection"
---

# 4. Cutoff selection on pilot subjects

The FOD amplitude cutoff determines when tracking stops. A high cutoff terminates streamlines before they reach the target; a low cutoff, without constraints, produces streamlines throughout the brain. The corridor changes this trade-off. With tracking confined to the corridor, a permissive cutoff produces well-formed bundles and uses far fewer seeds than a conservative one. This should be verified on each dataset and tract family rather than assumed. The procedure is to run a small sweep on a few subjects, tabulate the results, and inspect the reconstructions side by side.

During atlas construction at 7 T the cutoff was 0.06 for VTA → hippocampus and 0.08 for hippocampus → accumbens. The MRtrix default for FOD-based tracking is 0.05. Lower field strength produces noisier FOD estimates, so a higher cutoff (around 0.08) was expected to be necessary at 3 T. The sweep showed otherwise.

## Sweep

Five subjects, four cutoffs, reduced budgets (`-select 1000`, `-seeds 5000000`), all other parameters as in production.

```bash
bash 04_tune_cutoff.sh "s169 s4222 s4418 s606 s1000" "0.1 0.08 0.06 0.01"
```

Script: [`04_tune_cutoff.sh`](pathname:///MesoConnect-Tutorial/scripts/04_tune_cutoff.sh). It prints streamlines reached, seeds consumed and mean length for each subject and cutoff.

## Results table

Example dataset, posterior VTA → hippocampus, target 1,000 streamlines, seed limit 5 million:

| Subject | Hemi | 0.1 | 0.08 | 0.06 | 0.01 |
|---|---|---|---|---|---|
| s169 | L | 118 | 556 | 1000 | 1000 |
| s169 | R | 30 | 434 | 1000 | 1000 |
| s4222 | L | 274 | 1000 | 1000 | 1000 |
| s4222 | R | 165 | 906 | 1000 | 1000 |
| s4418 | L | 1000 | 1000 | 1000 | 1000 |
| s4418 | R | 1000 | 1000 | 1000 | 1000 |
| s606 | L | 88 | 309 | 1000 | 1000 |
| s606 | R | 731 | 1000 | 1000 | 1000 |

- 0.1: most runs exhausted the seed budget before reaching the target.
- 0.08: some subjects reached the target; one stopped at 309.
- 0.06: all runs reached the target.
- 0.01: all runs reached the target using about one fifth of the seeds (approximately 415 K versus 2.1 M or more at 0.06).

Reaching the target in every pilot subject is a necessary condition. The reconstructions also have to correspond to the tract, which is checked next.

## Side-by-side comparison

Render each cutoff's tract-density image on the same slices, one column per cutoff, and compute Dice overlap of each cutoff against the most conservative one, TDI voxel count, and mean and standard deviation of streamline length.

```bash
python 04b_compare_cutoffs.py "s169 s4222 s4418 s606 s1000" "0.1 0.08 0.06 0.01"
```

Script: [`04b_compare_cutoffs.py`](pathname:///MesoConnect-Tutorial/scripts/04b_compare_cutoffs.py). It writes one panel per subject, `cutoff_summary.csv`, and a summary chart.

0.06 (left) and 0.01 (right) for one subject, uncleaned:

![Cutoff comparison](/img/cutoff_compare_s169_l.png)

Summary across the five pilot subjects:

![Cutoff statistics](/img/cutoff_stats_comparison.png)

In the example dataset the two cutoffs traced the same arc in axial and coronal views. The 0.01 reconstruction was somewhat thicker (mean Dice 0.66 against 0.06, broader spread through the corridor). Mean lengths were similar (about 44 mm versus 47 mm) and the length SD was slightly higher at 0.01 (7 mm versus 6 mm). The cleaning step removes the outlying streamlines responsible for the extra thickness; the cleaned 0.01 bundle is tighter than the uncleaned 0.06 bundle. That comparison is on the cleaning page.

## Selection

Choose the most permissive cutoff that reaches the target in every pilot subject and whose reconstruction matches the conservative one. In the example dataset that was 0.01. Other users of the atlas have used 0.01 for VTA → accumbens. The corridor mask is what allows this; the same cutoff without an exclusion mask produces streamlines throughout the brain.

Repeat the sweep for each tract family. A cutoff chosen for VTA → hippocampus is a starting value for VTA → amygdala.

## Options that were not used

Anatomically constrained tractography (ACT) was tested during atlas construction and abandoned: the segmentation's white-matter mask was too restrictive relative to the gray-matter mask and tracts did not reconstruct. `-backtrack`, `-crop_at_gmwmi`, and custom `-angle` and `-step_size` values were left at MRtrix defaults. Add them only in response to a specific failure.
