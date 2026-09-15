---
sidebar_position: 1
title: "Introduction"
slug: /
---

# Introduction

The MesoConnect Atlas is a probabilistic atlas of mesolimbic white-matter pathways derived from 7 Tesla diffusion MRI (Human Connectome Project; Vu et al., 2015). It covers connections among the ventral tegmental area (VTA), hippocampus, nucleus accumbens, ventral pallidum and amygdala. This tutorial describes how to reconstruct those pathways in new participants using the atlas as an anatomical constraint on subject-specific tractography, and how to quantify microstructure along the reconstructed bundles.

## Scope

The procedure has nine steps. The atlas map for a tract is registered to each participant and dilated into a corridor; probabilistic tractography is run through the corridor from the pathway's seed region to its target; the resulting bundle is cleaned of outlying streamlines; and scalar maps (fractional anisotropy and NODDI indices) are sampled at 100 equidistant points along the bundle. Group-level inference can be performed at three resolutions, the whole tract, quartiles of the tract, or individual nodes, and the tutorial describes the model and correction for each. Node-wise results can be inspected in the Node-wise Tract Explorer, a browser-based viewer distributed with this site that renders t-value profiles, clusters and hemispheric comparisons from a results file.

Two alternative uses of the atlas, averaging a scalar map within the warped atlas mask and sampling along an atlas-derived centerline, are described in the appendix. Corridor-constrained tractography is presented as the primary method because the streamlines are estimated from each participant's own data and support along-tract analysis.

## Prerequisites

The tutorial assumes preprocessed diffusion data (denoised, corrected for susceptibility and eddy-current distortion, brain-masked), a T1-weighted anatomical image, and a Unix environment with FSL, ANTs, MRtrix3 (Tournier et al., 2019) and Python with DIPY (Garyfallidis et al., 2014) and pyAFQ (Kruper et al., 2021). Preprocessing itself is documented in the [TUBRIC DTI tutorial](https://diffusiontensorimaging-repos.github.io/TUBRIC-DTI/). QSIPrep produces equivalent inputs. Estimation of fibre orientation distributions, which the TUBRIC pipeline does not include, is described on the [software page](reference/software).

## Organization

| Section | Contents |
|---|---|
| Atlas | File types, tract families, region-of-interest sources, downloads |
| Workflow | The nine steps, with parameters, verification criteria and results from an example dataset |
| Explorer | The results viewer and its input format |
| Alternative approaches | Whole-tract extraction; atlas-guided synthetic streamlines |
| Reference | Consolidated parameters, troubleshooting, software, scripts, citation, references |

## Example dataset

Numerical results and figures on the workflow pages are drawn from a single dataset: 57 adults scanned at 3 T with a multi-shell protocol (b = 1000, 2000, 3250 and 5000 s/mm²), processed for the posterior and anterior VTA → hippocampus pathways. The atlas was constructed at 7 T. The example dataset is included to illustrate expected output at a field strength typical of most studies.
