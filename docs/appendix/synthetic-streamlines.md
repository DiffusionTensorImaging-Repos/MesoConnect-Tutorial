---
sidebar_position: 2
title: "Atlas-guided synthetic streamlines"
---

# Atlas-guided synthetic streamlines

For studies that need along-tract profiles but cannot reconstruct the tract in every subject. The warped atlas becomes a geometric scaffold: estimate an ordered centerline from one endpoint to the other inside the mask, place 100 nodes along it, optionally generate jittered streamlines inside the mask, and sample scalars at each node.

These are not biological streamlines. They are a reproducible coordinate system for sampling. Reviewers unfamiliar with the approach may object, which is why it is last here.

## Steps

1. Warp the **probabilistic** map onto the scalar grid with linear interpolation.
2. Threshold to taste: 50% for a conservative core, 25% if the core is too short or breaks. Avoid going lower without a reason.
3. Build the scaffold from the mask, the probability map, and native-space start and end ROIs. Node 0 must be the seed side and node 99 the target side, identically for every subject. Save a QA image of the node ordering.
4. Sample every scalar at every node with pyAFQ, DIPY or a small custom function. One row per subject, tract, metric and node, which is the same long format the Explorer reads.
5. Model exactly as in step 9 of the main workflow, with cluster or permutation correction.

## Reporting language

"Atlas-guided streamline scaffolds were used to define a consistent along-tract coordinate system for node-wise sampling." Do not describe the scaffold as subject-specific tractography.
