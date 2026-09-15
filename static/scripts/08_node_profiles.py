#!/usr/bin/env python3
"""Step 8 — 100-node tract profiles (AFQ-style, Gaussian-weighted) for any scalar map.

METRICS maps a column name to the scalar image per subject. Streamlines are oriented to a
QuickBundles centroid first so node 0 is always the seed end and node 99 the target end.
Output: one long CSV per tract — Subject, Tract, Node, <metric columns>.
"""
import os, csv
from pathlib import Path
import numpy as np
import dipy.stats.analysis as dsa, dipy.tracking.streamline as dts
from dipy.io.streamline import load_tractogram
from dipy.io.image import load_nifti
from dipy.segment.clustering import QuickBundles
from dipy.segment.metricspeed import AveragePointwiseEuclideanMetric
from dipy.segment.featurespeed import ResampleFeature

PROJECT = Path(os.environ["PROJECT"]); OUT = Path(os.environ["OUT"]); TRACT = os.environ["TRACT"]; CUTOFF = os.environ["CUTOFF"]
subjects = [l.strip() for l in open(os.environ["SUBJECTS_FILE"]) if l.strip()]
NODES, MIN_STREAMLINES = 100, 5
METRICS = {  # column -> path template; add or remove freely
    "FA":  "dwi/{s}/fa.nii.gz",
    "NDI": "noddi/{s}/fit_NDI_modulated.nii.gz",
    "ODI": "noddi/{s}/fit_ODI_modulated.nii.gz",
    "FWF": "noddi/{s}/fit_FWF.nii.gz",
}

def orient_to_centroid(sl):
    qb = QuickBundles(threshold=np.inf, metric=AveragePointwiseEuclideanMetric(ResampleFeature(nb_points=NODES)))
    return dts.Streamlines(dts.orient_by_streamline(sl, qb.cluster(sl).centroids[0]))

def profile(img, sl):
    data, aff = load_nifti(str(img)); w = dsa.gaussian_weights(sl)
    return np.asarray(dsa.afq_profile(data, sl, aff, nb_points=NODES, weights=w), float)

out_dir = OUT / "nodewise"; out_dir.mkdir(exist_ok=True)
with open(out_dir / f"{TRACT}_nodewise_all_subjects.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["Subject", "Tract", "Node"] + list(METRICS))
    for s in subjects:
        tck = OUT / s / "tckgen" / TRACT / f"{TRACT}_{CUTOFF}_cleaned.tck"
        maps = {m: PROJECT / p.format(s=s) for m, p in METRICS.items()}
        if not tck.exists() or not all(p.exists() for p in maps.values()): print(f"[{s}] SKIP missing inputs"); continue
        sl = load_tractogram(str(tck), str(next(iter(maps.values()))), bbox_valid_check=False).streamlines
        if len(sl) < MIN_STREAMLINES: print(f"[{s}] SKIP {len(sl)} streamlines"); continue
        sl = orient_to_centroid(sl); prof = {m: profile(p, sl) for m, p in maps.items()}
        for n in range(NODES): w.writerow([s, TRACT, n] + [float(prof[m][n]) for m in METRICS])
        print(f"[{s}] {NODES} nodes x {len(METRICS)} metrics")
print("DONE ->", out_dir)
