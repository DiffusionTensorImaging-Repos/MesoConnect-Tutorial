#!/usr/bin/env python3
"""Step 8b — Build the wide analysis CSV that permutation_one.R and final_models.py read.

Inputs: $OUT/nodewise/<TRACT>_nodewise_all_subjects.csv (long, from step 8),
        $OUT/nodewise/<TRACT>_tract_stats.csv (Subject, Count_tckstats, Mean_tckstats, from step 5),
        $COVARIATES_CSV (Subject + covariates + outcomes; e.g. ICV, absolute_motion, age, outcome columns).
Output: $OUT/analysis/<TRACT>__<METRIC>__analysis.csv, one row per participant, with columns
        Subject, <covariates>, <outcomes>, Count_tckstats, Mean_tckstats, <METRIC>_0 ... <METRIC>_99.
"""
import os
from pathlib import Path
import pandas as pd

OUT = Path(os.environ["OUT"]); TRACT = os.environ["TRACT"]; COV = Path(os.environ["COVARIATES_CSV"])
long = pd.read_csv(OUT / "nodewise" / f"{TRACT}_nodewise_all_subjects.csv")
stats = pd.read_csv(OUT / "nodewise" / f"{TRACT}_tract_stats.csv")
cov = pd.read_csv(COV)
metrics = [c for c in long.columns if c not in ("Subject", "Tract", "Node")]
(OUT / "analysis").mkdir(exist_ok=True)
for m in metrics:
    wide = long.pivot(index="Subject", columns="Node", values=m)
    wide.columns = [f"{m}_{int(n)}" for n in wide.columns]; wide = wide.reset_index()
    df = cov.merge(stats, on="Subject", how="inner").merge(wide, on="Subject", how="inner")
    p = OUT / "analysis" / f"{TRACT}__{m}__analysis.csv"; df.to_csv(p, index=False)
    print(f"{p.name}: {len(df)} participants x {wide.shape[1]-1} nodes (+ {len(cov.columns)-1} covariate/outcome columns)")
print("Then, per outcome:  Rscript permutation_one.R <analysis.csv> <outcome> <METRIC>_ <out_dir> <label>")
