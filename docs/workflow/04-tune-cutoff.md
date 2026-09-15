---
sidebar_position: 5
title: "4. Cutoff selection"
---

# Step 4. Selection of the FOD amplitude cutoff

The FOD amplitude cutoff determines the minimum fibre orientation distribution amplitude at which tracking continues. A high cutoff terminates streamlines before they reach the target; a low cutoff, in unconstrained tracking, produces spurious streamlines. The corridor alters this trade-off. With tracking confined to the corridor, a permissive cutoff produces well-formed bundles while consuming far fewer seeds than a conservative cutoff. This behaviour should be verified for each dataset and tract family by a pilot sweep on a small number of participants, followed by tabulation and side-by-side inspection of the reconstructions.

During atlas construction at 7 T the cutoff was 0.06 for VTA → hippocampus and 0.08 for hippocampus → accumbens. The MRtrix3 default for FOD-based tracking is 0.05. Because lower field strength yields noisier FOD estimates, a higher cutoff (approximately 0.08) was anticipated for 3 T data. The pilot sweep did not support that expectation.

## Pilot sweep

The sweep uses five participants, four cutoffs and reduced budgets (`-select 1000`, `-seeds 5000000`); all other parameters match the production run.

```bash
bash 04_tune_cutoff.sh "s169 s4222 s4418 s606 s1000" "0.1 0.08 0.06 0.01"
```

The script ([`04_tune_cutoff.sh`](pathname:///MesoConnect-Tutorial/scripts/04_tune_cutoff.sh)) reports streamlines reached, seeds consumed and mean length for each participant and cutoff. Table 1 gives the streamline counts obtained in the example dataset.

**Table 1.** *Streamlines reached by cutoff in the pilot sweep (target 1,000; seed limit 5 million), posterior VTA → hippocampus.*

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

At 0.1 most runs exhausted the seed budget before reaching the target. At 0.08 some participants reached the target and one stopped at 309. At 0.06 and at 0.01 all runs reached the target; the 0.01 runs consumed approximately one fifth of the seeds (about 415,000 versus 2.1 million or more at 0.06). Reaching the target in every pilot participant is a necessary condition for a cutoff; the reconstructions must also correspond to the tract, which is assessed next.

## Side-by-side comparison

For each participant, the tract-density image at each cutoff is rendered on the same axial and coronal slices, one column per cutoff. Dice overlap of each cutoff against the most conservative one, the number of tract-density voxels, and the mean and standard deviation of streamline length are computed and summarized.

```bash
python 04b_compare_cutoffs.py "s169 s4222 s4418 s606 s1000" "0.1 0.08 0.06 0.01"
```

The script ([`04b_compare_cutoffs.py`](pathname:///MesoConnect-Tutorial/scripts/04b_compare_cutoffs.py)) writes one panel per participant, `cutoff_summary.csv`, and a summary chart.

![Cutoff comparison](/img/cutoff_compare_s169_l.png)

*Figure 1.* Tract-density images at cutoff 0.06 (left) and 0.01 (right) for one participant, uncleaned, left posterior VTA → hippocampus.

![Cutoff statistics](/img/cutoff_stats_comparison.png)

*Figure 2.* Summary statistics across the five pilot participants by cutoff.

In the example dataset the two cutoffs traced the same trajectory in both views. The 0.01 reconstruction was somewhat thicker (mean Dice = 0.66 against 0.06), mean lengths were similar (approximately 44 versus 47 mm), and the length standard deviation was slightly greater at 0.01 (7 versus 6 mm). Bundle cleaning (step 6) removes the outlying streamlines responsible for the additional thickness; the cleaned 0.01 bundle is more compact than the uncleaned 0.06 bundle, as shown on that page.

## Selection criterion

The cutoff selected is the most permissive value that reaches the streamline target in every pilot participant and whose reconstruction matches the conservative reconstruction. In the example dataset this was 0.01. Other users of the atlas have used 0.01 for VTA → accumbens. The corridor mask is the condition that makes this value usable; the same cutoff without an exclusion mask produces streamlines throughout the brain. The sweep should be repeated for each tract family, since a cutoff selected for VTA → hippocampus is only a starting value for other pathways.

## Options not used

Anatomically constrained tractography was evaluated during atlas construction and abandoned because the tissue segmentation's white-matter mask was too restrictive relative to the gray-matter mask and tracts did not reconstruct. The `-backtrack` and `-crop_at_gmwmi` options and custom `-angle` and `-step_size` values were left at MRtrix3 defaults. These options should be introduced only in response to a specific, observed failure.
