#!/usr/bin/env python3
"""Step 9 (helper) — stack permutation_one.R outputs into the long CSV the Explorer reads.

Expects, per analysis: <id>_nodewise.csv (Node,Estimate,t_value,p_value), <id>_summary.csv,
<id>_clusters.csv, where <id> = <tract>__<metric>__<outcome>.  Writes results_long.csv with
outcome, tract, metric, node, t, p, N, covariates, extent_threshold, cluster_p, passed
(+ hemisphere if the tract name starts with l_/r_).
"""
import sys, glob, os, pandas as pd
R = sys.argv[1] if len(sys.argv) > 1 else "."
rows = []
for summ in sorted(glob.glob(f"{R}/*_summary.csv")):
    base = os.path.basename(summ)[:-len("_summary.csv")]
    try: tract, metric, outcome = base.split("__", 2)
    except ValueError: continue
    s = pd.read_csv(summ).iloc[0]; nw = pd.read_csv(f"{R}/{base}_nodewise.csv")
    cl = pd.read_csv(f"{R}/{base}_clusters.csv") if os.path.exists(f"{R}/{base}_clusters.csv") else pd.DataFrame()
    passed = bool((cl.get("PassExtentThreshold", pd.Series(dtype=bool)) == True).any()) if len(cl) else False
    cp = cl.loc[cl["PassExtentThreshold"] == True, "ClusterPValue"].min() if passed else ""
    hemi = "L" if tract.startswith("l_") else "R" if tract.startswith("r_") else ""
    for _, r in nw.iterrows():
        rows.append(dict(outcome=outcome, tract=tract, metric=metric, node=int(r["Node"]), t=round(float(r["t_value"]), 4),
                         p=round(float(r["p_value"]), 5), hemisphere=hemi, N=int(s["N_subjects"]), covariates="see model",
                         extent_threshold=int(s["ExtentThresholdNodes"]), cluster_p=cp, passed=int(passed)))
pd.DataFrame(rows).to_csv("results_long.csv", index=False); print(f"wrote results_long.csv ({len(rows)} rows)")
