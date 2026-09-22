#!/usr/bin/env python3
"""Step 9c. Stack the Step 9b node-wise results into the one CSV the Explorer reads.

Inputs:  $OUT/permutation/<tract>__<metric>__<outcome>_{summary,nodewise,clusters}.csv
Output:  $OUT/permutation/results_long.csv (one row per node; overwritten every run)
Run:     python 09c_stack_for_explorer.py "$OUT/permutation"
"""
import sys
from pathlib import Path

import pandas as pd

results_dir = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
rows = []

for summary_file in sorted(results_dir.glob("*_summary.csv")):
    label = summary_file.name[:-len("_summary.csv")]
    # maxsplit 2 keeps an outcome that itself contains "__" in one piece
    parts = label.split("__", 2)
    if len(parts) != 3:
        print(f"skipped {summary_file.name}: label is not <tract>__<metric>__<outcome>")
        continue
    tract, metric, outcome = parts

    summary = pd.read_csv(summary_file).iloc[0]
    nodewise = pd.read_csv(results_dir / f"{label}_nodewise.csv")
    clusters = pd.read_csv(results_dir / f"{label}_clusters.csv")
    # an empty clusters file reads back as object dtype, not bool, so we compare as text
    passing = clusters[clusters["PassExtentThreshold"].astype(str).str.upper() == "TRUE"]

    tokens = tract.lower().split("_")
    hemisphere = next((t.upper() for t in tokens if t in ("l", "r")), "")

    for node in nodewise.itertuples():
        rows.append({
            "outcome": outcome, "tract": tract, "metric": metric,
            "node": int(node.Node), "t": round(node.t_value, 4), "p": round(node.p_value, 5),
            "hemisphere": hemisphere, "N": int(summary["N_subjects"]),
            "covariates": summary["Covariates"],
            "extent_threshold": int(summary["ExtentThresholdNodes"]),
            "cluster_p": passing["ClusterPValue"].min() if len(passing) else "",
            "passed": int(len(passing) > 0),
        })

if not rows:
    sys.exit(f"no *_summary.csv files found in {results_dir}")
out = results_dir / "results_long.csv"
# index=False because the Explorer treats any column it does not know as a grouping variable
pd.DataFrame(rows).to_csv(out, index=False)
# assumes 100 nodes per analysis
print(f"wrote {out} ({len(rows)} rows, {len(rows) // 100} analyses)")
