---
sidebar_position: 5
title: "4. Tune the cutoff, and look"
---

# 4. Tune the FOD cutoff on pilot subjects, and look at the result

The FOD amplitude cutoff decides when tracking stops. Too high and the tract breaks up before reaching the target; too low and, without constraints, you get streamlines everywhere. The corridor changes that trade-off completely: with tracking confined to an anatomically plausible zone, a very permissive cutoff produces clean bundles, and it does so far more efficiently than a conservative one. But that is a claim to verify on your data, not assume. This step runs a small sweep, tabulates it, and renders the results side by side so you decide with your eyes.

The atlas was built at 7 T with a cutoff of 0.06 for VTA → hippocampus and 0.08 for hippocampus → accumbens. MRtrix's default for FOD-based tracking is 0.05. Lower field strength gives noisier FODs, so the expectation going in was that 3 T would need a *higher* cutoff, around 0.08. That expectation was wrong, which is the point of testing.

## Run the sweep

Five subjects, four cutoffs, reduced budgets so it finishes in an hour or two: `-select 1000`, `-seeds 5000000`, everything else as production.

```bash
bash 04_tune_cutoff.sh "s169 s4222 s4418 s606 s1000" "0.1 0.08 0.06 0.01"
```

Script: [`04_tune_cutoff.sh`](pathname:///MesoConnect-Tutorial/scripts/04_tune_cutoff.sh). It prints streamlines reached, seeds consumed and mean length per subject and cutoff.

## Tabulate

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

- **0.1**: too strict at 3 T; most runs exhausted the seed budget short of target.
- **0.08**: inconsistent; some subjects fine, one at 309.
- **0.06**: reached target in every run.
- **0.01**: reached target in every run, using about a fifth of the seeds (roughly 415 K versus 2.1 M or more at 0.06).

A cutoff that reaches target in every pilot subject is necessary. It is not sufficient; the streamlines have to look like the tract.

## Look

Render each cutoff's tract-density image on the same slices, one column per cutoff, and put numbers on the differences: Dice overlap of each cutoff against the most conservative one, TDI voxel count, and the mean and standard deviation of streamline length.

```bash
python 04b_compare_cutoffs.py "s169 s4222 s4418 s606 s1000" "0.1 0.08 0.06 0.01"
```

Script: [`04b_compare_cutoffs.py`](pathname:///MesoConnect-Tutorial/scripts/04b_compare_cutoffs.py). Writes one panel per subject and a `cutoff_summary.csv` plus a summary chart.

0.06 (left) against 0.01 (right) for one subject, uncleaned:

![Cutoff comparison](/img/cutoff_compare_s169_l.png)

Across the five pilot subjects:

![Cutoff statistics](/img/cutoff_stats_comparison.png)

What the comparison showed in the example: the two paths are the same arc in axial and coronal views; 0.01 is a little thicker (mean Dice 0.66 against 0.06, broader spread through the corridor); mean lengths are nearly identical (about 44 mm versus 47 mm); the length SD is marginally higher at 0.01 (7 mm versus 6 mm). None of that is a problem, because cleaning in step 6 removes exactly the outlying streamlines that make the permissive cutoff look thicker, and the cleaned 0.01 bundle ends up tighter than the uncleaned 0.06 one. That comparison is shown on the cleaning page.

## Decide

Pick the most permissive cutoff that reaches target in every pilot subject and whose TDI is the same tract as the conservative one. In the example that was 0.01, which other users of the atlas have also settled on for VTA → accumbens. The corridor is what makes this safe; the same cutoff without the exclusion mask would track into everything.

Do the sweep per tract family. A cutoff chosen for VTA → hippocampus is a starting point for VTA → amygdala, not an answer.

## What not to add

Anatomically constrained tractography (ACT) was tried during atlas construction and abandoned: the tissue segmentation's white-matter mask was too tight relative to gray matter and nothing reconstructed. `-backtrack`, `-crop_at_gmwmi`, custom `-angle` and `-step_size` were left at MRtrix defaults for the same reason. Add them only if you have a specific failure they fix.
