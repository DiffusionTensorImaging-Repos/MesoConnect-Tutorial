---
sidebar_position: 2
title: "Atlas-guided synthetic streamlines"
---

# Atlas-guided synthetic streamlines

For studies that require along-tract profiles but cannot reconstruct the tract in every subject. The warped atlas is used as a geometric scaffold: an ordered centerline is estimated from one endpoint to the other inside the mask, 100 nodes are placed along it, jittered streamlines may be generated inside the mask, and scalar maps are sampled at each node.

The resulting streamlines are a reproducible coordinate system for sampling. They are not tractography reconstructions, and the approach is less established than the corridor method.

## Steps

1. Warp the probabilistic map onto the scalar grid with linear interpolation.
2. Threshold: 50% for a conservative core, 25% if the core is short or discontinuous. Lower thresholds require a stated reason.
3. Build the scaffold from the mask, the probability map, and native-space start and end ROIs. Node 0 is the seed side and node 99 the target side for every subject. Save an image of the node ordering.
4. Sample every scalar map at every node with pyAFQ, DIPY or a custom function. Output one row per subject, tract, metric and node, the same long format the Explorer reads.
5. Model as in step 9 of the main workflow, with cluster or permutation correction.

## Reporting language

"Atlas-guided streamline scaffolds were used to define a consistent along-tract coordinate system for node-wise sampling." The scaffold should not be described as subject-specific tractography.
