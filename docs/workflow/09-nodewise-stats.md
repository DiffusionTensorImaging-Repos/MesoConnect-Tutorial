---
sidebar_position: 10
title: "9. Group-level inference"
---

# Step 9. Group-level inference

Along-tract data can be analysed at three spatial resolutions: the whole tract, quartiles of the tract, and individual nodes (Table 1). The three address different questions, and no single resolution is appropriate for every study. The resolution, or combination of resolutions, should be specified before results are examined, and the same covariates should be used throughout.

**Table 1.** *Three resolutions for along-tract inference.*

| Resolution | Unit of analysis | Question | Correction | Script |
|---|---|---|---|---|
| Whole tract | Metric averaged across nodes; one value per participant per tract | Is the metric associated with the outcome; does the association differ between subregional tracts | None within tract; across outcomes as pre-specified | `final_models.py` |
| Quartiles | Metric averaged within nodes 0–24, 25–49, 50–74, 75–99 | Does the association vary along the tract; is it confined to a segment | FDR or maximum-statistic permutation across the four quartiles | `final_models.py` |
| Nodes | Metric at each of 100 nodes | Where along the tract is the association located | Cluster-extent family-wise error by permutation | `permutation_one.R` |

## Whole-tract model

The metric is averaged across all 100 nodes, or across the retained range if end nodes are trimmed, and regressed on the outcome and covariates. When two subregional tracts share most of their course (posterior and anterior VTA → hippocampus), both are entered in one mixed model with a subregion term, two rows per participant, a random intercept for participant, and each row carrying its own streamline length and count. The metric × subregion interaction is tested by likelihood ratio; when it does not improve fit, the main effect is reported. This resolution has the greatest power when the effect is distributed along the tract, and it does not localize the effect.

## Quartile model

The same model is fitted with the metric averaged within each quartile. Because adjacent quartiles are correlated, correction across the four should either use the false discovery rate or a maximum-statistic permutation that preserves their dependence. Uniformity along the tract is tested directly by contrasting the seed-end quartile against the target-end quartile with the mean and the difference entered together: when the mean carries the effect and the difference does not differ from zero, the effect is diffuse rather than localized.

## Node-wise model

At each node the outcome is regressed on the node's metric and the covariates, and the fit is compared with a reduced model omitting the metric.

```r
full    ~ metric_node + ICV + tract_length + streamline_count + motion + age
reduced ~               ICV + tract_length + streamline_count + motion + age
```

The observed *t* statistic at each node is evaluated against a Freedman–Lane permutation distribution (Freedman & Lane, 1983; Winkler et al., 2014): the residuals of the reduced model are permuted, all 100 nodes are refitted, and the procedure is repeated 5,000 times. Adjacent nodes with *p* < .05 form clusters, and a cluster is retained when its extent equals or exceeds the 95th percentile of the null distribution of maximum cluster extent. Outputs per analysis are `_nodewise.csv` (node, estimate, *t*, *p*), `_clusters.csv` and `_summary.csv`; each call requires a few minutes on one core.

This resolution localizes an effect along the tract. Its limitation is that cluster-extent correction detects contiguous runs of supra-threshold nodes; when an effect is uniform along the tract, per-node *t* statistics remain near threshold at every node and the outcome becomes sensitive to small changes in model specification. In that situation node-wise results are descriptive and the whole-tract or quartile model carries the inference.

## Covariates

Covariates comprise intracranial volume, mean streamline length and streamline count for the tract, absolute head motion and age. Length and count are tract-specific and index reconstruction quality. Streamline count can be strongly correlated with the metric under test (up to *r* = .80 with NDI in the example dataset), which reduces the residual variance available to the test. Its inclusion should be decided in advance and both specifications reported.

## Choosing a resolution

A hypothesis about a particular segment of a pathway calls for the quartile or node-wise model. A hypothesis about the pathway as a whole calls for the whole-tract model. Exploratory work is often best served by the whole-tract model for inference with the node-wise profile reported as description. Tests across several metrics, tracts and outcomes accumulate rapidly at any resolution; fixing the analytic hierarchy in advance (primary metric, primary outcome family) is more readily justified than correcting across all tests afterwards.

In the example dataset, three social-memory measures were associated with NDI in the whole-tract model with no subregion interaction. In the quartile model one of them (positivity bias in false memories) was significant in all four quartiles and the seed-end versus target-end contrast was null for all three, indicating uniform effects. Node-wise clusters were located at nodes 27 to 55 and changed with covariate specification. The results were therefore reported with the whole-tract model as primary, the quartile model as confirmation of uniformity, and node-wise profiles as description. The script [`final_models.py`](pathname:///MesoConnect-Tutorial/scripts/final_models.py) reproduces the whole-tract and quartile analyses for that dataset.

## Preparing node-wise results for the Explorer

Node-wise outputs are stacked into a single long-format file for the Node-wise Tract Explorer, the browser-based viewer described in the [Explorer section](../explorer).

```bash
python 09_stack_for_explorer.py /path/to/permutation/results   # writes results_long.csv
```

The file contains one row per node with the columns `outcome, tract, metric, node, t, p`, together with `hemisphere, N, covariates, extent_threshold, cluster_p` and `passed`.
