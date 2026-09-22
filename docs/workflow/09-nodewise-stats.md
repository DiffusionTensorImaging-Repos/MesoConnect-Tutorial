---
sidebar_position: 10
title: "Step 9. Group-level inference"
---

# Step 9. Group-level inference

Along-tract data can be analysed at three spatial resolutions: the whole tract, quartiles of the tract, and individual nodes (Table 1). The three address different questions, and no single resolution is appropriate for every study. The resolution, or combination of resolutions, should be specified before results are examined, and the same covariates should be used throughout. Where the neurite density index (NDI) is mentioned below, it refers to the neurite orientation dispersion and density imaging metric profiled in Step 8; VTA denotes the ventral tegmental area.

**Table 1**

*Three Resolutions for Along-Tract Inference*

| Resolution | Unit of analysis | Question | Correction | Script |
|---|---|---|---|---|
| Whole tract | Metric averaged across nodes; one value per participant per tract | Is the metric associated with the outcome; does the association differ between subregional tracts | None within tract; across outcomes as pre-specified | `09a_tract_models.py` |
| Quartiles | Metric averaged within nodes 0–24, 25–49, 50–74, 75–99 | Does the association vary along the tract; is it confined to a segment | False discovery rate (FDR) or maximum-statistic permutation across the four quartiles | `09a_tract_models.py` |
| Nodes | Metric at each of 100 nodes | Where along the tract is the association located | Cluster-extent family-wise error (FWE) by permutation | `09b_nodewise_permutation.R` |

## Whole-tract model

The metric is averaged across all 100 nodes, or across the retained range if end nodes are trimmed (`--trim`), and the outcome is regressed on the averaged metric and the covariates. All variables are standardized, so coefficients are standardized betas. When two subregional tracts share most of their course (posterior and anterior VTA → hippocampus), both are entered in one mixed model with a subregion term, two rows per participant, a random intercept for participant, and each row carrying its own streamline length and count. The outcome × subregion interaction is tested by likelihood ratio; when it does not improve fit, the main effect is reported. In the mixed model the metric is the dependent variable, because each participant contributes one metric value per tract and a single outcome value. This resolution has the greatest power when the effect is distributed along the tract, and it does not localize the effect.

## Quartile model

The same model is fitted with the metric averaged within each quartile. Because adjacent quartiles are correlated, correction across the four should either use the FDR or a maximum-statistic permutation that preserves their dependence. Uniformity along the tract is tested directly by contrasting the seed-end quartile against the target-end quartile with the mean and the difference entered together: when the mean carries the effect and the difference does not differ from zero, the effect is diffuse rather than localized.

Both resolutions are fitted by one script, which reads the analysis files from Step 8b and the covariate list (`COVARIATES`) from the configuration. With one tract it reports the whole-tract and quartile regressions, the FDR-corrected quartile *p* values and the uniformity contrast; with two tracts it adds the mixed model and the likelihood-ratio test of the interaction for every segment.

```bash
source 00_config.sh
python 09a_tract_models.py --metric NDI --outcomes memory_accuracy,memory_bias
python 09a_tract_models.py --metric NDI --outcomes memory_accuracy \
    --tracts l_vta_l_hipp,anterior_l_vta_l_hipp
```

Results are printed and written to `$OUT/analysis/<tract>__<METRIC>__tract_models.csv`, one row per model term, with the columns `model` (`ols`, `uniformity` or `mixed`), `tract`, `segment`, `outcome`, `term`, `n`, `beta`, `statistic`, `p`, `p_fdr` and `interaction_p`.

## Node-wise model

At each node the outcome is regressed on the node's metric and the covariates, and the fit is compared with a reduced model omitting the metric.

```r
full    ~ metric_node + ICV + tract_length + streamline_count + motion + age
reduced ~               ICV + tract_length + streamline_count + motion + age
```

Each node yields a *t* statistic and a parametric *p* value, and adjacent nodes with *p* < .05 form clusters. Family-wise error is controlled at the cluster level with a Freedman–Lane permutation procedure (Freedman & Lane, 1983; Winkler et al., 2014): the residuals of the reduced model are permuted, all 100 nodes are refitted, the largest cluster of each permutation is recorded, and the procedure is repeated 5,000 times. A cluster's *p* value is the proportion of permutations whose largest cluster is at least as long, and a cluster is retained when that value does not exceed .05; the smallest extent that meets this criterion is reported as the extent threshold. The permutations are drawn once from a fixed seed, so results do not depend on the number of cores. Variables are not standardized in this script; the node-wise estimates are in the units of the outcome per unit of the metric.

The script reads the wide analysis file produced in Step 8b and is called once per outcome, tract and metric: `Rscript 09b_nodewise_permutation.R <analysis.csv> <outcome> <METRIC>_ <out_dir> <label>`, with the label written as `<tract>__<metric>__<outcome>`. Covariate column names and the number of permutations are taken from the `COVARIATES` and `N_PERMUTATIONS` settings in the configuration. Outputs per analysis are `_nodewise.csv` (node, estimate, *t*, *p*), `_clusters.csv` and `_summary.csv`; each call requires a few minutes on one core.

