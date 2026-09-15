---
sidebar_position: 1
title: "Start here"
slug: /
---

# MesoConnect Atlas: corridor-guided tractography tutorial

This site shows how to use the **MesoConnect Atlas**, a 7 Tesla probabilistic atlas of mesolimbic white-matter pathways (ventral tegmental area, hippocampus, nucleus accumbens, ventral pallidum, amygdala), to reconstruct those pathways in your own subjects and measure microstructure along them.

The method it teaches is the one that holds up: warp a tract atlas into a subject, dilate it into a corridor, and run the subject's **own** tractography through that corridor. You get subject-specific streamlines that are anatomically constrained by the group atlas, then clean them, profile them at 100 nodes, and test node by node. Warping the atlas in and taking a mean inside it is faster and is covered in an appendix, but it is not what this tutorial recommends.

## Who this is for

You have preprocessed diffusion data (denoised, distortion and eddy corrected, with a brain mask) and a T1, and you want one or more of the atlas's tracts in each subject. You do not need to have run tractography before. You do need a Unix shell, FSL, ANTs, MRtrix3 and Python with DIPY and pyAFQ.

## Where preprocessing is covered

Preprocessing is not repeated here. The **[TUBRIC DTI tutorial](https://diffusiontensorimaging-repos.github.io/TUBRIC-DTI/)** takes raw DICOMs through eddy correction, tensor fitting and registration, and is the intended step zero for this site. QSIPrep produces equivalent inputs. Whichever you use, the corridor workflow starts from three things per subject: a skull-stripped T1, a normalized white-matter FOD image from MRtrix (tissue response functions, MSMT-CSD, `mtnormalise`), and a diffusion-space brain mask. The [software page](reference/software) lists exact commands for the FOD steps if your preprocessing stopped at the tensor.

## How the site is organized

- **Atlas**: what the files are, which tract families exist, what the ROIs are made from, and downloads.
- **Workflow**: the nine steps, each with the command, an audit that checks every subject, and what to look at. Step 4 is the one people skip and should not: it shows how to sweep the tracking threshold on a few subjects and look at the results before committing.
- **Explorer**: a browser tool that takes your node-wise results as a CSV and draws the profiles, clusters and hemisphere comparison.
- **Appendices**: whole-tract extraction and atlas-guided synthetic streamlines, in the order of how defensible they are.
- **Reference**: every parameter in one table, troubleshooting, software, downloadable scripts, citation.

## The worked example

Numbers and figures throughout come from one dataset: 57 adults scanned at 3 T with a multi-shell protocol (b = 1000, 2000, 3250, 5000), run for the **VTA → hippocampus** tracts (posterior and anterior). Every step reports what that dataset produced so you can judge whether yours looks similar. The atlas was built at 7 T; the example shows the workflow transferring to ordinary 3 T data, which is the case most users are in.
