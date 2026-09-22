#!/usr/bin/env python3
"""Step 9a. Whole-tract and quartile models.

Step 8b left one wide table per metric with a row per participant: the covariates and
outcomes from covariates.csv, the cleaned bundle's streamline count and mean length, and
the metric at each of the 100 nodes.  This script collapses the nodes into segment means
(the whole tract and four quartiles), regresses each outcome on each segment mean with
the covariates, and writes one tidy table of estimates.  Given two tracts it also fits a
mixed model asking whether the association differs between them.

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
        Columns: Subject, covariates, outcomes, Streamline_count, Mean_length_mm and
        <METRIC>_0 ... <METRIC>_99.  Node 0 is the seed end, 99 the target end (Step 8).
Output: $OUT/analysis/<label>__<METRIC>__tract_models.csv
        One row per model term; <label> is the tract, or a+b for two tracts.  Columns:
        model (ols, uniformity, mixed), tract, segment, outcome, term, n, beta,
        statistic, p, p_fdr (quartile rows only), interaction_p (mixed rows only).
        Nothing downstream reads this file; it is the table you report.  Step 9b goes
        back to the analysis CSV for the node-wise test.

Takes seconds: a few dozen small OLS fits, plus ten mixed models per outcome when two
tracts are given.  The table is printed as well as written.  Check that n is your sample
size minus anyone with a missing value, that p_fdr is filled on the Q1-Q4 rows only and
interaction_p on the mixed rows only, and that the last line names the file you expected.
"""
import argparse
import os
import sys
import warnings
from pathlib import Path

# statsmodels.formula.api gives R-style formulas ("y ~ x + z") for both OLS and the mixed
# model; multipletests does the Benjamini-Hochberg correction; chi2 turns the
# likelihood-ratio statistic of the two-tract test into a p value.
import pandas as pd
import statsmodels.formula.api as smf
from scipy.stats import chi2
from statsmodels.stats.multitest import multipletests


# Read one variable exported by 00_config.sh, or stop with a message that says what to
# do.  Argument: the variable name.  Returns its value as a string.  Python only sees
# variables exported in the shell that launched it, which is why "source 00_config.sh"
# has to come first, and again after every edit to the config.
def env(name):
    if name not in os.environ:
        sys.exit(f"{name} is not set: run `source 00_config.sh` first")
    return os.environ[name]


# Command line.  --metric is the node-column prefix Step 8b used (NDI gives NDI_0 ...
# NDI_99).  --outcomes lists the outcome columns to model; every model below is fitted
# once per outcome.  --tracts defaults to $TRACT from the config; two names, comma
# separated, add the mixed model.  --trim drops that many nodes at each end before
# averaging (see SEGMENTS).  --analysis-dir is for analysis files kept somewhere other
# than $OUT/analysis, for instance a copy you are re-analysing on a laptop; the output
# CSV is written there as well.
parser = argparse.ArgumentParser(description="Whole-tract and quartile models")
parser.add_argument("--metric", required=True, help="metric prefix, e.g. NDI")
parser.add_argument("--outcomes", required=True, help="comma-separated outcome columns")
parser.add_argument("--tracts", default=None, help="one tract, or two separated by a comma")
parser.add_argument("--trim", type=int, default=0, help="nodes excluded at each end")
parser.add_argument("--analysis-dir", default=None)
args = parser.parse_args()

# Settings.  "a or b" takes a when it is set and b otherwise, so --tracts wins over the
# config's TRACT.  COVARIATES is the same comma-separated list Step 9b uses.  Nothing is
# stripped of whitespace: COVARIATES="ICV, age" would look for a column called " age" and
# stop in load() with "columns not found"; a space after the comma in --tracts makes load()
# look for a file whose name starts with a space, and read_csv stops with FileNotFoundError.
METRIC = args.metric
OUTCOMES = args.outcomes.split(",")
TRACTS = (args.tracts or env("TRACT")).split(",")
COVARIATES = env("COVARIATES").split(",")
ANALYSIS = Path(args.analysis_dir) if args.analysis_dir else Path(env("OUT")) / "analysis"
# Two guards.  The mixed model is written for exactly two tracts, and trimming 25 or more
# nodes would leave Q1 or Q4 with nothing to average.
if len(TRACTS) > 2:
    sys.exit("--tracts takes one tract or two")