```bash
source 00_config.sh
mkdir -p "$OUT/permutation"
for outcome in memory_accuracy memory_bias; do
  Rscript 09b_nodewise_permutation.R "$OUT/analysis/${TRACT}__NDI__analysis.csv" \
    "$outcome" NDI_ "$OUT/permutation" "${TRACT}__NDI__${outcome}"
done
```

This resolution localizes an effect along the tract. Its limitation is that cluster-extent correction detects contiguous runs of supra-threshold nodes; when an effect is uniform along the tract, per-node *t* statistics remain near threshold at every node and the outcome becomes sensitive to small changes in model specification. In that situation node-wise results are descriptive and the whole-tract or quartile model carries the inference.

## Covariates

Covariates comprise intracranial volume (ICV), the mean streamline length and streamline count of the cleaned bundle (written by Step 6), absolute head motion and age. Length and count are tract-specific and index reconstruction quality. Streamline count can be strongly correlated with the metric under test (*r* = .63 to .87 with tract-mean NDI across the tracts of the example dataset), which reduces the residual variance available to the test. Its inclusion should be decided in advance and both specifications reported.

## Choosing a resolution

A hypothesis about a particular segment of a pathway calls for the quartile or node-wise model. A hypothesis about the pathway as a whole calls for the whole-tract model. Exploratory work is often best served by the whole-tract model for inference with the node-wise profile reported as description. Tests across several metrics, tracts and outcomes accumulate rapidly at any resolution; fixing the analytic hierarchy in advance (primary metric, primary outcome family) is more readily justified than correcting across all tests afterwards.

In the example dataset, three social-memory measures were associated with NDI in the whole-tract model with no subregion interaction. In the quartile model one of them (positivity bias in false memories) was significant in all four quartiles and the seed-end versus target-end contrast was null for all three, indicating uniform effects. Node-wise clusters were located at nodes 27 to 55 and changed with covariate specification. The results were therefore reported with the whole-tract model as primary, the quartile model as confirmation of uniformity, and node-wise profiles as description. Applied to the analysis files of that dataset, `09a_tract_models.py` reproduces the reported whole-tract and quartile estimates.

## Preparing node-wise results for the Explorer

Node-wise outputs are stacked into a single long-format file for the Node-wise Tract Explorer, the browser-based viewer described in the [Explorer section](../explorer).

```bash
python 09c_stack_for_explorer.py "$OUT/permutation"   # writes results_long.csv in that directory
```

The file contains one row per node with the columns `outcome, tract, metric, node, t, p`, together with `hemisphere, N, covariates, extent_threshold, cluster_p` and `passed`.

## Scripts

<!-- script:09a_tract_models.py -->
<details>
<summary>Script <code>09a_tract_models.py</code> (313 lines)</summary>

```python title="09a_tract_models.py"
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
```

</details>
<!-- /script:09a_tract_models.py -->

<!-- script:09b_nodewise_permutation.R -->
<details>
<summary>Script <code>09b_nodewise_permutation.R</code> (421 lines)</summary>

