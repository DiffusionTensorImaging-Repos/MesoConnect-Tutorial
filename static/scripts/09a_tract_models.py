#!/usr/bin/env python3
"""Step 9a. Whole-tract and quartile models.

Run in a shell where 00_config.sh has been sourced:

    source 00_config.sh
    python 09a_tract_models.py --metric NDI --outcomes memory_accuracy,memory_bias
    python 09a_tract_models.py --metric NDI --outcomes memory_accuracy \\
        --tracts l_vta_l_hipp,anterior_l_vta_l_hipp

The metric is averaged over the whole tract and within quartiles (nodes 0-24, 25-49,
50-74, 75-99).  All variables are standardized, so coefficients are standardized betas.

One tract.  For each segment:  outcome ~ metric + covariates  (ordinary least squares).
    Quartile p values are corrected across the four quartiles (Benjamini-Hochberg).
    Uniformity along the tract:  outcome ~ mean(Q1, Q4) + (Q4 - Q1) + covariates.
    An effect carried by the mean and not by the difference is diffuse, not localized.

Two tracts that share most of their course (--tracts a,b).  Both are stacked, two rows
    per participant, each row with the streamline count and length of its own tract:
    metric ~ outcome + tract + covariates + (1 | participant), fitted by maximum
    likelihood.  The outcome x tract interaction is tested by likelihood ratio (1 df);
    the main effect is reported from the model without the interaction.

Input:  $OUT/analysis/<TRACT>__<METRIC>__analysis.csv   (Step 8b; --analysis-dir overrides)
Output: $OUT/analysis/<label>__<METRIC>__tract_models.csv
"""
import argparse
import os
import sys
import warnings
from pathlib import Path

import pandas as pd
import statsmodels.formula.api as smf
from scipy.stats import chi2
from statsmodels.stats.multitest import multipletests


def env(name):
    if name not in os.environ:
        sys.exit(f"{name} is not set: run `source 00_config.sh` first")
    return os.environ[name]


parser = argparse.ArgumentParser(description="Whole-tract and quartile models")
parser.add_argument("--metric", required=True, help="metric prefix, e.g. NDI")
parser.add_argument("--outcomes", required=True, help="comma-separated outcome columns")
parser.add_argument("--tracts", default=None, help="one tract, or two separated by a comma")
parser.add_argument("--trim", type=int, default=0, help="nodes excluded at each end")
parser.add_argument("--analysis-dir", default=None)
args = parser.parse_args()

METRIC = args.metric
OUTCOMES = args.outcomes.split(",")
TRACTS = (args.tracts or env("TRACT")).split(",")
COVARIATES = env("COVARIATES").split(",")
ANALYSIS = Path(args.analysis_dir) if args.analysis_dir else Path(env("OUT")) / "analysis"
if len(TRACTS) > 2:
    sys.exit("--tracts takes one tract or two")

SEGMENTS = {"Whole": (args.trim, 100 - args.trim), "Q1": (args.trim, 25), "Q2": (25, 50),
            "Q3": (50, 75), "Q4": (75, 100 - args.trim)}
RHS = " + ".join(COVARIATES)


def zscore(frame):
    return (frame - frame.mean()) / frame.std(ddof=1)


def load(tract):
    table = pd.read_csv(ANALYSIS / f"{tract}__{METRIC}__analysis.csv", dtype={"Subject": str})
    absent = [c for c in COVARIATES + OUTCOMES if c not in table.columns]
    if absent:
        sys.exit(f"{tract}: columns not found: {', '.join(absent)}")
    return table


def segment_mean(table, segment):
    lo, hi = SEGMENTS[segment]
    return table[[f"{METRIC}_{node}" for node in range(lo, hi)]].mean(axis=1)


def single_tract(tract):
    """OLS per segment, FDR across quartiles, and the uniformity contrast."""
    table = load(tract)
    rows = []
    for outcome in OUTCOMES:
        quartile_rows = []
        for segment in SEGMENTS:
            d = table[COVARIATES + [outcome]].assign(metric=segment_mean(table, segment))
            d = d.dropna()
            fit = smf.ols(f"{outcome} ~ metric + {RHS}", zscore(d)).fit()
            row = {"model": "ols", "tract": tract, "segment": segment, "outcome": outcome,
                   "term": "metric", "n": int(fit.nobs), "beta": fit.params["metric"],
                   "statistic": fit.tvalues["metric"], "p": fit.pvalues["metric"]}
            rows.append(row)
            if segment != "Whole":
                quartile_rows.append(row)
        adjusted = multipletests([r["p"] for r in quartile_rows], method="fdr_bh")[1]
        for row, p_fdr in zip(quartile_rows, adjusted):
            row["p_fdr"] = p_fdr

        q1, q4 = segment_mean(table, "Q1"), segment_mean(table, "Q4")
        d = table[COVARIATES + [outcome]].assign(mean_q1q4=(q1 + q4) / 2, diff_q4q1=q4 - q1)
        d = d.dropna()
        fit = smf.ols(f"{outcome} ~ mean_q1q4 + diff_q4q1 + {RHS}", zscore(d)).fit()
        for term in ("mean_q1q4", "diff_q4q1"):
            rows.append({"model": "uniformity", "tract": tract, "segment": "Q1,Q4",
                         "outcome": outcome, "term": term, "n": int(fit.nobs),
                         "beta": fit.params[term], "statistic": fit.tvalues[term],
                         "p": fit.pvalues[term]})
    return rows


def two_tracts(tract_a, tract_b):
    """Mixed model across two tracts; likelihood-ratio test of outcome x tract."""
    tables = {tract: load(tract) for tract in (tract_a, tract_b)}
    rows = []
    for outcome in OUTCOMES:
        for segment in SEGMENTS:
            stacked = pd.concat([
                t[["Subject", outcome] + COVARIATES].assign(metric=segment_mean(t, segment),
                                                           tract=name)
                for name, t in tables.items()], ignore_index=True).dropna()
            numeric = ["metric", outcome] + COVARIATES
            stacked[numeric] = zscore(stacked[numeric])
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                main = smf.mixedlm(f"metric ~ {outcome} + tract + {RHS}", stacked,
                                   groups=stacked["Subject"]).fit(reml=False)
                full = smf.mixedlm(f"metric ~ {outcome} * tract + {RHS}", stacked,
                                   groups=stacked["Subject"]).fit(reml=False)
            lr = max(2 * (full.llf - main.llf), 0)
            rows.append({"model": "mixed", "tract": f"{tract_a}+{tract_b}", "segment": segment,
                         "outcome": outcome, "term": outcome,
                         "n": stacked["Subject"].nunique(), "beta": main.params[outcome],
                         "statistic": main.tvalues[outcome], "p": main.pvalues[outcome],
                         "interaction_p": chi2.sf(lr, 1)})
    return rows


results = []
for tract in TRACTS:
    results += single_tract(tract)
if len(TRACTS) == 2:
    results += two_tracts(*TRACTS)

results = pd.DataFrame(results)
label = "+".join(TRACTS)
path = ANALYSIS / f"{label}__{METRIC}__tract_models.csv"
results.to_csv(path, index=False)
with pd.option_context("display.width", 200, "display.float_format", "{:.3f}".format):
    print(results.to_string(index=False))
print(f"\n-> {path}")
