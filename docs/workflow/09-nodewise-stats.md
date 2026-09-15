---
sidebar_position: 10
title: "9. Node-wise statistics"
---

# 9. Node-wise statistics

## Node-wise model

At each of the 100 nodes, regress the outcome on that node's metric and the covariates, and compare against a reduced model without the metric:

```r
full    ~ metric_node + ICV + tract_length + streamline_count + motion + age
reduced ~               ICV + tract_length + streamline_count + motion + age
```

The observed t statistic for the metric at each node is compared against a Freedman–Lane permutation null: permute the reduced model's residuals, refit all 100 nodes, repeat 5,000 times. Adjacent nodes with p < .05 form a cluster; a cluster is retained if its extent is at least the 95th percentile of the null distribution of the maximum cluster extent. This provides cluster-extent family-wise error control across the 100 nodes for one outcome, tract and metric.

Script: [`permutation_one.R`](pathname:///MesoConnect-Tutorial/scripts/permutation_one.R). One call per outcome × tract × metric, a few minutes each on one core; run them in parallel. Outputs per analysis: `_nodewise.csv` (node, estimate, t, p), `_clusters.csv`, `_summary.csv`.

Covariates: intracranial volume, mean streamline length and streamline count for the tract, absolute head motion, and age. Length and count are per tract and index reconstruction quality. Streamline count can be strongly correlated with the metric under test (up to r = 0.8 with NDI in the example dataset), which reduces the residual variance being tested. Decide on its inclusion before examining results and report both specifications.

## Multiple tracts and metrics

Node-wise tests across four metrics, two tracts and several outcomes accumulate quickly. The example dataset defined the hierarchy in advance: NDI as the primary metric, FA as a supplement, and one outcome family as primary. Correction within a hypothesis is easier to justify than correction across all tests.

## Whole-tract model

Cluster-extent correction detects contiguous runs of significant nodes. When an effect is distributed uniformly along the tract, per-node t statistics remain near the threshold at every node and the method is unstable with respect to small changes in specification. To test for this, contrast the seed-end quarter of the tract against the target-end quarter with the mean and the difference entered together. If the mean carries the effect and the difference does not differ from zero, the effect is diffuse; in that case node-wise results are descriptive and a whole-tract model is the inferential unit.

For two subregional tracts that share most of their course (posterior and anterior VTA → hippocampus), a mixed model with both tracts stacked, a subregion term, and a memory × subregion interaction tested by likelihood ratio determines whether the subregions differ. Quartile averages in the same model show whether an effect is uniform along the tract. Script: [`final_models.py`](pathname:///MesoConnect-Tutorial/scripts/final_models.py), which reproduces this analysis for the example dataset.

## Long CSV for the Explorer

```bash
python 09_stack_for_explorer.py /path/to/permutation/results   # writes results_long.csv
```

One row per node: `outcome, tract, metric, node, t, p`, plus `hemisphere, N, covariates, extent_threshold, cluster_p, passed`. Load it in the [Explorer](../explorer).