```r title="09b_nodewise_permutation.R"
# =============================================================================
# Step 9b. Node-wise cluster-extent permutation test (Freedman-Lane)
# =============================================================================
# At each node:  outcome ~ metric_node + covariates.  The residuals of the
# reduced model (covariates only) are permuted, all nodes are refitted, and the
# maximum cluster extent of each permutation forms the null distribution.
# Adapted from a reference implementation used in atlas construction.
#
# What it does.  Step 9a asked whether the metric relates to the outcome over the whole
# tract or within quartiles; this script asks WHERE along the tract.  One linear model
# per node (100 of them) gives 100 t values; adjacent nodes with p < .05 are joined into
# clusters; the question is then whether a cluster that long could arise by chance.
# Permutation answers it: shuffle the part of the outcome the covariates do not explain,
# refit all 100 nodes, keep the longest cluster, repeat N_PERMUTATIONS times.  A real
# cluster passes when no more than 5% of the shuffles produced one at least as long.
# Nothing is standardized here, so Estimate is in outcome units per unit of the metric;
# the 9a betas are standardized, so do not compare the two directly.
#
# Usage (in a shell where 00_config.sh has been sourced):
#   Rscript 09b_nodewise_permutation.R <analysis.csv> <outcome> <METRIC>_ <out_dir> <label>
#     1. analysis.csv   wide analysis file from Step 8b
#     2. outcome        outcome column, e.g. memory_accuracy
#     3. METRIC_        node-column prefix including the underscore, e.g. NDI_
#     4. out_dir        directory for the results
#     5. label          <tract>__<metric>__<outcome>, used in the output file names
# Environment: COVARIATES (comma-separated columns), N_PERMUTATIONS (default 5000),
#              R_PERM_CORES (default: all cores but one)
# Outputs: <label>_nodewise.csv, <label>_clusters.csv, <label>_summary.csv
#
# One call does one outcome for one tract and one metric, so the Step 9 page loops in
# the shell:
#   for outcome in memory_accuracy memory_bias; do
#     Rscript 09b_nodewise_permutation.R "$OUT/analysis/${TRACT}__NDI__analysis.csv" \
#       "$outcome" NDI_ "$OUT/permutation" "${TRACT}__NDI__${outcome}"
#   done
# The label is not parsed here, but Step 9c splits it on the double underscore to get
# tract, metric and outcome back, so keep that exact shape.
#
# Needs:
#   $OUT/analysis/<TRACT>__<METRIC>__analysis.csv   Step 8b: one row per participant,
#       the covariate and outcome columns, Streamline_count, Mean_length_mm and the
#       node columns <METRIC>_0 ... <METRIC>_99
#   R with readr, tibble, foreach, doParallel (dplyr and stringr are attached below
#       but nothing calls them)
# Writes, into <out_dir> (normally $OUT/permutation):
#   <label>_nodewise.csv   one row per node: Node, Estimate, t_value, p_value, df, n
#   <label>_clusters.csv   one row per observed cluster, with its permutation p value
#   <label>_summary.csv    one row: sample size, settings, counts, extent threshold
# Step 9c stacks these three into results_long.csv for the Explorer.
#
# Runtime: a few minutes per call on one core at 5,000 permutations; more cores cut that
# (the default is every core but one).  The seed is fixed and the shuffles are drawn
# before the workers start, so the same N gives the same numbers whatever the core count.
# What to look for.  The last line printed is "Done: <label> — clusters=K sig nodes=M
# ext_thr=T": K clusters were formed, M nodes had p < .05, and a cluster needs at least
# T nodes to pass.  Open _clusters.csv and look at PassExtentThreshold; TRUE rows are
# the ones that survive.  In the example dataset the clusters sat at nodes 27 to 55 and
# moved when the covariate list changed, which is why the page treats node-wise results
# as description and lets the whole-tract model carry the inference.  "Dropping N
# incomplete participants" means N rows had an NA in the outcome, a covariate or a node;
# if N is large, look at the analysis file before trusting anything else.
# =============================================================================
# suppressPackageStartupMessages hides the "Attaching package" chatter so the terminal
# shows only this script's own messages.  readr reads and writes the CSVs, tibble builds
# the output tables, foreach + doParallel + parallel run the permutations on several
# cores.  dplyr and stringr are attached but nothing below calls them; on an R install
# without them, those two library() calls are the only place this script would fail.
suppressPackageStartupMessages({
  library(readr); library(dplyr); library(stringr)
  library(foreach); library(doParallel); library(parallel); library(tibble)
})

# Positional arguments.  commandArgs(trailingOnly = TRUE) returns only what came after
# the script name, so args[1] is the analysis CSV.  stopifnot aborts with a message if
# fewer than five were given; extra ones are ignored.
args <- commandArgs(trailingOnly = TRUE)
stopifnot(length(args) >= 5)
data_csv      <- args[1]
response_col  <- args[2]
metric_prefix <- args[3]    # "NDI_", underscore included; "NDI" alone matches nothing
out_dir       <- args[4]
base          <- args[5]    # <tract>__<metric>__<outcome>; every output name starts with it

# Covariates: comma-separated column names, exported by 00_config.sh
# Sys.getenv returns "" when the variable is missing; stopping here with a plain message
# beats a cryptic "object not found" from lm later on.  strsplit returns a list with one
# element per input string, and [[1]] takes the vector for our single string.  Nothing
# is trimmed, so "ICV, age" (with a space) would look for a column named " age".
# The same list is used by Step 9a, so the three resolutions are comparable.
# Streamline_count is in the default list and correlates strongly with NDI (see
# 00_config.sh); decide before running whether it stays in, and report both.
covariate_env <- Sys.getenv("COVARIATES", unset = "")
if (covariate_env == "") stop("COVARIATES is not set: run `source 00_config.sh` first")
covariate_cols <- strsplit(covariate_env, ",")[[1]]

# Settings.  alpha_node is the per-node threshold that decides which nodes join a
# cluster; alpha_familywise is the cluster-level threshold applied to the permutation
# p values.  Both are .05 as on the page.  Lowering alpha_node makes clusters shorter
# and rarer in the real data and in the null alike, so the extent threshold drops too;
# it is a cluster-forming choice, not a correction.  N_PERMUTATIONS comes from
# 00_config.sh (5,000); the cluster p values are proportions of that many draws, so
# their resolution is 1/N.  rng_seed fixes the shuffles, so a rerun reproduces the
# output exactly.  use_parallel is not read anywhere below; the core count further down
# is what decides between the parallel and serial paths.
alpha_node       <- 0.05
alpha_familywise <- 0.05
num_permutations <- as.integer(Sys.getenv("N_PERMUTATIONS", unset = "5000"))
rng_seed         <- 123
use_parallel     <- TRUE

# recursive = TRUE creates missing parents (like mkdir -p); showWarnings = FALSE keeps
# quiet when the directory already exists, which it will from the second outcome on.
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

# show_col_types = FALSE silences readr's column-type printout (over 100 columns here).
dat <- readr::read_csv(data_csv, show_col_types = FALSE)

# Collect node columns
# The pattern anchors the prefix at the start and allows only digits to the end (\\d+$),
# so NDI_0 ... NDI_99 match and something like NDI_mean would not.  value = TRUE returns
# the matching names rather than their positions.
node_cols <- grep(paste0("^", metric_prefix, "\\d+$"), names(dat), value = TRUE)
if (length(node_cols) == 0) {
  stop("No columns matching ", metric_prefix, "0.. in: ", data_csv)
}
# Strip the prefix to get the node number, then sort numerically.  read_csv hands the
# columns back in file order, which is already 0..99 from Step 8b, but ordering by the
# integer guards against a file where NDI_10 sits before NDI_2.  The cluster code below
# relies on node_idx increasing along the vector.
node_idx  <- as.integer(sub(paste0("^", metric_prefix), "", node_cols))
ord       <- order(node_idx)
node_cols <- node_cols[ord]; node_idx <- node_idx[ord]
num_nodes <- length(node_cols)

# Numeric casts
# A stray text value ("missing", ".", a note) makes readr read the whole column as text;
# as.numeric turns the numbers back and the text into NA, which the complete-case
# filter below then drops.  Expect a "NAs introduced by coercion" warning when that
# happens; it is telling you which column to clean.
dat[[response_col]] <- as.numeric(dat[[response_col]])
for (cc in covariate_cols) dat[[cc]] <- as.numeric(dat[[cc]])

# Drop incomplete
# complete.cases is TRUE for rows with no NA in any of the listed columns: the outcome,
# every covariate and every node.  A participant missing even one node is dropped
# entirely, so that all 100 fits use the same people and the permutation, which
# shuffles one residual vector for all nodes at once, stays valid.  "if (n_dropped)"
# treats 0 as FALSE.  message() writes to stderr, so add 2>&1 if you redirect to a log.
all_model_cols <- c(response_col, covariate_cols, node_cols)
mask <- complete.cases(dat[, all_model_cols])
n_dropped <- sum(!mask)
if (n_dropped) message("Dropping ", n_dropped, " incomplete participants")
dat <- dat[mask, , drop = FALSE]
n_subj <- nrow(dat)
# Five is a sanity floor, not a power check: with the default five covariates the full
# model has seven coefficients (intercept, node, covariates) and needs more rows than
# that to have any residual df at all.  quit(status = 0) exits cleanly, so a shell loop
# running under set -e is not aborted; the missing output files are the sign that this
# outcome was skipped.
if (n_subj < 5) {
  message("Fewer than 5 complete participants (", n_subj, ") — skipping ", base)
  quit(status = 0)
}

y <- dat[[response_col]]

# Formulas
# Built as text so the covariate list can be anything.  "node" is the column the fit
# functions below create for the current node's metric; y is the outcome.  The full
# model tests the node; the reduced model, without it, is what gets permuted.
full_formula <- as.formula(
  paste("y ~ node +", paste(covariate_cols, collapse = " + "))
)
red_formula  <- as.formula(
  paste("y ~", paste(covariate_cols, collapse = " + "))
)

# Nodewise fit
# One ordinary least squares fit of the full model for one node.
#   y              outcome vector, all complete participants
#   node           that node's metric, one value per participant
#   covariates_df  data frame holding the covariate columns
# Returns a named vector: Estimate (slope of y on the node metric), t, two-sided p,
# residual df and n.  The statistics come back NA when the node cannot be tested: fewer
# than three rows, a metric that is constant across participants (no variance, no
# slope), or a "node" term that lm dropped because it is perfectly collinear with a
# covariate (summary() leaves aliased terms out of its coefficient table, hence the
# rownames check).  Such nodes count as not significant and break any cluster.
fit_node_full <- function(y, node, covariates_df) {
  df0 <- data.frame(y = y, node = node, covariates_df)
  df0 <- df0[complete.cases(df0), ]
  if (nrow(df0) < 3 || sd(df0$node) == 0)
    return(c(Estimate=NA, t=NA, p=NA, df=NA, n=nrow(df0)))
  fit <- lm(full_formula, data = df0)
  sm <- summary(fit)$coefficients
  if (!("node" %in% rownames(sm)))
    return(c(Estimate=NA, t=NA, p=NA, df=fit$df.residual, n=nrow(df0)))
  # summary() already reports Pr(>|t|); recomputing it as 2*pt(-|t|, df) gives the same
  # two-sided p and is the exact formula the permutation loop uses, so the observed and
  # null p values are on the same footing.  df.residual is n minus the coefficient count.
  tval <- unname(sm["node","t value"])
  est  <- unname(sm["node","Estimate"])
  pval <- 2*pt(-abs(tval), df=fit$df.residual)
  c(Estimate=est, t=tval, p=pval, df=fit$df.residual, n=nrow(df0))
}

# Observed statistics, one fit per node.  lm is deterministic, so this set.seed changes
# nothing; the seed that matters is reset just before the shuffles are drawn.  lapply
# returns a list of named vectors and do.call(rbind, ...) stacks them into a matrix
# with one row per node and the names as columns.
set.seed(rng_seed)
node_stats <- lapply(seq_along(node_cols), function(i) {
  fit_node_full(y, dat[[node_cols[i]]], dat[, covariate_cols, drop=FALSE])
})
node_stats <- do.call(rbind, node_stats)
# First output.  Step 9c reads Node, t_value and p_value from this file, and the
# Explorer draws t_value along the tract with the p < .05 nodes highlighted.
node_stats_df <- tibble(
  Node=node_idx, Estimate=node_stats[,"Estimate"],
  t_value=node_stats[,"t"], p_value=node_stats[,"p"],
  df=node_stats[,"df"], n=node_stats[,"n"]
)
write_csv(node_stats_df, file.path(out_dir, paste0(base, "_nodewise.csv")))

# Cluster helpers
# Group significant nodes into runs of consecutive node numbers.
#   sig            logical, one entry per node, TRUE where p < alpha_node
#   nodes_numeric  the node numbers in the same order (node_idx)
# Returns a list of integer vectors, one per cluster, each holding the node numbers in
# that run; an empty list when nothing is significant.  Adjacency is judged on the node
# NUMBER (k follows k-1), not on position in the vector, so a gap in the numbering ends
# a cluster.  A lone significant node is a cluster of size 1.  The same function serves
# the observed data and every permutation, so the cluster rule cannot drift apart.
clusters_from_sig <- function(sig, nodes_numeric) {
  if (!any(sig)) return(list())
  idx <- which(sig); cls <- list(); run <- c(nodes_numeric[idx[1]])
  if (length(idx) > 1) for (k in 2:length(idx)) {
    if (nodes_numeric[idx[k]] == nodes_numeric[idx[k-1]] + 1)
      run <- c(run, nodes_numeric[idx[k]])
    else { cls[[length(cls)+1]] <- run; run <- c(nodes_numeric[idx[k]]) }
  }
  cls[[length(cls)+1]] <- run; cls
}
# Length of the longest cluster, or 0 when there is none.  This one number per
# permutation is the whole null distribution.  vapply(..., 1L) promises one integer per
# cluster, so max() gets an integer vector rather than a list.
max_cluster_size_from_sig <- function(sig, nodes_numeric) {
  cls <- clusters_from_sig(sig, nodes_numeric)
  if (length(cls)==0) 0L else max(vapply(cls, length, 1L))
}

# Observed clusters.  Nodes with an NA p (untestable) are treated as not significant,
# so they end a cluster rather than being skipped over.
sig_mask <- !is.na(node_stats_df$p_value) & node_stats_df$p_value < alpha_node
obs_clusters <- clusters_from_sig(sig_mask, node_stats_df$Node)
obs_sizes <- vapply(obs_clusters, length, 1L)
obs_max_size <- if (length(obs_sizes)) max(obs_sizes) else 0L
num_sig_nodes <- sum(sig_mask)
num_clusters  <- length(obs_clusters)

# Freedman-Lane
# Fit the reduced model (covariates only) once on the real outcome and keep its fitted
# values and residuals.  Each permuted outcome is fitted + shuffled residuals: the part
# of y the covariates explain stays with its owner, only the leftover is reassigned
# across participants.  That is what makes the null hold for the node term with the
# covariates still in the model (Freedman & Lane, 1983; Winkler et al., 2014).
# Shuffling y outright would also scramble its relation to the covariates, so the null
# would no longer describe data with those covariates in place.
df_red_global <- data.frame(y=y, dat[, covariate_cols, drop=FALSE])
fit_red <- lm(red_formula, data=df_red_global)
yhat_red <- fitted(fit_red); resid_red <- resid(fit_red)

# Nodes whose metric is constant across participants have no slope to test; they keep p = 1
# in every permutation.  Checked once here rather than 5,000 x 100 times in the loop.
analysable <- vapply(seq_along(node_cols), function(i)
  sd(dat[[node_cols[i]]]) > 0, logical(1))

# All permutations are drawn once, here, so that the null distribution is identical
# for any number of cores and any scheduling of the parallel workers.
# sample.int(n) is a random ordering of 1..n; vapply stacks the draws into an n_subj by
# num_permutations integer matrix, one shuffle per column.  Drawing inside the workers
# instead would give each worker its own RNG stream and the result would change with
# the core count; the validation on the Scripts page checked 1, 3 and 4 cores agree.
set.seed(rng_seed)
perm_mat <- vapply(seq_len(num_permutations), function(k) sample.int(n_subj),
                   integer(n_subj))

# One permutation.  Takes the permutation number, builds the permuted outcome, refits
# the full model at every analysable node, and returns the length of the longest run of
# nodes with p < alpha_node (an integer, 0 if none).  Same model, same p formula and
# same cluster rule as the observed pass, which is what makes the two comparable.  Only
# the p values are kept; estimates from permuted data mean nothing.  The leading dot in
# .perm is only a naming convention, so the argument and the foreach loop variable perm
# further down do not share a name.
perm_fun <- function(.perm) {
  perm_idx <- perm_mat[, .perm]
  y_perm <- yhat_red + resid_red[perm_idx]
  p_perm <- rep(1, num_nodes)
  for (i in which(analysable)) {
    df_perm <- data.frame(y=y_perm, node=dat[[node_cols[i]]],
                          dat[, covariate_cols, drop=FALSE])
    fit <- lm(full_formula, data=df_perm)
    sm <- summary(fit)$coefficients
    if ("node" %in% rownames(sm)) {
      tval <- sm["node","t value"]
      p_perm[i] <- 2*pt(-abs(tval), df=fit$df.residual)
    }
  }
  max_cluster_size_from_sig(p_perm < alpha_node, node_idx)
}

# Core count.  R_PERM_CORES in the shell overrides.  Anything that is not a number
# (unset, "", "all") comes out of as.integer as NA and suppressWarnings hides the
# coercion warning; NA or anything below 1 falls back to every core but one.
# detectCores counts logical CPUs, so on a shared machine set R_PERM_CORES to something
# polite.
env_cores <- suppressWarnings(as.integer(Sys.getenv("R_PERM_CORES", unset = NA)))
if (!is.na(env_cores) && env_cores > 0L) {
  cores <- env_cores
} else {
  cores <- max(1L, parallel::detectCores() - 1L)
}

# Run the permutations.  makeCluster starts that many separate R processes (PSOCK
# workers, the default type) and registerDoParallel points foreach's %dopar% at them.
# foreach(perm = 1:N) %dopar% expr evaluates expr once per value of perm, spread over
# the workers.  foreach finds the variables the body needs by walking perm_fun and the
# functions it calls, and ships them (dat, perm_mat, node_idx, ...) to each worker, so
# no .export is needed.  .packages = "stats" loads the package holding lm and pt on the
# workers; they attach it at startup anyway, so this is belt and braces.  .combine = c
# joins the returned integers into one vector instead of a list.  stopCluster shuts the
# workers down; without it they linger until R exits.  With one core the same function
# runs through a plain vapply.  If something inside perm_fun fails, all that comes back
# is 'task N failed - "<message>"' with no hint of where; rerun with R_PERM_CORES=1 and
# R names the failing call.
if (cores > 1L) {
  cl <- parallel::makeCluster(cores); registerDoParallel(cl)
  perm_max_sizes <- foreach(perm = 1:num_permutations, .combine = c,
                            .packages = "stats") %dopar% perm_fun(perm)
  parallel::stopCluster(cl)
} else {
  perm_max_sizes <- vapply(1:num_permutations, perm_fun, integer(1))
}

# Cluster p value: proportion of permutations whose largest cluster is at least as long.
# The extent threshold is the smallest extent with p <= alpha.  Extents are whole
# numbers, so this is one node above the (1 - alpha) quantile; a cluster exactly at the
# quantile has p > alpha and does not pass.
# quantile(type = 1) is the inverse of the empirical distribution function: it returns
# an actual value from perm_max_sizes, never an interpolated fraction, so the + 1 lands
# on a whole node.  The p value uses >=, so a null cluster exactly as long as the
# observed one counts against it.  When no permutation reached the observed length the
# proportion comes out 0, which only means below 1/N_PERMUTATIONS, the smallest p these
# draws can resolve.  The threshold is one number per analysis, written to the summary
# and copied into every cluster row.
cluster_p_from_size <- function(size) mean(perm_max_sizes >= size)
extent_threshold <- as.integer(quantile(perm_max_sizes, probs = 1 - alpha_familywise,
                                        type = 1)) + 1L

# Second output, one row per observed cluster.  match() finds each cluster node's row in
# the node table so its t value and estimate can be pulled out.  Direction is the sign
# of the mean t; MaxAbsTNode is where |t| peaks, handy when reporting a location.
# PassExtentThreshold is computed from the p value, not from Size >= threshold, so the
# two can never disagree.  Step 9c keeps only the TRUE rows and takes the smallest
# ClusterPValue among them for the Explorer.
if (num_clusters > 0) {
  all_clusters_df <- do.call(rbind, lapply(seq_along(obs_clusters), function(k) {
    nodes <- obs_clusters[[k]]; idx_in_table <- match(nodes, node_stats_df$Node)
    t_vals <- node_stats_df$t_value[idx_in_table]
    ests   <- node_stats_df$Estimate[idx_in_table]
    tibble(
      ClusterID=k, Size=length(nodes), StartNode=min(nodes), EndNode=max(nodes),
      Nodes=paste(nodes, collapse=","),
      MeanTValue=mean(t_vals, na.rm=TRUE),
      Direction=ifelse(mean(t_vals, na.rm=TRUE)>0,"Positive","Negative"),
      MaxAbsTValue=t_vals[which.max(abs(t_vals))],
      MaxAbsTNode=nodes[which.max(abs(t_vals))],
      MeanEstimate=mean(ests, na.rm=TRUE),
      ClusterPValue=cluster_p_from_size(length(nodes)),
      ExtentThresholdNodes=extent_threshold,
      PassExtentThreshold=cluster_p_from_size(length(nodes)) <= alpha_familywise
    )
  }))
} else {
  # No clusters at all: write a header-only file with the same columns and types, so
  # Step 9c and anything else reading the directory finds the file it expects.
  all_clusters_df <- tibble(
    ClusterID=integer(), Size=integer(), StartNode=integer(), EndNode=integer(),
    Nodes=character(), MeanTValue=double(), Direction=character(),
    MaxAbsTValue=double(), MaxAbsTNode=integer(),
    MeanEstimate=double(),
    ClusterPValue=double(), ExtentThresholdNodes=integer(), PassExtentThreshold=logical()
  )
}
write_csv(all_clusters_df, file.path(out_dir, paste0(base, "_clusters.csv")))

# Third output, one row that records what was modelled, on how many participants, with
# which settings, and what came out.  Step 9c reads N_subjects, Covariates and
# ExtentThresholdNodes from here (the column names are fixed; it looks them up by
# name).  N_subjects is the count after the incomplete rows went; N_dropped says how
# many that was.  NodesTested should be 100.
summary_df <- tibble(
  Outcome=response_col,
  MetricPrefix=metric_prefix,
  Covariates=paste(covariate_cols, collapse=", "),
  N_subjects=n_subj, N_dropped=n_dropped,
  NodesTested=num_nodes,
  NodewiseAlpha=alpha_node, FamilywiseAlpha=alpha_familywise,
  NumPermutations=num_permutations,
  NumNodewiseSignificant=num_sig_nodes,
  NumClustersFormed=num_clusters,
  ObservedMaxClusterSize=obs_max_size,
  ExtentThresholdNodes=extent_threshold,
  NumClustersPassingExtent=sum(all_clusters_df$PassExtentThreshold, na.rm=TRUE)
)
write_csv(summary_df, file.path(out_dir, paste0(base, "_summary.csv")))
# Last line on the terminal; the numbers repeat NumClustersFormed, NumNodewiseSignificant
# and ExtentThresholdNodes from the summary, so a quick scan of the shell loop's output
# tells you which outcomes produced anything.
message("Done: ", base, " — clusters=", num_clusters,
        " sig nodes=", num_sig_nodes, " ext_thr=", extent_threshold)
```

