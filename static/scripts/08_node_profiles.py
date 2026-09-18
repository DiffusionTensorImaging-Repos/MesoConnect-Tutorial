#!/usr/bin/env python3
"""Step 8. Along-tract profiles at 100 nodes (AFQ, Gaussian-weighted).

Run in a shell where 00_config.sh has been sourced:

    source 00_config.sh
    python 08_node_profiles.py

Streamlines are first oriented to the bundle centroid and the centroid is oriented
so that it starts at the seed region; node 0 is therefore the seed end and node 99
the target end in every participant.  At each node, every streamline's value is
weighted by the inverse of its Mahalanobis distance from the bundle core
(Yeatman et al., 2012).

METRICS maps a column name to a scalar image; add or remove entries freely.

Output: $OUT/nodewise/<TRACT>_nodewise_all_subjects.csv
        (long format: Subject, Tract, Node, one column per metric)
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


def env(name):
    if name not in os.environ:
        sys.exit(f"{name} is not set: run `source 00_config.sh` first")
    return os.environ[name]


PROJECT = Path(env("PROJECT"))
OUT = Path(env("OUT"))
TRACT = env("TRACT")
CUTOFF = env("CUTOFF")
SUBJECTS = Path(env("SUBJECTS_FILE")).read_text().split()

N_NODES = 100
MIN_STREAMLINES = 5
METRICS = {
    "FA": "dwi/{s}/fa.nii.gz",
    "NDI": "noddi/{s}/fit_NDI_modulated.nii.gz",
    "ODI": "noddi/{s}/fit_ODI_modulated.nii.gz",
    "FWF": "noddi/{s}/fit_FWF.nii.gz",
}


def seed_centre_mm(s):
    """Centre of mass of the warped seed region, in scanner (mm) coordinates."""
    img = nib.load(str(OUT / s / "rois" / f"{TRACT}_seed_diff.nii.gz"))
    voxels = np.argwhere(img.get_fdata() > 0)
    return nib.affines.apply_affine(img.affine, voxels.mean(axis=0))


def orient_seed_to_target(streamlines, seed_mm):
    """Orient all streamlines alike, with node 0 at the seed end."""
    metric = AveragePointwiseEuclideanMetric(ResampleFeature(nb_points=N_NODES))
    centroid = QuickBundles(threshold=np.inf, metric=metric).cluster(streamlines).centroids[0]
    starts_at_target = (np.linalg.norm(centroid[0] - seed_mm)
                        > np.linalg.norm(centroid[-1] - seed_mm))
    if starts_at_target:
        centroid = centroid[::-1]
    return Streamlines(orient_by_streamline(streamlines, centroid))


def profile(image, streamlines, weights):
    data, affine = load_nifti(str(image))
    return afq_profile(data, streamlines, affine, n_points=N_NODES, weights=weights)


rows = []
for s in SUBJECTS:
    tck = OUT / s / "tckgen" / TRACT / f"{TRACT}_{CUTOFF}_cleaned.tck"
    maps = {m: PROJECT / template.format(s=s) for m, template in METRICS.items()}
    missing = [str(p) for p in [tck, *maps.values()] if not p.exists()]
    if missing:
        print(f"[{s}] SKIP: missing {missing[0]}")
        continue

    reference = next(iter(maps.values()))
    streamlines = load_tractogram(str(tck), str(reference), bbox_valid_check=False).streamlines
    if len(streamlines) < MIN_STREAMLINES:
        print(f"[{s}] SKIP: {len(streamlines)} streamlines")
        continue

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
