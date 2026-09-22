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

Covariates comprise intracranial volume (ICV), the mean streamline length and streamline count of the cleaned bundle (written by Step 6), absolute head motion and age. Length and count are tract-specific and index reconstruction quality. Streamline count can be strongly correlated with the metric under test, which reduces the residual variance available to the test. Its inclusion should be decided in advance and both specifications reported.

## Choosing a resolution

A hypothesis about a particular segment of a pathway calls for the quartile or node-wise model. A hypothesis about the pathway as a whole calls for the whole-tract model. Exploratory work is often best served by the whole-tract model for inference with the node-wise profile reported as description. Tests across several metrics, tracts and outcomes accumulate rapidly at any resolution; fixing the analytic hierarchy in advance (primary metric, primary outcome family) is more readily justified than correcting across all tests afterwards.

## Preparing node-wise results for the Explorer

Node-wise outputs are stacked into a single long-format file for the Node-wise Tract Explorer, the browser-based viewer described in the [Explorer section](../explorer).

```bash
python 09c_stack_for_explorer.py "$OUT/permutation"   # writes results_long.csv in that directory
```

The file contains one row per node with the columns `outcome, tract, metric, node, t, p`, together with `hemisphere, N, covariates, extent_threshold, cluster_p` and `passed`.

## Scripts

<!-- script:09a_tract_models.py -->
<details>
<summary>Script <code>09a_tract_models.py</code> (165 lines)</summary>

```python title="09a_tract_models.py"
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
```

</details>
<!-- /script:09a_tract_models.py -->

<!-- script:09b_nodewise_permutation.R -->
<details>
<summary>Script <code>09b_nodewise_permutation.R</code> (243 lines)</summary>

