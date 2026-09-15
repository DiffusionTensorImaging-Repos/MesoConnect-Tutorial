---
sidebar_position: 1
title: "Start here"
slug: /
---

# MesoConnect Atlas tutorial

The MesoConnect Atlas is a 7 Tesla probabilistic atlas of mesolimbic white-matter pathways connecting the ventral tegmental area, hippocampus, nucleus accumbens, ventral pallidum and amygdala. This site documents one way to use it: warp a tract from the atlas into a subject, dilate it into a corridor, run the subject's own tractography through that corridor, clean the result, and measure microstructure at 100 points along the bundle.

The atlas can also be warped in and averaged over, or used as a scaffold for synthetic streamlines. Both are described in the appendix. The corridor method is the recommended one because the streamlines come from the subject's data and support node-wise analysis.

## Requirements

Preprocessed diffusion data (denoised, distortion and eddy corrected, brain masked), a T1-weighted image, and a Unix shell with FSL, ANTs, MRtrix3 and Python with DIPY and pyAFQ installed. Prior tractography experience is not assumed.

## Preprocessing

Preprocessing is documented separately in the [TUBRIC DTI tutorial](https://diffusiontensorimaging-repos.github.io/TUBRIC-DTI/), which covers DICOM conversion through eddy correction, tensor fitting and registration. QSIPrep produces equivalent outputs. The corridor workflow starts from three files per subject: a skull-stripped T1, a normalized white-matter FOD image from MRtrix, and a diffusion-space brain mask. The [software page](reference/software) gives the MRtrix commands that produce the FOD image if your preprocessing ended at the tensor fit.

## Site contents

- **Atlas**: file types, tract families, ROI sources, downloads.
- **Workflow**: nine steps, each with the command, an audit that runs over every subject, and the images to inspect. Step 4 covers how to choose the tracking threshold on pilot subjects before running everyone.
- **Explorer**: a browser page that reads node-wise results as a CSV and plots profiles, clusters and the left–right comparison.
- **Alternative uses**: whole-tract extraction and atlas-guided synthetic streamlines.
- **Reference**: parameters, troubleshooting, software, scripts, citation.

## Example dataset

The numbers and figures on the workflow pages come from one dataset: 57 adults scanned at 3 T with a multi-shell protocol (b = 1000, 2000, 3250, 5000 s/mm²), processed for the posterior and anterior VTA → hippocampus tracts. The atlas itself was built from 7 T data. The example is included so that users can compare their own output against a completed run at a common field strength.
