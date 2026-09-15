---
sidebar_position: 4
title: "Explorer"
---

# Node-wise Tract Explorer

An in-browser viewer for along-tract results. Nothing is uploaded; the file is parsed locally.

**[Open the Explorer](pathname:///MesoConnect-Tutorial/explorer/)** · [sample CSV](pathname:///MesoConnect-Tutorial/explorer/sample_results.csv) · [example dataset](pathname:///MesoConnect-Tutorial/explorer/example_results_long.csv)

Give it a long-format CSV with one row per node and six required columns: `outcome, tract, metric, node, t, p`. Optional columns: `hemisphere` (L/R), `N`, `covariates`, `extent_threshold`, `cluster_p`, `passed`. Any other column becomes a filter. Column names from `permutation_one.R` output (`Node`, `t_value`, `p_value`) are recognized as they are.

Everything else is derived in the browser: significant-node counts, clusters as contiguous p < .05 runs, the largest cluster, which clusters pass the extent threshold, and, if a hemisphere column exists, the left–right comparison.

Click any row for the full profile: a t-value plot with a labelled axis, the significant nodes highlighted, passing clusters shaded, the cluster table, and, for lateralized data, the left and right profiles stacked with the same axis so you see both hemispheres' t-values, not only the significant ones. The hemisphere panel is descriptive. It counts significant nodes per side and shows where they overlap; it is not a test of lateralization.

Page labels can be set in the URL: `?title=…&method=Freedman–Lane&node0=VTA&node1=hippocampus&n_perms=5000`, and `?data=URL` loads a hosted CSV directly.
