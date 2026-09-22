#!/usr/bin/env python3
"""Step 9a. Collapse the 100 nodes into whole-tract and quartile means, regress each outcome
on each mean with the covariates, and with two tracts fit a mixed model of outcome x tract.

Input:  $OUT/analysis/<TRACT>__<METRIC>__analysis.csv   (Step 8b; --analysis-dir overrides)
Output: $OUT/analysis/<label>__<METRIC>__tract_models.csv   (<label> is the tract, or a+b)
Run:    source 00_config.sh
        python 09a_tract_models.py --metric NDI --outcomes memory_accuracy,memory_bias
        python 09a_tract_models.py --metric NDI --outcomes memory_accuracy --tracts a,b
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


# Read a variable exported by 00_config.sh, or stop and say so.
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
# The mixed model is written for exactly two tracts; trimming 25+ nodes would empty Q1 or Q4.
if len(TRACTS) > 2:
    sys.exit("--tracts takes one tract or two")
if not 0 <= args.trim < 25:
    sys.exit("--trim must be between 0 and 24 (nodes excluded at each end)")

# Half-open node ranges. Node 0 is the seed end and 99 the target end (Step 8 orients every
# bundle that way), so Q1 sits at the seed and Q4 at the target. --trim shortens Whole, Q1, Q4.
SEGMENTS = {"Whole": (args.trim, 100 - args.trim), "Q1": (args.trim, 25), "Q2": (25, 50),
            "Q3": (50, 75), "Q4": (75, 100 - args.trim)}


def q(column):
    """Quote a column name for patsy, so names like memory-bias or 2back work in a formula."""
    return f'Q("{column}")'


# Covariate part of every formula, so all fits are adjusted identically.
RHS = " + ".join(q(c) for c in COVARIATES)


# Standardize each column (sample SD, as R's scale() does), so the betas are standardized.
def zscore(frame):
    return (frame - frame.mean()) / frame.std(ddof=1)


# Read one tract's Step 8b table (Subject as str keeps leading zeros); stop on missing columns.
def load(tract):
    table = pd.read_csv(ANALYSIS / f"{tract}__{METRIC}__analysis.csv", dtype={"Subject": str})
    absent = [c for c in COVARIATES + OUTCOMES if c not in table.columns]
    if absent:
        sys.exit(f"{tract}: columns not found: {', '.join(absent)}")
    return table


# Per-participant mean of the metric over one segment's nodes; NaN nodes are skipped.
def segment_mean(table, segment):
    lo, hi = SEGMENTS[segment]
    return table[[f"{METRIC}_{node}" for node in range(lo, hi)]].mean(axis=1)


def single_tract(tract):
    """OLS per segment, FDR across the quartiles, and the uniformity contrast."""
    table = load(tract)
    rows = []
    for outcome in OUTCOMES:
        quartile_rows = []
        for segment in SEGMENTS:
            d = table[COVARIATES + [outcome]].assign(metric=segment_mean(table, segment))
            d = d.dropna()
            fit = smf.ols(f"{q(outcome)} ~ metric + {RHS}", zscore(d)).fit()
            row = {"model": "ols", "tract": tract, "segment": segment, "outcome": outcome,
                   "term": "metric", "n": int(fit.nobs), "beta": fit.params["metric"],
                   "statistic": fit.tvalues["metric"], "p": fit.pvalues["metric"]}
            rows.append(row)
            if segment != "Whole":
                quartile_rows.append(row)
        # BH across this outcome's four quartiles; quartile_rows shares its dicts with rows.
        adjusted = multipletests([r["p"] for r in quartile_rows], method="fdr_bh")[1]
        for row, p_fdr in zip(quartile_rows, adjusted):
            row["p_fdr"] = p_fdr

        # mean(Q1, Q4) catches an effect shared by both ends, Q4 - Q1 one stronger at one end.
        q1, q4 = segment_mean(table, "Q1"), segment_mean(table, "Q4")
        d = table[COVARIATES + [outcome]].assign(mean_q1q4=(q1 + q4) / 2, diff_q4q1=q4 - q1)
        d = d.dropna()
        fit = smf.ols(f"{q(outcome)} ~ mean_q1q4 + diff_q4q1 + {RHS}", zscore(d)).fit()
        for term in ("mean_q1q4", "diff_q4q1"):
            rows.append({"model": "uniformity", "tract": tract, "segment": "Q1,Q4",
                         "outcome": outcome, "term": term, "n": int(fit.nobs),
                         "beta": fit.params[term], "statistic": fit.tvalues[term],
                         "p": fit.pvalues[term]})
    return rows


def two_tracts(tract_a, tract_b):
    """Mixed model across two stacked tracts; likelihood-ratio test of outcome x tract."""
    tables = {tract: load(tract) for tract in (tract_a, tract_b)}
    rows = []
    for outcome in OUTCOMES:
        for segment in SEGMENTS:
            # Two rows per participant, each with its own tract's segment mean, streamline
            # count and length (Step 6 measured those per tract).
            stacked = pd.concat([
                t[["Subject", outcome] + COVARIATES].assign(metric=segment_mean(t, segment),
                                                           tract=name)
                for name, t in tables.items()], ignore_index=True).dropna()
            # Standardize pooled, so an offset between tracts goes to the tract term.
            numeric = ["metric", outcome] + COVARIATES
            stacked[numeric] = zscore(stacked[numeric])
            # metric is the DV since each participant has two of them and one outcome.
            # reml=False: the LR test needs ML fits. mixedlm's boundary warnings are muted.
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                main = smf.mixedlm(f"metric ~ {q(outcome)} + tract + {RHS}", stacked,
                                   groups=stacked["Subject"]).fit(reml=False)
                full = smf.mixedlm(f"metric ~ {q(outcome)} * tract + {RHS}", stacked,
                                   groups=stacked["Subject"]).fit(reml=False)
            # Likelihood ratio on 1 df; max(..., 0) clamps a tiny negative from the optimiser.
            lr = max(2 * (full.llf - main.llf), 0)
            # Main effect from the additive model (term Q("<outcome>")); n counts participants.
            rows.append({"model": "mixed", "tract": f"{tract_a}+{tract_b}", "segment": segment,
                         "outcome": outcome, "term": outcome,
                         "n": stacked["Subject"].nunique(), "beta": main.params[q(outcome)],
                         "statistic": main.tvalues[q(outcome)], "p": main.pvalues[q(outcome)],
                         "interaction_p": chi2.sf(lr, 1)})
    return rows


results = []
for tract in TRACTS:
    results += single_tract(tract)
if len(TRACTS) == 2:
    results += two_tracts(*TRACTS)

# "+" in the file name keeps a two-tract run from overwriting a single-tract file.
results = pd.DataFrame(results)
label = "+".join(TRACTS)
path = ANALYSIS / f"{label}__{METRIC}__tract_models.csv"
results.to_csv(path, index=False)
with pd.option_context("display.width", 200, "display.float_format", "{:.3f}".format):
    print(results.to_string(index=False))
print(f"\n-> {path}")
