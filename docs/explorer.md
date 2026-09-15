---
sidebar_position: 4
title: "Explorer"
---

# Node-wise Tract Explorer

The Node-wise Tract Explorer is a browser-based viewer for node-wise statistical results distributed with this site. Whole-tract and quartile results are tabular and do not require it. It reads a results file in the browser, without uploading it, and presents each analysis as a table row that expands to show the node-wise *t*-value profile, the clusters identified, and, where both hemispheres are present, a left–right comparison.

**[Open the Explorer](pathname:///MesoConnect-Tutorial/explorer/)** · [sample file](pathname:///MesoConnect-Tutorial/explorer/sample_results.csv) · [example dataset](pathname:///MesoConnect-Tutorial/explorer/example_results_long.csv)

## Input format

The input is a long-format CSV with one row per node. Six columns are required: `outcome`, `tract`, `metric`, `node`, `t` and `p`. Optional columns are `hemisphere` (L or R), `N`, `covariates`, `extent_threshold`, `cluster_p` and `passed`. Any additional column is treated as a grouping variable and becomes a filter. The column names produced by `permutation_one.R` (`Node`, `t_value`, `p_value`) are accepted without renaming. The helper script in step 9 produces this file from the permutation outputs.

## Derived quantities

From the node rows the viewer derives the number of significant nodes, clusters (contiguous runs with *p* < .05), the largest cluster, which clusters exceed the extent threshold, and, when a hemisphere column is present, the counts of significant nodes per hemisphere and their overlap.

## Display

Selecting a row shows the *t*-value profile with a labelled axis and reference lines at ±2, significant nodes highlighted, retained clusters shaded, and a cluster table. For lateralized data the left and right profiles are drawn on a common axis so that both hemispheres' full *t*-value profiles are visible. The hemisphere panel is descriptive: it reports the number of significant nodes per side and their overlap and does not constitute a test of lateralization.

Page labels may be supplied in the URL (`?title=…&method=Freedman–Lane&node0=VTA&node1=hippocampus&n_perms=5000`), and `?data=URL` loads a hosted file directly.
