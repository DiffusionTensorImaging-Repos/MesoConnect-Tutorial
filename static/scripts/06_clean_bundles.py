#!/usr/bin/env python3
"""Step 6 — Clean each bundle with pyAFQ (Mahalanobis + length outliers).

Optional QuickBundles split: if a tract sometimes reconstructs as two distinct bundles
(a ventral secondary bundle is common for VTA-hippocampus), set QB_SPLIT=True to cluster
first, clean each cluster, and choose the correct one by visual QC.
"""
import os, sys
from pathlib import Path
from AFQ.recognition.cleaning import clean_bundle
from dipy.io.streamline import load_tractogram, save_tractogram
from dipy.segment.clustering import QuickBundles
from dipy.segment.metricspeed import AveragePointwiseEuclideanMetric
from dipy.segment.featurespeed import ResampleFeature

PROJECT = Path(os.environ["PROJECT"]); OUT = Path(os.environ["OUT"]); TRACT = os.environ["TRACT"]; CUTOFF = os.environ["CUTOFF"]
subjects = [l.strip() for l in open(os.environ["SUBJECTS_FILE"]) if l.strip()]
N_POINTS, ROUNDS, DIST_SD, LEN_SD = 100, 5, 3, 2
QB_SPLIT, QB_THRESHOLD = False, 5.0

def clean(sft):
    out, _ = clean_bundle(sft, n_points=N_POINTS, clean_rounds=ROUNDS, distance_threshold=DIST_SD,
                          length_threshold=LEN_SD, stat="mean", return_idx=True)
    return out

for s in subjects:
    tdir = OUT / s / "tckgen" / TRACT; in_tck = tdir / f"{TRACT}_{CUTOFF}.tck"
    ref = PROJECT / "dwi" / s / "nodif_brain_mask.nii.gz"
    if not in_tck.exists(): print(f"[{s}] SKIP missing {in_tck}"); continue
    if os.environ.get("FORCE","0")!="1" and (tdir / f"{TRACT}_{CUTOFF}_cleaned.tck").exists(): print(f"[{s}] cleaned file exists"); continue
    sft = load_tractogram(str(in_tck), str(ref), bbox_valid_check=False)
    n0 = len(sft.streamlines)
    if n0 == 0: print(f"[{s}] SKIP 0 streamlines"); continue
    if not QB_SPLIT:
        c = clean(sft); save_tractogram(c, str(tdir / f"{TRACT}_{CUTOFF}_cleaned.tck"), bbox_valid_check=False)
        print(f"[{s}] {n0} -> {len(c.streamlines)} ({100*len(c.streamlines)/n0:.0f}% retained)")
    else:
        qb = QuickBundles(threshold=QB_THRESHOLD, metric=AveragePointwiseEuclideanMetric(ResampleFeature(nb_points=N_POINTS)))
        clusters = sorted(qb.cluster(sft.streamlines), key=len, reverse=True)[:2]
        for i, cl in enumerate(clusters, 1):
            sub = sft.__class__(sft.streamlines[cl.indices], sft, sft.space); c = clean(sub)
            save_tractogram(c, str(tdir / f"{TRACT}_{CUTOFF}_qb_cluster{i}_cleaned.tck"), bbox_valid_check=False)
            print(f"[{s}] cluster{i}: {len(cl)} -> {len(c.streamlines)}")
        print(f"[{s}] inspect both clusters and copy the anatomically correct one to {TRACT}_{CUTOFF}_cleaned.tck")
print("DONE")
