#!/usr/bin/env python3
"""Step 9c. Stack the node-wise results into the file read by the Explorer.

    python 09c_stack_for_explorer.py /path/to/permutation/results

Expects the three outputs of 09b_nodewise_permutation.R for every analysis, named
<tract>__<metric>__<outcome>_nodewise.csv, _clusters.csv and _summary.csv.

Output: results_long.csv in the same directory, one row per node, with columns
    outcome, tract, metric, node, t, p, hemisphere, N, covariates,
    extent_threshold, cluster_p, passed
hemisphere is L or R when the tract name contains the token l or r (l_vta_l_hipp,
anterior_r_vta_r_hipp) and is otherwise empty; cluster_p and passed
describe the largest cluster of the analysis that met the extent threshold.
"""
import sys
from pathlib import Path

import pandas as pd

results_dir = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
rows = []

for summary_file in sorted(results_dir.glob("*_summary.csv")):
    label = summary_file.name[:-len("_summary.csv")]
    parts = label.split("__", 2)
    if len(parts) != 3:
        print(f"skipped {summary_file.name}: label is not <tract>__<metric>__<outcome>")
        continue
    tract, metric, outcome = parts

    summary = pd.read_csv(summary_file).iloc[0]
    nodewise = pd.read_csv(results_dir / f"{label}_nodewise.csv")
    clusters = pd.read_csv(results_dir / f"{label}_clusters.csv")
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
pd.DataFrame(rows).to_csv(out, index=False)
print(f"wrote {out} ({len(rows)} rows, {len(rows) // 100} analyses)")