if not 0 <= args.trim < 25:
    sys.exit("--trim must be between 0 and 24 (nodes excluded at each end)")

# Node ranges as half-open (lo, hi) pairs, so range(lo, hi) is the node list.  Whole is
# nodes 0-99 and each quartile is 25 nodes.  Node 0 is the seed end and 99 the target end
# (Step 8 orients every bundle that way), so Q1 sits at the seed and Q4 at the target.
# --trim shortens only Whole, Q1 and Q4.  The end nodes (roughly 0-4 and 95-99) lie in or
# next to grey matter and carry partial-volume signal from the seed and target regions,
# which is the reason to consider trimming.  Decide before looking at any result, and say
# so when reporting; Step 9b has no trim option and always tests all 100 nodes.
SEGMENTS = {"Whole": (args.trim, 100 - args.trim), "Q1": (args.trim, 25), "Q2": (25, 50),
            "Q3": (50, 75), "Q4": (75, 100 - args.trim)}


def q(column):
    """Quote a column name so that any name is valid in a model formula.

    patsy reads the formula as Python, so a column called memory-bias or 2back would
    break "y ~ memory-bias".  Q("memory-bias") looks the column up by string instead.
    The fitted term is then named Q("memory-bias") as well, which is why two_tracts()
    uses q(outcome) again when it pulls the estimate out of the result.
    """
    return f'Q("{column}")'


# The covariate part of every formula, e.g. Q("ICV") + Q("Mean_length_mm") + ...  The
# same string goes into every model so the whole-tract, quartile and mixed fits are
# adjusted identically and can be compared with each other.
RHS = " + ".join(q(c) for c in COVARIATES)


# Standardize every column of a frame: subtract the mean, divide by the SD.
# Argument: a numeric DataFrame.  Returns a frame of the same shape.  ddof=1 is the
# sample SD (N - 1), the same as R's scale(), so a beta from here matches lm() on scaled
# data.  The outcome is standardized along with everything else, which is what makes the
# coefficients standardized betas; the intercept comes out at essentially zero.
def zscore(frame):
    return (frame - frame.mean()) / frame.std(ddof=1)


# Read one tract's analysis CSV from Step 8b and check that every column we will model
# is there.  Argument: the tract label.  Returns the DataFrame.  Subject is read as str
# so an ID like 0123 keeps its leading zero; the mixed model groups rows by this column.
# A missing covariate or outcome is nearly always a typo in COVARIATES or --outcomes, so
# we stop and name it rather than let the column selection below fail with a KeyError.
def load(tract):
    table = pd.read_csv(ANALYSIS / f"{tract}__{METRIC}__analysis.csv", dtype={"Subject": str})
    absent = [c for c in COVARIATES + OUTCOMES if c not in table.columns]
    if absent:
        sys.exit(f"{tract}: columns not found: {', '.join(absent)}")
    return table


# Average the metric over one segment's nodes, per participant.
# Arguments: the analysis table and a SEGMENTS key.  Returns a Series, one value per row.
# The columns are <METRIC>_lo ... <METRIC>_(hi-1) and mean(axis=1) averages across them
# within each row.  pandas skips NaN, so a participant with a few missing nodes is
# averaged over the nodes present rather than dropped; only an all-NaN segment gives
# NaN, and dropna() in the callers removes that participant.
def segment_mean(table, segment):
    lo, hi = SEGMENTS[segment]
    return table[[f"{METRIC}_{node}" for node in range(lo, hi)]].mean(axis=1)


