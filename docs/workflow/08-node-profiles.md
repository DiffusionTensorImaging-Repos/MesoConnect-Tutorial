---
sidebar_position: 9
title: "8. Node profiles"
---

# 8. Profile microstructure at 100 nodes

Each cleaned bundle becomes a 100-point profile of any scalar map: FA from the tensor, NDI, ODI and FWF from NODDI, or anything else on the diffusion grid.

Two things make the profiles comparable across subjects:

1. **Orientation.** Streamlines come out of `tckgen` running either way. Every bundle is oriented against a QuickBundles centroid (`threshold=np.inf` gives one cluster) so that node 0 is always the seed end and node 99 the target end. Check this once per tract by looking at where the profile's endpoint features fall.
2. **Weighting.** `dipy.stats.analysis.afq_profile` with `gaussian_weights` weights each streamline's contribution at a node by its Mahalanobis distance from the bundle core, so outliers count less and profiles are smoother.

```python
qb = QuickBundles(threshold=np.inf, metric=AveragePointwiseEuclideanMetric(ResampleFeature(nb_points=100)))
oriented = dts.orient_by_streamline(sl, qb.cluster(sl).centroids[0])
w = dsa.gaussian_weights(oriented)
profile = dsa.afq_profile(data, oriented, affine, nb_points=100, weights=w)
```

Script: [`08_node_profiles.py`](pathname:///MesoConnect-Tutorial/scripts/08_node_profiles.py). Edit the `METRICS` dictionary to point at your scalar maps; it writes one long CSV per tract with a column per metric. About 20 to 40 minutes for 57 subjects and four tracts.

## Which nodes to trust

Nodes near the ends (0 to 4, 95 to 99) sit in or beside gray matter and carry partial-volume contamination from the seed and target. Deep white matter is roughly nodes 25 to 75. Whether you trim the ends before modelling is a decision to make before you look at results.

## NODDI inputs

Fit NODDI with AMICO on the eddy-corrected data and use the **modulated** NDI and ODI maps (`fit_NDI_modulated.nii.gz`, `fit_ODI_modulated.nii.gz`); they carry a tissue-weighted partial-volume correction. FWF has no modulated version, and the regular `fit_FWF.nii.gz` is the right file. Settings that worked: `bStep=200` when converting the scheme (rounds jittered b-values), `b0_thr=100`, `doSaveModulatedMaps=True`, `doComputeRMSE=True`, `BLAS_nthreads=1`. AMICO regenerates kernels into a shared directory; if you run subjects in parallel, generate kernels once on a single subject before launching the pool or parallel jobs will delete each other's files.

If you also sample NODDI inside a gray-matter ROI (hippocampus, say), refit with the gray-matter intrinsic parallel diffusivity (around 1.1e-3 mm²/s rather than the white-matter default 1.7e-3). The white-matter fit is not biologically plausible in gray matter and the two can give different answers.

## What profiles look like

Posterior VTA → hippocampus, one subject. FA peaks in deep white matter and drops toward the hippocampal end:

![FA profile](/img/step27_fa_profile_s1000_posterior_l.png)

NDI, ODI and FWF for the same bundle. NDI is high near the VTA and recovers toward the hippocampus; ODI is higher at both ends where fibres fan; FWF climbs sharply at the hippocampal end near CSF:

![NDI](/img/step30_NDI_profile_s1000_posterior_l.png)
![ODI](/img/step30_ODI_profile_s1000_posterior_l.png)
![FWF](/img/step30_FWF_profile_s1000_posterior_l.png)

The anterior tract for the same subject shares the early trajectory and diverges late:

![Anterior NDI](/img/step30_NDI_profile_s1000_anterior_l.png)

## Audit

Row count per CSV should be subjects × 100. The example produced 5,700 rows per tract for every tract and metric with zero skips.

## Left and right

If you ran both hemispheres, check that the two profiles are aligned before averaging them. Correlating node i on the left with node i on the right across subjects gives a strongly positive value if they are (about +0.98 in the example); a strongly negative one means one side is flipped. Mid-tract averages (nodes 25 to 74) correlate across hemispheres at roughly 0.8 to 0.9 for NDI and ODI and 0.5 for FA.
