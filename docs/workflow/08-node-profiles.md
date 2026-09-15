---
sidebar_position: 9
title: "8. Node profiles"
---

# 8. Node profiles

Each cleaned bundle is converted to a 100-point profile of a scalar map: FA from the tensor fit, NDI, ODI and FWF from NODDI, or any other map on the diffusion grid.

Two operations make profiles comparable across subjects:

1. **Orientation.** Streamlines from `tckgen` run in either direction. Each bundle is oriented against a QuickBundles centroid (`threshold=np.inf` yields one cluster) so that node 0 is the seed end and node 99 the target end. Check this once per tract by locating the endpoint features in the profile.
2. **Weighting.** `dipy.stats.analysis.afq_profile` with `gaussian_weights` weights each streamline's contribution at a node by its Mahalanobis distance from the bundle core, reducing the influence of outliers.

```python
qb = QuickBundles(threshold=np.inf, metric=AveragePointwiseEuclideanMetric(ResampleFeature(nb_points=100)))
oriented = dts.orient_by_streamline(sl, qb.cluster(sl).centroids[0])
w = dsa.gaussian_weights(oriented)
profile = dsa.afq_profile(data, oriented, affine, nb_points=100, weights=w)
```

Script: [`08_node_profiles.py`](pathname:///MesoConnect-Tutorial/scripts/08_node_profiles.py). Edit the `METRICS` dictionary to point at the scalar maps; the script writes one long CSV per tract with one column per metric. About 20 to 40 minutes for 57 subjects and four tracts.

## Node range

Nodes near the ends (0 to 4, 95 to 99) lie in or adjacent to gray matter and are affected by partial volume from the seed and target. Deep white matter spans roughly nodes 25 to 75. Whether to trim the ends should be decided before modelling.

## NODDI inputs

Fit NODDI with AMICO on the eddy-corrected data and use the modulated NDI and ODI maps (`fit_NDI_modulated.nii.gz`, `fit_ODI_modulated.nii.gz`), which include a tissue-weighted partial-volume correction. FWF has no modulated version; use `fit_FWF.nii.gz`. Settings used: `bStep=200` when converting the scheme (rounds jittered b-values), `b0_thr=100`, `doSaveModulatedMaps=True`, `doComputeRMSE=True`, `BLAS_nthreads=1`. AMICO regenerates kernels into a shared directory; when running subjects in parallel, generate kernels once on a single subject before starting the pool, otherwise concurrent jobs delete each other's files.

For NODDI sampled inside a gray-matter ROI (for example the hippocampus), refit with the gray-matter intrinsic parallel diffusivity (about 1.1e-3 mm²/s instead of the white-matter default 1.7e-3). The white-matter fit is not appropriate in gray matter and can give different results.

## Example profiles

Posterior VTA → hippocampus, one subject. FA peaks in deep white matter and decreases toward the hippocampal end:

![FA profile](/img/step27_fa_profile_s1000_posterior_l.png)

NDI, ODI and FWF for the same bundle. NDI is high near the VTA and increases again toward the hippocampus; ODI is higher at both ends where fibres fan out; FWF rises sharply at the hippocampal end near CSF:

![NDI](/img/step30_NDI_profile_s1000_posterior_l.png)
![ODI](/img/step30_ODI_profile_s1000_posterior_l.png)
![FWF](/img/step30_FWF_profile_s1000_posterior_l.png)

The anterior tract for the same subject shares the early trajectory and diverges late:

![Anterior NDI](/img/step30_NDI_profile_s1000_anterior_l.png)

## Audit

Row count per CSV should equal subjects × 100. The example dataset produced 5,700 rows per tract for every tract and metric with no skipped subjects.

## Left and right

If both hemispheres were run, confirm that the two profiles are aligned before averaging them. The correlation across subjects between node i on the left and node i on the right is strongly positive when they are aligned (about +0.98 in the example dataset) and strongly negative when one side is reversed. Mid-tract averages (nodes 25 to 74) correlated across hemispheres at roughly 0.8 to 0.9 for NDI and ODI and 0.5 for FA.
