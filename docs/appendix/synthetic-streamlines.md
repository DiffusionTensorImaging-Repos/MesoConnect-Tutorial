---
sidebar_position: 2
title: "Atlas-guided synthetic streamlines"
---

# Atlas-guided synthetic streamlines

This approach is intended for studies that require along-tract profiles but cannot reconstruct the tract in every participant. The warped atlas serves as a geometric scaffold: an ordered centerline is estimated from one endpoint to the other within the mask, 100 nodes are placed along it, jittered streamlines may be generated within the mask, and scalar maps are sampled at each node. The resulting streamlines constitute a reproducible sampling coordinate system rather than a tractography reconstruction, and the approach is less established than corridor-constrained tractography.

## Procedure

The probabilistic map is warped onto the scalar grid with linear interpolation and thresholded, at 50% for a conservative core or 25% when the core is short or discontinuous; lower thresholds require justification. The scaffold is built from the mask, the probability map, and native-space start and end regions, with node 0 assigned to the seed side and node 99 to the target side for every participant; an image of the node ordering is saved. Each scalar map is sampled at every node using pyAFQ, DIPY or a custom function, producing one row per participant, tract, metric and node in the long format read by the Explorer. Modelling proceeds as in Step 9 of the main workflow, with cluster or permutation correction.

## Reporting

Recommended language: "Atlas-guided streamline scaffolds were used to define a consistent along-tract coordinate system for node-wise sampling." The scaffold should not be described as participant-specific tractography.
