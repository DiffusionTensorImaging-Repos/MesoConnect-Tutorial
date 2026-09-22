#!/usr/bin/env python3
"""Step 8b. Reshape the Step 8 node profiles to one row per participant and join covariates.
Inputs:  $OUT/nodewise/<TRACT>_{nodewise_all_subjects,tract_stats}.csv (Steps 8 and 6)
         $COVARIATES_CSV (Subject, covariates, outcomes)
Output:  $OUT/analysis/<TRACT>__<METRIC>__analysis.csv, one per metric, named as Step 9 expects
Run:     source 00_config.sh && python 08b_build_analysis_csv.py
"""
import os
import sys
from pathlib import Path

import pandas as pd


# Read one exported config variable or stop; exports need `source 00_config.sh`, not `bash`.
def env(name):
    if name not in os.environ:
        sys.exit(f"{name} is not set: run `source 00_config.sh` first")
    return os.environ[name]


OUT = Path(env("OUT"))
TRACT = env("TRACT")

# Subject as str in all three files: all-digit IDs keep leading zeros and the merges match.
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
    # Inner joins: anyone missing from an input is dropped, so N can be below subjects.txt.
    table = covariates.merge(bundle, on="Subject").merge(wide.reset_index(), on="Subject")
    path = analysis_dir / f"{TRACT}__{metric}__analysis.csv"
    table.to_csv(path, index=False)
    print(f"{path.name}: {len(table)} participants, {wide.shape[1]} nodes")

profiled = set(profiles["Subject"])
absent = sorted(profiled - set(covariates["Subject"]))
if absent:
    print(f"profiled but absent from the covariate file: {', '.join(absent)}")
