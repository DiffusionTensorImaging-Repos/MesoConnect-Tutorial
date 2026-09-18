#!/usr/bin/env python3
"""Step 6. Bundle cleaning (pyAFQ) and the cleaned-bundle covariate table.

Run in a shell where 00_config.sh has been sourced:

    source 00_config.sh
    python 06_clean_bundles.py

Each tractogram from Step 5 is cleaned with AFQ.recognition.cleaning.clean_bundle:
streamlines are resampled to 100 points, and those farther than DISTANCE_SD from
the bundle core (Mahalanobis distance), or longer than the mean length by more than
LENGTH_SD, are removed, for up to CLEAN_ROUNDS iterations.

Some tracts reconstruct as two distinct bundles in a subset of participants.
With QB_SPLIT = True the tractogram is first divided with QuickBundles, the two
largest clusters are cleaned separately, and the anatomically correct cluster is
chosen by inspection and copied to <TRACT>_<CUTOFF>_cleaned.tck.  Rerun the
script afterwards to rebuild the covariate table.

Outputs
    $OUT/<subj>/tckgen/<TRACT>/<TRACT>_<CUTOFF>_cleaned.tck
    $OUT/nodewise/<TRACT>_tract_stats.csv
        Subject, Streamline_count, Mean_length_mm (cleaned bundle; model covariates),
        Count_uncleaned, Retention_pct
"""
import inspect
import os
import sys
from pathlib import Path

import pandas as pd
from AFQ.recognition.cleaning import clean_bundle
from dipy.io.stateful_tractogram import StatefulTractogram
from dipy.io.streamline import load_tractogram, save_tractogram
from dipy.segment.clustering import QuickBundles
from dipy.segment.featurespeed import ResampleFeature
from dipy.segment.metricspeed import AveragePointwiseEuclideanMetric
from dipy.tracking.streamline import length


def env(name):
    if name not in os.environ:
        sys.exit(f"{name} is not set: run `source 00_config.sh` first")
    return os.environ[name]


PROJECT = Path(env("PROJECT"))
OUT = Path(env("OUT"))
TRACT = env("TRACT")
CUTOFF = env("CUTOFF")
FORCE = os.environ.get("FORCE", "0") == "1"
SUBJECTS = Path(env("SUBJECTS_FILE")).read_text().split()

N_POINTS = 100          # resampling for the Mahalanobis distance
CLEAN_ROUNDS = 5        # maximum cleaning iterations
DISTANCE_SD = 3         # Mahalanobis distance threshold, SD
LENGTH_SD = 2           # length threshold, SD above the mean
QB_SPLIT = False        # True: split into two bundles before cleaning
QB_THRESHOLD_MM = 5.0   # QuickBundles distance threshold


CLEAN_ARGS = dict(n_points=N_POINTS, clean_rounds=CLEAN_ROUNDS, stat="mean",
                  distance_threshold=DISTANCE_SD, length_threshold=LENGTH_SD)
# pyAFQ 3 and later compute the distance over the middle 60% of each streamline by
# default; core_only=0 restores the full-length computation of earlier versions.
if "core_only" in inspect.signature(clean_bundle).parameters:
    CLEAN_ARGS["core_only"] = 0


def clean(sft):
    cleaned, _ = clean_bundle(sft, return_idx=True, **CLEAN_ARGS)
    return cleaned


def load(tck, reference):
    return load_tractogram(str(tck), str(reference), bbox_valid_check=False)


for s in SUBJECTS:
    tdir = OUT / s / "tckgen" / TRACT
    raw = tdir / f"{TRACT}_{CUTOFF}.tck"
    out = tdir / f"{TRACT}_{CUTOFF}_cleaned.tck"
    reference = PROJECT / "dwi" / s / "nodif_brain_mask.nii.gz"

    if not raw.exists():
        print(f"[{s}] SKIP: no tractogram from Step 5")
        continue
    if out.exists() and not FORCE:
        print(f"[{s}] cleaned bundle exists")
        continue
    sft = load(raw, reference)
    n_raw = len(sft.streamlines)
    if n_raw == 0:
        print(f"[{s}] SKIP: 0 streamlines")
        continue

    if not QB_SPLIT:
        cleaned = clean(sft)
        save_tractogram(cleaned, str(out), bbox_valid_check=False)
        n_clean = len(cleaned.streamlines)
        print(f"[{s}] {n_raw} -> {n_clean} streamlines ({100 * n_clean / n_raw:.0f}% retained)")
        continue

    metric = AveragePointwiseEuclideanMetric(ResampleFeature(nb_points=N_POINTS))
    clusters = QuickBundles(threshold=QB_THRESHOLD_MM, metric=metric).cluster(sft.streamlines)
    largest = sorted(clusters, key=len, reverse=True)[:2]
    for i, cluster in enumerate(largest, start=1):
        part = StatefulTractogram.from_sft(sft.streamlines[cluster.indices], sft)
        cleaned = clean(part)
        name = f"{TRACT}_{CUTOFF}_cluster{i}_cleaned.tck"
        save_tractogram(cleaned, str(tdir / name), bbox_valid_check=False)
        print(f"[{s}] cluster {i}: {len(cluster)} -> {len(cleaned.streamlines)} streamlines")
    print(f"[{s}] inspect both clusters; copy the correct one to {out.name}")

# Covariate table from the cleaned bundles (rebuilt on every run)
rows = []
for s in SUBJECTS:
    tdir = OUT / s / "tckgen" / TRACT
    raw = tdir / f"{TRACT}_{CUTOFF}.tck"
    out = tdir / f"{TRACT}_{CUTOFF}_cleaned.tck"
    if not out.exists():
        continue
    reference = PROJECT / "dwi" / s / "nodif_brain_mask.nii.gz"
    lengths = length(load(out, reference).streamlines)
    n_raw = len(load(raw, reference).streamlines) if raw.exists() else float("nan")
    rows.append({
        "Subject": s,
        "Streamline_count": len(lengths),
        "Mean_length_mm": round(float(lengths.mean()), 3) if len(lengths) else float("nan"),
        "Count_uncleaned": n_raw,
        "Retention_pct": round(100 * len(lengths) / n_raw, 1) if n_raw else float("nan"),
    })

table = OUT / "nodewise" / f"{TRACT}_tract_stats.csv"
table.parent.mkdir(parents=True, exist_ok=True)
pd.DataFrame(rows).to_csv(table, index=False)
print(f"\n{len(rows)} of {len(SUBJECTS)} participants have a cleaned bundle")
print(f"covariate table -> {table}")
