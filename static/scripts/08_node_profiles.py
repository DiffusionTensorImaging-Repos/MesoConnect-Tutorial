#!/usr/bin/env python3
"""Step 8. Along-tract profiles at 100 nodes (AFQ, Gaussian-weighted).

Run in a shell where 00_config.sh has been sourced:

    source 00_config.sh
    python 08_node_profiles.py

What this does.  For every participant it loads the cleaned bundle from Step 6, lines
the streamlines up so they all run seed -> target, resamples each one to 100 points
(nodes) and, at every node, averages a scalar map (FA, NODDI) over the streamlines.
The result is one curve of 100 values per metric per participant: the tract profile of
Yeatman et al. (2012), computed with DIPY's afq_profile.

Streamlines are first oriented to the bundle centroid and the centroid is oriented
so that it starts at the seed region; node 0 is therefore the seed end and node 99
the target end in every participant.  At each node, every streamline's value is
weighted by the inverse of its Mahalanobis distance from the bundle core
(Yeatman et al., 2012), so a stray that survived Step 6 counts for less than the core.

METRICS maps a column name to a scalar image; add or remove entries freely.  A metric
whose image exists for no participant (for example NODDI when Step 8a was not run) is
dropped with a notice; a participant missing any remaining image is skipped.

Needs, per participant:
    $OUT/<s>/tckgen/<TRACT>/<TRACT>_<CUTOFF>_cleaned.tck   cleaned bundle (Step 6)
    $OUT/<s>/rois/<TRACT>_seed_diff.nii.gz                 seed region in diffusion space
                                                           (Step 2); says which end is 0
    $PROJECT/dwi/<s>/fa.nii.gz                             FA map (preprocessing)
    $PROJECT/noddi/<s>/fit_*.nii.gz                        NODDI maps (Step 8a, optional)

Output: $OUT/nodewise/<TRACT>_nodewise_all_subjects.csv
        (long format: Subject, Tract, Node, one column per metric)
Step 8b pivots this into one wide file per metric for the Step 9 models.

Runtime: the tutorial page quotes 20 to 40 min for 57 participants and four tracts, so
roughly 5 to 10 min for one run of this script.  There is no FORCE switch; every run
rebuilds the CSV from scratch.

What to look for.  The DONE line gives the participant count, which should equal the
number of IDs in subjects.txt minus the SKIP lines above it; the CSV then has exactly
100 x that many rows (5,700 for 57 participants).  If you run both hemispheres, check
the orientation: the across-participant correlation of node i on the left with node i
on the right is strongly positive when both sides run seed -> target and strongly
negative when one side is reversed (Step 8 page, Verification).  Nodes 0-4 and 95-99
sit in or next to gray matter and are partial-volume mixtures; whether Step 9 trims
them (--trim in 09a) is a decision to make before modelling, not after.
"""
import os
import sys
from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd
# DIPY does the real work.  load_nifti and load_tractogram read the scalar maps and the
# .tck; QuickBundles with the feature and metric classes builds the bundle centroid;
# orient_by_streamline flips streamlines to match it; gaussian_weights and afq_profile
# are DIPY's implementation of the AFQ tract profile.
from dipy.io.image import load_nifti
from dipy.io.streamline import load_tractogram
from dipy.segment.clustering import QuickBundles
from dipy.segment.featurespeed import ResampleFeature
from dipy.segment.metricspeed import AveragePointwiseEuclideanMetric
from dipy.stats.analysis import afq_profile, gaussian_weights
from dipy.tracking.streamline import Streamlines, orient_by_streamline


# Read one exported variable, or stop with a hint.  Argument: the variable name.
# Returns its value as a string.  The Python steps cannot source 00_config.sh
# themselves; they only see what "source 00_config.sh" exported into the shell that
# launched them, so a missing name almost always means the config was not sourced (or
# was sourced in a different terminal).  sys.exit with a string prints it and exits 1.
def env(name):
    if name not in os.environ:
        sys.exit(f"{name} is not set: run `source 00_config.sh` first")
    return os.environ[name]


# Values from 00_config.sh.  PROJECT holds the raw data (dwi/, noddi/); OUT is where the
# workflow writes.  TRACT and CUTOFF are spliced into file names, so they must be the
# values Steps 5 and 6 ran with or the cleaned .tck is not found and everyone is
# skipped.  CUTOFF stays a string because it only ever appears in a file name.
PROJECT = Path(env("PROJECT"))
OUT = Path(env("OUT"))
TRACT = env("TRACT")
CUTOFF = env("CUTOFF")
# bash cannot export an array, so the ID list is re-read from the file.  read_text()
# gives the whole file as one string and split() breaks it on any whitespace, so blank
# lines, CRLF endings and a missing final newline are all harmless (the same tolerance
# read_subjects has in 00_config.sh).
SUBJECTS = Path(env("SUBJECTS_FILE")).read_text().split()