def single_tract(tract):
    """OLS per segment, FDR across quartiles, and the uniformity contrast.

    Argument: the tract label.  Returns a list of result rows (dicts): for every outcome,
    five "ols" rows (Whole, Q1-Q4) and two "uniformity" rows.
    """
    table = load(tract)
    rows = []
    for outcome in OUTCOMES:
        quartile_rows = []
        for segment in SEGMENTS:
            # A small frame with just what this model needs.  .assign adds the segment
            # mean as a column called "metric"; dropna removes any participant with a
            # missing outcome, covariate or segment mean, so n can differ between
            # outcomes.  Standardizing after dropna keeps the z-scores on the people who
            # are actually in the model.
            d = table[COVARIATES + [outcome]].assign(metric=segment_mean(table, segment))
            d = d.dropna()
            # outcome ~ metric + covariates by ordinary least squares.  patsy adds the
            # intercept itself.  .fit() with no arguments gives the usual (non-robust)
            # standard errors and t tests.
            fit = smf.ols(f"{q(outcome)} ~ metric + {RHS}", zscore(d)).fit()
            # One row per fit.  nobs is the number of rows the model saw; params,
            # tvalues and pvalues are indexed by term name and "metric" is the one we
            # report.  The covariate terms are fitted but not written out.
            row = {"model": "ols", "tract": tract, "segment": segment, "outcome": outcome,
                   "term": "metric", "n": int(fit.nobs), "beta": fit.params["metric"],
                   "statistic": fit.tvalues["metric"], "p": fit.pvalues["metric"]}
            rows.append(row)
            # Whole stands alone; the four quartiles are corrected together below.
            if segment != "Whole":
                quartile_rows.append(row)
        # Benjamini-Hochberg across this outcome's four quartile p values.  multipletests
        # returns (reject, corrected p, alpha_sidak, alpha_bonferroni); [1] is the
        # corrected p vector, in the same order as the input.  Adjacent quartiles are
        # correlated, which is why the Step 9 page asks for FDR or a max-statistic
        # permutation here; this script does FDR.  The dicts in quartile_rows are the
        # same objects that sit in rows, so adding p_fdr here lands in the output table.
        adjusted = multipletests([r["p"] for r in quartile_rows], method="fdr_bh")[1]
        for row, p_fdr in zip(quartile_rows, adjusted):
            row["p_fdr"] = p_fdr

        # Uniformity contrast, seed-end quartile against target-end quartile.  Entering
        # the mean of Q1 and Q4 and their difference together is just a re-expression of
        # "Q1 + Q4", but the two terms answer different questions: the mean picks up an
        # effect shared by both ends, the difference an effect that is stronger at one
        # end.  Mean significant and difference near zero reads as a diffuse effect along
        # the tract; a significant difference says the two ends behave differently and
        # the quartile rows are where to look.  Nothing is corrected for these two.
        q1, q4 = segment_mean(table, "Q1"), segment_mean(table, "Q4")
        d = table[COVARIATES + [outcome]].assign(mean_q1q4=(q1 + q4) / 2, diff_q4q1=q4 - q1)
        d = d.dropna()
        fit = smf.ols(f"{q(outcome)} ~ mean_q1q4 + diff_q4q1 + {RHS}", zscore(d)).fit()
        # Both terms are written out, labelled with segment "Q1,Q4" so they sort together.
        for term in ("mean_q1q4", "diff_q4q1"):
            rows.append({"model": "uniformity", "tract": tract, "segment": "Q1,Q4",
                         "outcome": outcome, "term": term, "n": int(fit.nobs),
                         "beta": fit.params[term], "statistic": fit.tvalues[term],
                         "p": fit.pvalues[term]})
    return rows


