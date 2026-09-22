#!/usr/bin/env python3
"""Step 8. Sample each scalar map at 100 nodes along the cleaned bundle (AFQ tract profile).

Inputs, per participant:
    $OUT/<s>/tckgen/<TRACT>/<TRACT>_<CUTOFF>_cleaned.tck   cleaned bundle (Step 6)
    $OUT/<s>/rois/<TRACT>_seed_diff.nii.gz                 seed region (Step 2); node 0 end
    $PROJECT/dwi/<s>/fa.nii.gz                             FA map
    $PROJECT/noddi/<s>/fit_*.nii.gz                        NODDI maps (Step 8a, optional)
Output: $OUT/nodewise/<TRACT>_nodewise_all_subjects.csv (long format; Step 8b pivots it)
Run:    source 00_config.sh && python 08_node_profiles.py
"""
import os
import sys
from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd
from dipy.io.image import load_nifti
from dipy.io.streamline import load_tractogram
from dipy.segment.clustering import QuickBundles
from dipy.segment.featurespeed import ResampleFeature
from dipy.segment.metricspeed import AveragePointwiseEuclideanMetric
from dipy.stats.analysis import afq_profile, gaussian_weights
from dipy.tracking.streamline import Streamlines, orient_by_streamline


# Read one variable exported by 00_config.sh, or stop with a hint.
def env(name):
    if name not in os.environ:
        sys.exit(f"{name} is not set: run `source 00_config.sh` first")
    return os.environ[name]


# TRACT and CUTOFF go into file names, so they must match what Steps 5 and 6 ran with.
PROJECT = Path(env("PROJECT"))
OUT = Path(env("OUT"))
TRACT = env("TRACT")
CUTOFF = env("CUTOFF")
# bash cannot export an array, so the ID list is re-read from the file.
SUBJECTS = Path(env("SUBJECTS_FILE")).read_text().split()

# 100 nodes is the AFQ convention; Step 9a's quartiles and Step 9c's blocks of 100 assume it.
N_NODES = 100
# A real bundle has hundreds of streamlines; a handful means tracking or cleaning failed.
MIN_STREAMLINES = 5
METRICS = {
    "FA": "dwi/{s}/fa.nii.gz",
    "NDI": "noddi/{s}/fit_NDI_modulated.nii.gz",
    "ODI": "noddi/{s}/fit_ODI_modulated.nii.gz",
    "FWF": "noddi/{s}/fit_FWF.nii.gz",
}


unavailable = [m for m, template in METRICS.items()
               if not any((PROJECT / template.format(s=s)).exists() for s in SUBJECTS)]
for m in unavailable:
    print(f"metric {m}: no image found for any participant; not profiled")
    del METRICS[m]
if not METRICS:
    sys.exit("no scalar images found")


def seed_centre_mm(s):
    """Centre of mass of the warped seed region, in scanner (mm) coordinates."""
    img = nib.load(str(OUT / s / "rois" / f"{TRACT}_seed_diff.nii.gz"))
    voxels = np.argwhere(img.get_fdata() > 0)
    return nib.affines.apply_affine(img.affine, voxels.mean(axis=0))


def orient_seed_to_target(streamlines, seed_mm):
    """Orient all streamlines alike, with node 0 at the seed end."""
    # threshold=np.inf: one cluster, so centroids[0] is the mean streamline of the whole bundle.
    metric = AveragePointwiseEuclideanMetric(ResampleFeature(nb_points=N_NODES))
    centroid = QuickBundles(threshold=np.inf, metric=metric).cluster(streamlines).centroids[0]
    # The centroid may run either way; flip it so node 0 is the seed end in every participant.
    starts_at_target = (np.linalg.norm(centroid[0] - seed_mm)
                        > np.linalg.norm(centroid[-1] - seed_mm))
    if starts_at_target:
        centroid = centroid[::-1]
    return Streamlines(orient_by_streamline(streamlines, centroid))


# Sample one scalar map along the oriented bundle; one value per node.
def profile(image, streamlines, weights):
    data, affine = load_nifti(str(image))
    return afq_profile(data, streamlines, affine, n_points=N_NODES, weights=weights)


# --- Main loop, one participant at a time ---
rows = []
for s in SUBJECTS:
    tck = OUT / s / "tckgen" / TRACT / f"{TRACT}_{CUTOFF}_cleaned.tck"
    maps = {m: PROJECT / template.format(s=s) for m, template in METRICS.items()}
    missing = [str(p) for p in [tck, *maps.values()] if not p.exists()]
    if missing:
        print(f"[{s}] SKIP: missing {missing[0]}")
        continue

    # Any map can be the grid; bbox_valid_check=False accepts points outside it, as in Step 6.
    reference = next(iter(maps.values()))
    streamlines = load_tractogram(str(tck), str(reference), bbox_valid_check=False).streamlines
    if len(streamlines) < MIN_STREAMLINES:
        print(f"[{s}] SKIP: {len(streamlines)} streamlines")
        continue

    # Orient first; the weights are per node, so node i must line up across streamlines.
    # Weights depend on geometry only, so one matrix serves every metric.
    streamlines = orient_seed_to_target(streamlines, seed_centre_mm(s))
    weights = gaussian_weights(streamlines, n_points=N_NODES)
    profiles = {m: profile(p, streamlines, weights) for m, p in maps.items()}
    for node in range(N_NODES):
        rows.append({"Subject": s, "Tract": TRACT, "Node": node,
                     **{m: float(profiles[m][node]) for m in METRICS}})
    print(f"[{s}] {len(streamlines)} streamlines, {N_NODES} nodes, {len(METRICS)} metrics")

out = OUT / "nodewise" / f"{TRACT}_nodewise_all_subjects.csv"
out.parent.mkdir(parents=True, exist_ok=True)
pd.DataFrame(rows).to_csv(out, index=False)
print(f"DONE -> {out}  ({len(rows) // N_NODES} participants)")
