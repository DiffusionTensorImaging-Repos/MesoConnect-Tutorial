#!/usr/bin/env python3
"""Step 8b. Assemble the analysis files read by the Step 9 scripts.

Run in a shell where 00_config.sh has been sourced:

    source 00_config.sh
    python 08b_build_analysis_csv.py

Inputs
    $OUT/nodewise/<TRACT>_nodewise_all_subjects.csv   node profiles (Step 8)
    $OUT/nodewise/<TRACT>_tract_stats.csv             cleaned-bundle count and length (Step 6)
    $COVARIATES_CSV                                   Subject, covariates, outcomes

Output, one file per metric, one row per participant:
    $OUT/analysis/<TRACT>__<METRIC>__analysis.csv
    Subject, covariates, outcomes, Streamline_count, Mean_length_mm, <METRIC>_0 ... <METRIC>_99
"""
import os
import sys
from pathlib import Path

import pandas as pd


def env(name):
    if name not in os.environ:
        sys.exit(f"{name} is not set: run `source 00_config.sh` first")
    return os.environ[name]


OUT = Path(env("OUT"))
TRACT = env("TRACT")

profiles = pd.read_csv(OUT / "nodewise" / f"{TRACT}_nodewise_all_subjects.csv",
                       dtype={"Subject": str})
tract_stats = pd.read_csv(OUT / "nodewise" / f"{TRACT}_tract_stats.csv", dtype={"Subject": str})
covariates = pd.read_csv(env("COVARIATES_CSV"), dtype={"Subject": str})
metrics = [c for c in profiles.columns if c not in ("Subject", "Tract", "Node")]

analysis_dir = OUT / "analysis"
analysis_dir.mkdir(parents=True, exist_ok=True)

for metric in metrics:
    wide = profiles.pivot(index="Subject", columns="Node", values=metric)
    wide.columns = [f"{metric}_{int(node)}" for node in wide.columns]
    bundle = tract_stats[["Subject", "Streamline_count", "Mean_length_mm"]]
    table = covariates.merge(bundle, on="Subject").merge(wide.reset_index(), on="Subject")
    path = analysis_dir / f"{TRACT}__{metric}__analysis.csv"
    table.to_csv(path, index=False)
    print(f"{path.name}: {len(table)} participants, {wide.shape[1]} nodes")

profiled = set(profiles["Subject"])
absent = sorted(profiled - set(covariates["Subject"]))
if absent:
    print(f"profiled but absent from the covariate file: {', '.join(absent)}")
