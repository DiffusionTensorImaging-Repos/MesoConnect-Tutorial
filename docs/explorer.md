---
sidebar_position: 4
title: "Explorer"
---

# Node-wise Tract Explorer

A browser page for along-tract results. The file is parsed locally and nothing is uploaded.

**[Open the Explorer](pathname:///MesoConnect-Tutorial/explorer/)** · [sample CSV](pathname:///MesoConnect-Tutorial/explorer/sample_results.csv) · [example dataset](pathname:///MesoConnect-Tutorial/explorer/example_results_long.csv)

Input is a long-format CSV with one row per node and six required columns: `outcome, tract, metric, node, t, p`. Optional columns: `hemisphere` (L/R), `N`, `covariates`, `extent_threshold`, `cluster_p`, `passed`. Any other column becomes a filter. The column names produced by `permutation_one.R` (`Node`, `t_value`, `p_value`) are accepted without renaming.

The page derives significant-node counts, clusters (contiguous runs with p < .05), the largest cluster, which clusters exceed the extent threshold, and, when a hemisphere column is present, the left–right comparison.

Clicking a row shows the profile: a t-value plot with a labelled axis, significant nodes highlighted, retained clusters shaded, and the cluster table. For lateralized data the left and right profiles are drawn on the same axis so that both hemispheres' t-values are visible. The hemisphere panel counts significant nodes per side and marks their overlap; it is descriptive and is not a test of lateralization.

Page labels can be set in the URL: `?title=…&method=Freedman–Lane&node0=VTA&node1=hippocampus&n_perms=5000`. `?data=URL` loads a hosted CSV.
