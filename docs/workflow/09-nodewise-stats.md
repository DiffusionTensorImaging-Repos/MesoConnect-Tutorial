---
sidebar_position: 10
title: "9. Node-wise statistics"
---

# 9. Test node by node, then decide what you are actually claiming

## The node-wise model

At each of the 100 nodes, regress the outcome on that node's metric plus covariates, and compare against a reduced model without the metric:

```r
full    ~ metric_node + ICV + tract_length + streamline_count + motion + age
reduced ~               ICV + tract_length + streamline_count + motion + age
```

The observed t for the metric at each node is compared against a Freedman–Lane permutation null: permute the reduced model's residuals, refit all 100 nodes, repeat 5,000 times. Adjacent nodes significant at p < .05 form a cluster; a cluster survives if its extent is at least the 95th percentile of the null's maximum cluster extent. That is cluster-extent family-wise error control across the 100 nodes for one outcome, tract and metric.

Script: [`permutation_one.R`](pathname:///MesoConnect-Tutorial/scripts/permutation_one.R). One call per outcome × tract × metric; a few minutes each on one core, so run them in parallel across a node. Outputs per analysis: `_nodewise.csv` (node, estimate, t, p), `_clusters.csv`, `_summary.csv`.

Covariates: intracranial volume, mean streamline length and streamline count for that tract, absolute head motion, age. Length and count are per tract and index reconstruction quality. Be aware that streamline count can be strongly correlated with the metric you are testing (up to r = 0.8 for NDI in the example), which makes the tested residual small; decide on it before looking at results and report both ways.

## Multiple tracts and metrics

Node-wise across four metrics, two tracts and several outcomes is a lot of tests. The example dataset handled it by deciding the hierarchy before testing: NDI primary, FA as a supplement, one outcome family primary. Corrections within a hypothesis are easier to defend than corrections across everything.

## The whole-tract complement

Cluster-extent correction finds focal runs of significant nodes. When an effect is spread evenly along the tract, per-node t hovers near the threshold everywhere and the method has no headroom; the answer flips with small changes in specification. Test for that: contrast the seed-end quarter against the target-end quarter with the mean and the difference entered together. If the mean carries the effect and the difference is null, the effect is diffuse, node-wise results are descriptive, and a whole-tract model is the inferential unit.

For two subregional tracts that share most of their course (posterior and anterior VTA → hippocampus), a mixed model with both tracts stacked, a subregion term, and a memory × subregion interaction tested by likelihood ratio settles whether the subregions differ without forcing a choice between them. Quartile averages in the same model show whether an effect is uniform along the tract. Script: [`final_models.py`](pathname:///MesoConnect-Tutorial/scripts/final_models.py), which reproduces that analysis for the example dataset.

## Build the long CSV for the Explorer

```bash
python 09_stack_for_explorer.py /path/to/permutation/results   # writes results_long.csv
```

One row per node: `outcome, tract, metric, node, t, p`, plus `hemisphere, N, covariates, extent_threshold, cluster_p, passed`. Drop it into the [Explorer](../explorer).