# 100 nodes is the AFQ convention and the rest of the workflow is built on it: Step 9a's
# quartiles are nodes 0-24, 25-49, 50-74, 75-99 and Step 9c counts analyses in blocks
# of 100.  Change this and those two need editing as well.
N_NODES = 100
# Below this many streamlines the participant is skipped rather than profiled.  A real
# bundle has hundreds (the smallest cleaned bundle in the example dataset had 659), so a
# handful means tracking or cleaning failed, not a bundle worth a curve.  The per-node
# covariance in gaussian_weights is also estimated across streamlines, so with this few
# the weights mean little.  Why exactly 5 is not written down anywhere.
MIN_STREAMLINES = 5
# Column name -> image path under $PROJECT, with {s} standing in for the participant ID.
# Every image must be in diffusion space, where the streamlines are; the first one is
# also the reference grid when the .tck is loaded.  NDI and ODI use the modulated
# (tissue-weighted) maps from Step 8a; FWF has no modulated form.  Add a line for any
# other diffusion-space map you want profiled; the key becomes the CSV column and, via
# Step 8b, the <METRIC> in the Step 9 file names.
METRICS = {
    "FA": "dwi/{s}/fa.nii.gz",
    "NDI": "noddi/{s}/fit_NDI_modulated.nii.gz",
    "ODI": "noddi/{s}/fit_ODI_modulated.nii.gz",
    "FWF": "noddi/{s}/fit_FWF.nii.gz",
}


# Drop any metric that no participant has an image for, e.g. the three NODDI entries
# when Step 8a was never run.  any(...) over the participants stops at the first image
# it finds, so this costs almost nothing.  The list is built first because a dict cannot
# shrink while it is being iterated.  A metric that exists for only some participants
# is kept; the participants without it are skipped in the main loop.
unavailable = [m for m, template in METRICS.items()
               if not any((PROJECT / template.format(s=s)).exists() for s in SUBJECTS)]
for m in unavailable:
    print(f"metric {m}: no image found for any participant; not profiled")
    del METRICS[m]
# Not even FA was found: PROJECT is probably wrong, or fa.nii.gz is not where the layout
# in 00_config.sh expects it.
if not METRICS:
    sys.exit("no scalar images found")


# Centre of mass of the participant's warped seed region.  Argument: participant ID.
# Returns (x, y, z) in scanner mm, the same space the streamlines are loaded into
# below, so the two can be compared directly.
# get_fdata() pulls the voxel array; argwhere lists the (i, j, k) index of every
# non-zero voxel; mean(axis=0) is their centroid in voxel units; apply_affine pushes
# that through the image's voxel-to-world matrix into mm.
def seed_centre_mm(s):
    """Centre of mass of the warped seed region, in scanner (mm) coordinates."""
    img = nib.load(str(OUT / s / "rois" / f"{TRACT}_seed_diff.nii.gz"))
    voxels = np.argwhere(img.get_fdata() > 0)
    return nib.affines.apply_affine(img.affine, voxels.mean(axis=0))


# Flip streamlines so they all run seed -> target.  Arguments: the loaded streamlines
# and the seed centre from seed_centre_mm.  Returns a new Streamlines object; the input
# is left alone.
# Streamlines in a .tck may run in either direction, so without this node 0 would be
# the seed end for some streamlines and the target end for others, and the profile
# would blend the two directions.
def orient_seed_to_target(streamlines, seed_mm):
    """Orient all streamlines alike, with node 0 at the seed end."""
    # One reference streamline: the QuickBundles centroid.  ResampleFeature puts every
    # streamline on N_NODES points, AveragePointwiseEuclideanMetric compares two
    # streamlines by the mean distance between matching points, and threshold=np.inf
    # means "everything is close enough", so there is exactly one cluster and
    # .centroids[0] is its mean streamline.  QuickBundles tries each streamline both
    # ways before folding it into the running mean, so mixed directions in the file do
    # not smear the centroid (checked on a synthetic bundle with half of it reversed).
    metric = AveragePointwiseEuclideanMetric(ResampleFeature(nb_points=N_NODES))
    centroid = QuickBundles(threshold=np.inf, metric=metric).cluster(streamlines).centroids[0]
    # The centroid itself may run either way.  Compare its two ends with the seed
    # centre (np.linalg.norm is Euclidean distance) and, if the first point is the far
    # one, reverse it ([::-1] is the array backwards).  This is what makes node 0 the
    # seed end in every participant, not just "the same end within one participant".
    starts_at_target = (np.linalg.norm(centroid[0] - seed_mm)
                        > np.linalg.norm(centroid[-1] - seed_mm))
    if starts_at_target:
        centroid = centroid[::-1]
    # orient_by_streamline resamples each streamline and the centroid to 12 points,
    # sums the point-to-point distances as is and flipped, and reverses the streamline
    # when flipped is closer.  It works on a copy.  Streamlines() keeps the result as
    # the array-sequence type the DIPY calls below expect.
    return Streamlines(orient_by_streamline(streamlines, centroid))