</details>
<!-- /script:09b_nodewise_permutation.R -->

<!-- script:09c_stack_for_explorer.py -->
<details>
<summary>Script <code>09c_stack_for_explorer.py</code> (144 lines)</summary>

```python title="09c_stack_for_explorer.py"
#!/usr/bin/env python3
"""Step 9c. Stack the node-wise results into the file read by the Explorer.

Step 9b writes three small CSVs per analysis (one outcome x one tract x one metric) and
nothing ties them together.  The Explorer wants one long table with a row per node and
the analysis-level facts (N, covariates, extent threshold, whether a cluster passed)
repeated on every row of that analysis, so this script walks the permutation directory,
joins the three files of each analysis and stacks the lot into results_long.csv.  Plain
pandas, reads no environment variables, ignores FORCE; it recomputes on every run and
takes well under a second for a few dozen analyses.

    python 09c_stack_for_explorer.py /path/to/permutation/results
    python 09c_stack_for_explorer.py "$OUT/permutation"       # the usual call

The only argument is the directory Step 9b wrote to; with no argument the current
directory is used.  Every analysis in that directory is picked up, whatever its tract,
metric or outcome, so run 9b for everything you want to see in the Explorer first and
then run this once.

Expects the three outputs of 09b_nodewise_permutation.R for every analysis, named
<tract>__<metric>__<outcome>_nodewise.csv, _clusters.csv and _summary.csv.
    $OUT/permutation/<label>_summary.csv    one row; we read N_subjects, Covariates and
                                            ExtentThresholdNodes
    $OUT/permutation/<label>_nodewise.csv   one row per node; we read Node, t_value, p_value
    $OUT/permutation/<label>_clusters.csv   one row per cluster (header only if none); we
                                            read ClusterPValue and PassExtentThreshold
The _summary.csv files drive the loop.  A summary whose _nodewise or _clusters partner
is missing stops the run with a FileNotFoundError rather than being skipped; rerun 9b
for that analysis and try again.

Output: results_long.csv in the same directory, one row per node, with columns
    outcome, tract, metric, node, t, p, hemisphere, N, covariates,
    extent_threshold, cluster_p, passed
hemisphere is L or R when the tract name contains the token l or r (l_vta_l_hipp,
anterior_r_vta_r_hipp) and is otherwise empty; cluster_p and passed
describe the largest cluster of the analysis that met the extent threshold.
An existing results_long.csv is overwritten without asking.

What to look at when it finishes.  One line, "wrote .../results_long.csv (N rows,
K analyses)".  K should equal the number of 9b calls you made and N should be 100 x K.
A "skipped" line above it names a summary file whose name did not split into three
double-underscore fields: a 9b label with fewer than two "__" in it, or some other
*_summary.csv sitting in the directory.  Extra "__" are not caught (see the loop).

Where the file goes next: open the Explorer (the Explorer page of the tutorial) and
load results_long.csv there; it is read in the browser and not uploaded anywhere.  The
Explorer derives clusters and significant-node counts from the t and p columns itself,
marks clusters at least extent_threshold nodes long as passing and takes its FWE verdict
from that; N, covariates and cluster_p are shown as given.  passed is only read when
extent_threshold is absent, but 9b defines both by the same rule, so they agree.
"""
import sys
from pathlib import Path

# Standard library plus pandas; nothing from the imaging stack is needed for this step.
import pandas as pd

# sys.argv[1] is the first word after the script name on the command line.  Falling back
# to "." lets you cd into $OUT/permutation and run the script bare.  Path() gives us the
# / operator and .glob() below instead of string concatenation.
results_dir = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
# One dict per node row, collected here and turned into a DataFrame once at the end;
# appending to a DataFrame inside the loop would copy the whole table every time.
rows = []

# One analysis per _summary.csv.  sorted() fixes the row order of results_long.csv run to
# run; glob's own order is whatever the filesystem hands back.
for summary_file in sorted(results_dir.glob("*_summary.csv")):
    # Strip the suffix to recover the label 9b was called with, then split it on the
    # double underscore into tract, metric and outcome.  The 2 is maxsplit: at most two
    # splits, so an outcome containing "__" survives intact, but a tract or metric with
    # "__" in it is mis-split without complaint (a__b__NDI__out gives tract a, metric b,
    # outcome NDI__out), so keep "__" out of TRACT.  Fewer than two "__" gives fewer
    # than three parts, which is what the check catches.  Skipping rather than stopping
    # keeps one odd file from blocking the rest.
    label = summary_file.name[:-len("_summary.csv")]
    parts = label.split("__", 2)
    if len(parts) != 3:
        print(f"skipped {summary_file.name}: label is not <tract>__<metric>__<outcome>")
        continue
    tract, metric, outcome = parts

    # The summary file has exactly one row, so .iloc[0] turns it into a Series and the
    # summary[...] lookups below return scalars rather than one-element columns.
    summary = pd.read_csv(summary_file).iloc[0]
    nodewise = pd.read_csv(results_dir / f"{label}_nodewise.csv")
    clusters = pd.read_csv(results_dir / f"{label}_clusters.csv")
    # Clusters whose extent survived the permutation test (cluster p <= .05 in 9b).
    # readr writes R logicals as TRUE/FALSE; pandas reads those back as a boolean column
    # when there are rows and as an empty object column when 9b formed no
    # clusters.  Casting to str and upper-casing makes the comparison work either way.
    passing = clusters[clusters["PassExtentThreshold"].astype(str).str.upper() == "TRUE"]

    # Hemisphere from the tract name: the first underscore-separated token that is
    # exactly l or r (l_vta_l_hipp -> L, anterior_r_vta_r_hipp -> R).  A tract without
    # such a token gets "" and the Explorer shows it with no hemisphere label.  The
    # left-right panel pairs an L analysis with an R one whose tract name matches once
    # the l/r tokens are stripped, same outcome and metric, so name the two sides alike.
    # next() with a second argument returns the first match or that default if none.
    tokens = tract.lower().split("_")
    hemisphere = next((t.upper() for t in tokens if t in ("l", "r")), "")

    # One output row per node.  itertuples() yields each row as a namedtuple, so the 9b
    # columns are attributes (node.Node, node.t_value).  The analysis-level values are
    # repeated on every row on purpose: the Explorer reads them off the node rows.  The
    # Explorer would accept 9b's Node/t_value/p_value names too; the short names are
    # the documented format.
    for node in nodewise.itertuples():
        rows.append({
            "outcome": outcome, "tract": tract, "metric": metric,
            # t and p are rounded to keep the file readable.  A node 9b could not fit
            # (metric constant across participants, or collinear with the covariates) is
            # NA in R, NaN here, and lands in the CSV as an empty cell.
            "node": int(node.Node), "t": round(node.t_value, 4), "p": round(node.p_value, 5),
            # N is the number of participants 9b actually modelled, those with a complete
            # outcome, covariates and profile, not the length of $SUBJECTS_FILE.
            "hemisphere": hemisphere, "N": int(summary["N_subjects"]),
            "covariates": summary["Covariates"],
            # Smallest cluster length (adjacent nodes with p < .05) whose permutation p is
            # <= .05, so any cluster at least this long passes; same number on every row.
            "extent_threshold": int(summary["ExtentThresholdNodes"]),
            # cluster_p is the smallest p among the passing clusters, which is the p of
            # the longest one since 9b's cluster p only falls as extent grows; "" when
            # nothing passed.  passed is 1 if at least one cluster passed, else 0.  Both
            # describe the analysis, not the node, so a node outside every cluster
            # carries them too.
            "cluster_p": passing["ClusterPValue"].min() if len(passing) else "",
            "passed": int(len(passing) > 0),
        })

# No rows means no *_summary.csv here (wrong directory, or 9b has not run yet) or every
# one was skipped.  sys.exit with a string prints it to stderr and exits with status 1,
# so nothing is written.
if not rows:
    sys.exit(f"no *_summary.csv files found in {results_dir}")
# index=False stops pandas from writing its 0..N-1 row numbers as an unnamed first
# column.  That matters here because the Explorer treats any column it does not know as a
# grouping variable: a filter, and part of what tells one analysis from the next, so a
# column of row numbers would split every node into its own analysis.
out = results_dir / "results_long.csv"
pd.DataFrame(rows).to_csv(out, index=False)
# The analysis count assumes 100 nodes per analysis (integer division).  If the row count
# is not a whole multiple of 100, some analysis was profiled at a different node count.
print(f"wrote {out} ({len(rows)} rows, {len(rows) // 100} analyses)")
```

</details>
<!-- /script:09c_stack_for_explorer.py -->