def two_tracts(tract_a, tract_b):
    """Mixed model across two tracts; likelihood-ratio test of outcome x tract.

    Arguments: the two tract labels; both analysis CSVs must exist for METRIC.  Returns
    one "mixed" row per outcome and segment, carrying the outcome main effect from the
    additive model and interaction_p from the likelihood-ratio test.
    """
    tables = {tract: load(tract) for tract in (tract_a, tract_b)}
    rows = []
    for outcome in OUTCOMES:
        for segment in SEGMENTS:
            # Stack the two tracts long: two rows per participant, each with its own
            # segment mean and, through COVARIATES, its own Streamline_count and
            # Mean_length_mm (Step 6 measured those per tract, so they differ between a
            # participant's two rows).  The outcome and the other covariates repeat.
            # ignore_index renumbers the rows; dropna then removes incomplete rows, so a
            # participant can survive for one tract and not the other.
            stacked = pd.concat([
                t[["Subject", outcome] + COVARIATES].assign(metric=segment_mean(t, segment),
                                                           tract=name)
                for name, t in tables.items()], ignore_index=True).dropna()
            # Standardize on the stacked table, both tracts pooled, so a metric offset
            # between the tracts survives and is absorbed by the tract term instead of
            # being scaled away.  "tract" is text, so patsy treats it as a factor and
            # codes it as one dummy against the first level in sorted order.
            numeric = ["metric", outcome] + COVARIATES
            stacked[numeric] = zscore(stacked[numeric])
            # The metric is the dependent variable here: each participant has one
            # outcome value but two metric values, one per tract, so the model has to
            # explain the metric.  groups= gives every participant a random intercept
            # (statsmodels' default random-effects structure), the "(1 | participant)"
            # of the docstring.  reml=False fits by maximum likelihood, which the
            # likelihood-ratio test needs: REML likelihoods are not comparable between
            # models with different fixed effects.  "main" is the additive model and
            # "full" adds the outcome x tract interaction (patsy's "*" is a + b + a:b).
            # mixedlm is chatty with small samples.  The usual ConvergenceWarning is "The
            # MLE may be on the boundary of the parameter space", which means the
            # participant variance came out near zero (statsmodels warns below 0.01).
            # Warnings are muted for these two fits only.  If an estimate looks odd,
            # refit it by hand outside the with-block and read what it was complaining
            # about.
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                main = smf.mixedlm(f"metric ~ {q(outcome)} + tract + {RHS}", stacked,
                                   groups=stacked["Subject"]).fit(reml=False)
                full = smf.mixedlm(f"metric ~ {q(outcome)} * tract + {RHS}", stacked,
                                   groups=stacked["Subject"]).fit(reml=False)
            # Likelihood-ratio statistic, 2 * (logL_full - logL_main), on 1 df because
            # the interaction adds a single coefficient.  The smaller model cannot fit
            # better in theory, but the optimiser can stop a hair short of the maximum
            # and give a tiny negative; max(..., 0) clamps that.  chi2.sf is the upper
            # tail of the chi-square distribution, so it is the p value directly.
            lr = max(2 * (full.llf - main.llf), 0)
            # The main effect is read from the additive model, as the docstring says.
            # Its term is named Q("<outcome>"), e.g. Q("memory_accuracy"), hence the
            # q(outcome) lookup.  n counts participants, not rows, so it lines up with
            # the OLS rows.
            rows.append({"model": "mixed", "tract": f"{tract_a}+{tract_b}", "segment": segment,
                         "outcome": outcome, "term": outcome,
                         "n": stacked["Subject"].nunique(), "beta": main.params[q(outcome)],
                         "statistic": main.tvalues[q(outcome)], "p": main.pvalues[q(outcome)],
                         "interaction_p": chi2.sf(lr, 1)})
    return rows


# Run.  One single-tract block per tract, so a two-tract call gives both sets of OLS and
# uniformity rows first and then the mixed rows.  *TRACTS unpacks the two-element list
# into the two arguments two_tracts() takes.
results = []
for tract in TRACTS:
    results += single_tract(tract)
if len(TRACTS) == 2:
    results += two_tracts(*TRACTS)

# Write and show.  The row dicts become one DataFrame; columns that only some rows carry
# (p_fdr, interaction_p) are empty elsewhere, and the model column says which kind of row
# each one is.  The file name joins the tract labels with "+", so a two-tract run sits
# next to the single-tract files instead of overwriting one.  option_context widens the
# printout and rounds to three decimals for the terminal only; the CSV keeps full
# precision, and index=False leaves out pandas' row numbers.
results = pd.DataFrame(results)
label = "+".join(TRACTS)
path = ANALYSIS / f"{label}__{METRIC}__tract_models.csv"
results.to_csv(path, index=False)
with pd.option_context("display.width", 200, "display.float_format", "{:.3f}".format):
    print(results.to_string(index=False))
print(f"\n-> {path}")