# Sample one scalar map along the bundle.  Arguments: image path, the oriented
# streamlines, and the (n_streamlines x N_NODES) weight matrix from gaussian_weights.
# Returns a 1-D array of N_NODES values.
# load_nifti returns the voxel array and its voxel-to-world affine.  afq_profile
# resamples each streamline to n_points, reads the map at every point (the affine maps
# mm back to voxels; values are trilinearly interpolated between voxels), then averages
# across streamlines at each node with np.average and the given weights.  DIPY checks
# that the weights sum to 1 per node and raises otherwise.
def profile(image, streamlines, weights):
    data, affine = load_nifti(str(image))
    return afq_profile(data, streamlines, affine, n_points=N_NODES, weights=weights)


# Main loop, one participant at a time.  rows collects one dict per node per
# participant and becomes the CSV at the end.
rows = []
for s in SUBJECTS:
    # The cleaned bundle from Step 6.  CUTOFF is part of the name, so editing it in the
    # config after Step 5 points this at a file that does not exist.
    tck = OUT / s / "tckgen" / TRACT / f"{TRACT}_{CUTOFF}_cleaned.tck"
    # Full path of every scalar map for this participant, keyed by column name.
    maps = {m: PROJECT / template.format(s=s) for m, template in METRICS.items()}
    # The .tck and every map must exist.  [tck, *maps.values()] is one list of all the
    # paths (the * unpacks the dict values into it).  Only the first missing path is
    # printed, to keep the log readable; fix it, rerun, and see if there is another.
    missing = [str(p) for p in [tck, *maps.values()] if not p.exists()]
    if missing:
        print(f"[{s}] SKIP: missing {missing[0]}")
        continue

    # load_tractogram needs a reference image for the grid and affine.  Any of the maps
    # will do, since they all sit on the diffusion grid, so the first one is used
    # (next(iter(...)) is "the first value in the dict").  Streamlines come back in
    # scanner mm (DIPY's default space), the same units as seed_centre_mm.
    # bbox_valid_check=False: DIPY otherwise refuses a tractogram with any point outside
    # the image's bounding box; Step 6 turned the check off for these same files, so we
    # do too.  .streamlines drops the tractogram wrapper and keeps the coordinates.
    reference = next(iter(maps.values()))
    streamlines = load_tractogram(str(tck), str(reference), bbox_valid_check=False).streamlines
    # Too small to weight or to trust; see MIN_STREAMLINES above.
    if len(streamlines) < MIN_STREAMLINES:
        print(f"[{s}] SKIP: {len(streamlines)} streamlines")
        continue

    # Orientation first, then the weights: the weights are computed per node and only
    # make sense once node i is the same place along the bundle in every streamline.
    # gaussian_weights resamples to N_NODES and, at each node, takes the mean and
    # covariance of the streamline positions, computes each streamline's Mahalanobis
    # distance from that mean, and returns 1/distance normalised to sum to 1 across
    # streamlines.  Streamlines near the bundle core dominate the average; strays that
    # survived Step 6's 3 SD cut count for little.  The weights depend on geometry
    # only, so the same matrix is reused for every metric.
    streamlines = orient_seed_to_target(streamlines, seed_centre_mm(s))
    weights = gaussian_weights(streamlines, n_points=N_NODES)
    # One 100-value profile per metric, keyed by column name.
    profiles = {m: profile(p, streamlines, weights) for m, p in maps.items()}
    # Long format: one row per node with Subject, Tract and Node as keys and every
    # metric as a column.  The ** splices the metric values into the row dict; float()
    # turns each numpy scalar into a plain number.  Tract is constant within a run but
    # lets CSVs from several tracts be stacked and still told apart.
    for node in range(N_NODES):
        rows.append({"Subject": s, "Tract": TRACT, "Node": node,
                     **{m: float(profiles[m][node]) for m in METRICS}})
    print(f"[{s}] {len(streamlines)} streamlines, {N_NODES} nodes, {len(METRICS)} metrics")

# Write the table.  mkdir(parents=True, exist_ok=True) creates $OUT/nodewise if needed
# and is silent if it already exists.  index=False keeps pandas' row numbers out of the
# file.  len(rows) // N_NODES is the number of participants profiled; Step 8b reads
# this file next and pivots it to one wide row per participant.
out = OUT / "nodewise" / f"{TRACT}_nodewise_all_subjects.csv"
out.parent.mkdir(parents=True, exist_ok=True)
pd.DataFrame(rows).to_csv(out, index=False)
print(f"DONE -> {out}  ({len(rows) // N_NODES} participants)")