```r title="09b_nodewise_permutation.R"
# =============================================================================
# Step 9b. Node-wise cluster-extent permutation test (Freedman-Lane)
# =============================================================================
# One lm per node (outcome ~ metric_node + covariates); runs of p < .05 nodes form
# clusters, tested against the longest cluster per permutation of reduced-model residuals.
# Input:  $OUT/analysis/<TRACT>__<METRIC>__analysis.csv from Step 8b
# Output: <out_dir>/<label>_{nodewise,clusters,summary}.csv (label = tract__metric__outcome)
# Run:    source 00_config.sh (COVARIATES, N_PERMUTATIONS, R_PERM_CORES), then
#   Rscript 09b_nodewise_permutation.R <analysis.csv> <outcome> <METRIC>_ <out_dir> <label>
# =============================================================================
suppressPackageStartupMessages({
  library(readr); library(dplyr); library(stringr)
  library(foreach); library(doParallel); library(parallel); library(tibble)
})

args <- commandArgs(trailingOnly = TRUE)
stopifnot(length(args) >= 5)
data_csv      <- args[1]
response_col  <- args[2]
metric_prefix <- args[3]    # "NDI_", underscore included; "NDI" alone matches nothing
out_dir       <- args[4]
base          <- args[5]    # <tract>__<metric>__<outcome>; every output name starts with it

# Covariates: comma-separated column names, exported by 00_config.sh
# Same list as Step 9a, so the two resolutions are comparable.
covariate_env <- Sys.getenv("COVARIATES", unset = "")
if (covariate_env == "") stop("COVARIATES is not set: run `source 00_config.sh` first")
covariate_cols <- strsplit(covariate_env, ",")[[1]]

# Settings.  alpha_node forms clusters; alpha_familywise is applied to the cluster p values.
alpha_node       <- 0.05
alpha_familywise <- 0.05
num_permutations <- as.integer(Sys.getenv("N_PERMUTATIONS", unset = "5000"))
rng_seed         <- 123
use_parallel     <- TRUE

dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

dat <- readr::read_csv(data_csv, show_col_types = FALSE)

# Collect node columns
node_cols <- grep(paste0("^", metric_prefix, "\\d+$"), names(dat), value = TRUE)
if (length(node_cols) == 0) {
  stop("No columns matching ", metric_prefix, "0.. in: ", data_csv)
}
# Sort by node number; the cluster code relies on node_idx increasing along the vector.
node_idx  <- as.integer(sub(paste0("^", metric_prefix), "", node_cols))
ord       <- order(node_idx)
node_cols <- node_cols[ord]; node_idx <- node_idx[ord]
num_nodes <- length(node_cols)

# Numeric casts (a stray text value makes readr read the whole column as text)
dat[[response_col]] <- as.numeric(dat[[response_col]])
for (cc in covariate_cols) dat[[cc]] <- as.numeric(dat[[cc]])

# Drop incomplete.  A participant missing any node is dropped entirely, so all nodes are
# fit on the same people and one shuffled residual vector serves every node.
all_model_cols <- c(response_col, covariate_cols, node_cols)
mask <- complete.cases(dat[, all_model_cols])
n_dropped <- sum(!mask)
if (n_dropped) message("Dropping ", n_dropped, " incomplete participants")
dat <- dat[mask, , drop = FALSE]
n_subj <- nrow(dat)
# Exit 0 so a shell loop under set -e carries on; the missing outputs mark the skip.
if (n_subj < 5) {
  message("Fewer than 5 complete participants (", n_subj, ") — skipping ", base)
  quit(status = 0)
}

y <- dat[[response_col]]

# Formulas
# The full model tests the node; the reduced model (covariates only) is what gets permuted.
full_formula <- as.formula(
  paste("y ~ node +", paste(covariate_cols, collapse = " + "))
)
red_formula  <- as.formula(
  paste("y ~", paste(covariate_cols, collapse = " + "))
)

# Nodewise fit
# OLS of the full model for one node; NA statistics when the node cannot be tested.
fit_node_full <- function(y, node, covariates_df) {
  df0 <- data.frame(y = y, node = node, covariates_df)
  df0 <- df0[complete.cases(df0), ]
  if (nrow(df0) < 3 || sd(df0$node) == 0)
    return(c(Estimate=NA, t=NA, p=NA, df=NA, n=nrow(df0)))
  fit <- lm(full_formula, data = df0)
  sm <- summary(fit)$coefficients
  if (!("node" %in% rownames(sm)))
    return(c(Estimate=NA, t=NA, p=NA, df=fit$df.residual, n=nrow(df0)))
  # p recomputed with the same formula the permutation loop uses, so the two agree.
  tval <- unname(sm["node","t value"])
  est  <- unname(sm["node","Estimate"])
  pval <- 2*pt(-abs(tval), df=fit$df.residual)
  c(Estimate=est, t=tval, p=pval, df=fit$df.residual, n=nrow(df0))
}

# Observed statistics
set.seed(rng_seed)
node_stats <- lapply(seq_along(node_cols), function(i) {
  fit_node_full(y, dat[[node_cols[i]]], dat[, covariate_cols, drop=FALSE])
})
node_stats <- do.call(rbind, node_stats)
node_stats_df <- tibble(
  Node=node_idx, Estimate=node_stats[,"Estimate"],
  t_value=node_stats[,"t"], p_value=node_stats[,"p"],
  df=node_stats[,"df"], n=node_stats[,"n"]
)
write_csv(node_stats_df, file.path(out_dir, paste0(base, "_nodewise.csv")))

# Cluster helpers.  Runs of consecutive node numbers among the significant nodes; one
# rule for the observed pass and every permutation, so they cannot drift apart.
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
# Longest cluster, or 0 when there is none; this one number per permutation is the null.
max_cluster_size_from_sig <- function(sig, nodes_numeric) {
  cls <- clusters_from_sig(sig, nodes_numeric)
  if (length(cls)==0) 0L else max(vapply(cls, length, 1L))
}

# Observed clusters; nodes with an NA p count as not significant and end a cluster.
sig_mask <- !is.na(node_stats_df$p_value) & node_stats_df$p_value < alpha_node
obs_clusters <- clusters_from_sig(sig_mask, node_stats_df$Node)
obs_sizes <- vapply(obs_clusters, length, 1L)
obs_max_size <- if (length(obs_sizes)) max(obs_sizes) else 0L
num_sig_nodes <- sum(sig_mask)
num_clusters  <- length(obs_clusters)

# Freedman-Lane: permuted y = reduced-model fit + shuffled residuals, so what the
# covariates explain stays with its owner (Freedman & Lane 1983; Winkler et al. 2014).
df_red_global <- data.frame(y=y, dat[, covariate_cols, drop=FALSE])
fit_red <- lm(red_formula, data=df_red_global)
yhat_red <- fitted(fit_red); resid_red <- resid(fit_red)

# Constant nodes have no slope to test; checked once here rather than inside the loop.
analysable <- vapply(seq_along(node_cols), function(i)
  sd(dat[[node_cols[i]]]) > 0, logical(1))

# All permutations are drawn once, up front, so the null is identical for any core count.
set.seed(rng_seed)
perm_mat <- vapply(seq_len(num_permutations), function(k) sample.int(n_subj),
                   integer(n_subj))

# One permutation: refit every analysable node, return the longest run of p < alpha_node.
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

# Core count: R_PERM_CORES overrides; otherwise every core but one.
env_cores <- suppressWarnings(as.integer(Sys.getenv("R_PERM_CORES", unset = NA)))
if (!is.na(env_cores) && env_cores > 0L) {
  cores <- env_cores
} else {
  cores <- max(1L, parallel::detectCores() - 1L)
}

# Run the permutations (a failing task says nothing useful; rerun with R_PERM_CORES=1).
if (cores > 1L) {
  cl <- parallel::makeCluster(cores); registerDoParallel(cl)
  perm_max_sizes <- foreach(perm = 1:num_permutations, .combine = c,
                            .packages = "stats") %dopar% perm_fun(perm)
  parallel::stopCluster(cl)
} else {
  perm_max_sizes <- vapply(1:num_permutations, perm_fun, integer(1))
}

# Cluster p: proportion of permutations whose longest cluster is at least as long.
# Extent threshold: one node above the (1 - alpha) quantile; type = 1 keeps it whole.
cluster_p_from_size <- function(size) mean(perm_max_sizes >= size)
extent_threshold <- as.integer(quantile(perm_max_sizes, probs = 1 - alpha_familywise,
                                        type = 1)) + 1L

# Cluster table.  PassExtentThreshold comes from the p value, so the two cannot disagree.
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
  # Header-only file with the same columns, so Step 9c still finds what it expects.
  all_clusters_df <- tibble(
    ClusterID=integer(), Size=integer(), StartNode=integer(), EndNode=integer(),
    Nodes=character(), MeanTValue=double(), Direction=character(),
    MaxAbsTValue=double(), MaxAbsTNode=integer(),
    MeanEstimate=double(),
    ClusterPValue=double(), ExtentThresholdNodes=integer(), PassExtentThreshold=logical()
  )
}
write_csv(all_clusters_df, file.path(out_dir, paste0(base, "_clusters.csv")))

# Summary.  Step 9c reads N_subjects, Covariates and ExtentThresholdNodes by name.
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
message("Done: ", base, " — clusters=", num_clusters,
        " sig nodes=", num_sig_nodes, " ext_thr=", extent_threshold)
```

</details>
<!-- /script:09b_nodewise_permutation.R -->

<!-- script:09c_stack_for_explorer.py -->
<details>
<summary>Script <code>09c_stack_for_explorer.py</code> (51 lines)</summary>

```python title="09c_stack_for_explorer.py"
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
```

</details>
<!-- /script:09c_stack_for_explorer.py -->

