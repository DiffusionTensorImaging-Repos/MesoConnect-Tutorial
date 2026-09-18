---
sidebar_position: 5
title: "Suggested methods text"
---

# Suggested methods text

The paragraphs below describe the corridor workflow in the form required for a Method section and may be adapted. Values in square brackets are study-specific and should be replaced with the values used; values stated without brackets are those of the workflow as documented here.

The whole tutorial is also available as a single document, with tables and figures numbered S1, S2 and so on and the scripts in an appendix: [PDF](pathname:///MesoConnect-Tutorial/supplement/MesoConnect_Supplementary_Methods.pdf) and [Word](pathname:///MesoConnect-Tutorial/supplement/MesoConnect_Supplementary_Methods.docx).

## Tractography

Mesolimbic pathways were reconstructed in each participant using the MesoConnect Atlas as an anatomical constraint on participant-level tractography. For each pathway, the seed region, the target region and the atlas's 50% group-overlap map were transformed from Montreal Neurological Institute (MNI) space to each participant's T1-weighted image using symmetric diffeomorphic registration (ANTs; Avants et al., 2008) and then to diffusion space using the affine transform estimated during preprocessing, with nearest-neighbour interpolation. The warped atlas was dilated by [two] voxels and combined with the seed and target regions to define an inclusion zone; its inverse served as the sole exclusion mask. Fibre orientation distributions were estimated with multi-shell multi-tissue constrained spherical deconvolution (Jeurissen et al., 2014) using group-averaged response functions (Dhollander et al., 2016) and intensity normalisation in MRtrix3 (Tournier et al., 2019). Probabilistic tractography (iFOD2; Tournier et al., 2010) was seeded unidirectionally from the seed region, required to enter the target region, and terminated on entry, with [2,500] streamlines selected from a maximum of [25 million] seeds, a fibre orientation distribution amplitude cutoff of [0.01], and length bounds of [35] to [65] mm. The cutoff was selected from a pilot sweep in [five] participants as the most permissive value that reached the streamline target in every pilot participant and reproduced the trajectory obtained at the most conservative cutoff.

## Bundle cleaning and quality control

Streamlines were resampled to 100 points and cleaned with pyAFQ (Kruper et al., 2021; Yeatman et al., 2012) by iteratively removing streamlines more than 3 *SD* (Mahalanobis distance) from the bundle centroid or longer than the mean length by more than 2 *SD*, for up to five iterations. [Where a tract reconstructed as two distinct bundles, streamlines were first clustered with QuickBundles (Garyfallidis et al., 2012; 5 mm threshold), each cluster was cleaned separately, and the anatomically correct cluster was retained after inspection.] Every cleaned bundle was inspected as a tract-density overlay on the mean *b* = 0 image; bundles with fewer than 50 or more than 5,000 tract-density voxels, or a maximum density below 5 streamlines per voxel, were flagged for review. [*n*] participants were excluded at this stage.

## Along-tract profiles

Each cleaned bundle was oriented from seed to target against its QuickBundles centroid and sampled at 100 equidistant nodes using Gaussian-weighted tract profiling (Yeatman et al., 2012) as implemented in DIPY (Garyfallidis et al., 2014). [Fractional anisotropy was taken from the diffusion tensor fit. Neurite density index, orientation dispersion index and free-water fraction were obtained from NODDI (Zhang et al., 2012) fitted with AMICO (Daducci et al., 2015), using tissue-weighted modulated maps for neurite density and orientation dispersion (Parker et al., 2021).] Streamline count and mean streamline length were recorded for each bundle as indices of reconstruction quality.

## Statistical analysis

[Whole tract: The metric was averaged across nodes and related to the outcome in a linear model (or, for subregional tracts sharing most of their course, a mixed model with a subregion term and a random intercept for participant, in which the outcome × subregion interaction was tested by likelihood ratio).] [Quartiles: The metric was averaged within nodes 0–24, 25–49, 50–74 and 75–99 and the same model was fitted per quartile, with correction across quartiles by false discovery rate (or maximum-statistic permutation).] [Nodes: At each node the outcome was regressed on the metric and covariates, and node-wise *t* statistics were evaluated against a Freedman–Lane permutation distribution (Freedman & Lane, 1983; Winkler et al., 2014) with 5,000 permutations; clusters of adjacent nodes with *p* < .05 were retained when their extent reached the 95th percentile of the null distribution of maximum cluster extent.] Covariates were [intracranial volume, the mean streamline length and streamline count of the cleaned bundle, absolute head motion and age]; all variables were standardized. The resolution of analysis and the covariate set were specified before results were examined.
