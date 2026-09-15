---
sidebar_position: 9
title: "8. Node profiles"
---

# Step 8. Along-tract profiles

Each cleaned bundle is converted to a 100-point profile of a scalar map: fractional anisotropy from the tensor fit, the neurite density index (NDI), orientation dispersion index (ODI) and free-water fraction (FWF) from NODDI (Zhang et al., 2012), or any other map on the diffusion grid. Profiling follows the tract-profile approach of Yeatman et al. (2012) as implemented in DIPY (Garyfallidis et al., 2014).

Two operations make profiles comparable across participants. First, because streamlines from `tckgen` run in either direction, each bundle is oriented against a QuickBundles centroid (Garyfallidis et al., 2012; `threshold=np.inf`, yielding one cluster) so that node 0 corresponds to the seed end and node 99 to the target end. The orientation should be confirmed once per tract by locating endpoint features in the profile. Second, `afq_profile` with `gaussian_weights` weights each streamline's contribution at a node by its Mahalanobis distance from the bundle core, reducing the influence of outlying streamlines.

## Procedure

```python
qb = QuickBundles(threshold=np.inf, metric=AveragePointwiseEuclideanMetric(ResampleFeature(nb_points=100)))
oriented = dts.orient_by_streamline(sl, qb.cluster(sl).centroids[0])
w = dsa.gaussian_weights(oriented)
profile = dsa.afq_profile(data, oriented, affine, nb_points=100, weights=w)
```

The corresponding script is [`08_node_profiles.py`](pathname:///MesoConnect-Tutorial/scripts/08_node_profiles.py). The `METRICS` dictionary specifies the scalar maps; the script writes one long-format CSV per tract with one column per metric. Processing 57 participants and four tracts required 20 to 40 minutes.

## Node range

Nodes near the ends of the profile (0 to 4 and 95 to 99) lie in or adjacent to gray matter and are affected by partial-volume contamination from the seed and target regions. Deep white matter spans approximately nodes 25 to 75. Whether end nodes are trimmed should be decided before modelling.

## NODDI inputs

NODDI is fitted with AMICO (Daducci et al., 2015) on the eddy-corrected data. The modulated NDI and ODI maps (`fit_NDI_modulated.nii.gz`, `fit_ODI_modulated.nii.gz`), which incorporate the tissue-weighted partial-volume correction of Parker et al. (2021), are used for profiling; FWF has no modulated form and `fit_FWF.nii.gz` is used. Settings used in the example dataset were `bStep=200` during scheme conversion (rounding jittered b-values), `b0_thr=100`, `doSaveModulatedMaps=True`, `doComputeRMSE=True` and `BLAS_nthreads=1`. AMICO regenerates its kernels in a shared directory; when participants are fitted in parallel, kernels should be generated once on a single participant before the pool is started, otherwise concurrent jobs delete one another's files.

When NODDI is sampled within a gray-matter region (for example the hippocampus), the model should be refitted with the gray-matter intrinsic parallel diffusivity (approximately 1.1 × 10⁻³ mm²/s rather than the white-matter default of 1.7 × 10⁻³). The white-matter fit is not appropriate in gray matter and the two fits can yield different results.

## Example profiles

![FA profile](/img/step27_fa_profile_s1000_posterior_l.png)

*Figure 1.* Fractional anisotropy along the left posterior VTA → hippocampus tract, one participant. FA peaks in deep white matter and declines toward the hippocampal end.

![NDI](/img/step30_NDI_profile_s1000_posterior_l.png)
![ODI](/img/step30_ODI_profile_s1000_posterior_l.png)
![FWF](/img/step30_FWF_profile_s1000_posterior_l.png)

*Figure 2.* NDI (top), ODI (middle) and FWF (bottom) for the same bundle. NDI is high near the VTA and increases again toward the hippocampus; ODI is higher at both ends where fibres fan; FWF rises sharply at the hippocampal end adjacent to cerebrospinal fluid.

![Anterior NDI](/img/step30_NDI_profile_s1000_anterior_l.png)

*Figure 3.* NDI along the anterior tract for the same participant, sharing the early trajectory and diverging late.

## Verification

The row count of each CSV should equal the number of participants × 100. In the example dataset every tract and metric produced 5,700 rows with no skipped participants.

When both hemispheres are processed, alignment should be confirmed before averaging. The across-participant correlation between node *i* on the left and node *i* on the right is strongly positive when the profiles are aligned (approximately +.98 in the example dataset) and strongly negative when one side is reversed. Mid-tract averages (nodes 25 to 74) correlated across hemispheres at approximately .8 to .9 for NDI and ODI and .5 for FA.
