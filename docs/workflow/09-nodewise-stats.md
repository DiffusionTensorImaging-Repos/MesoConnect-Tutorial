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
| Whole tract | Metric averaged across nodes; one value per participant per tract | Is the metric associated with the outcome; does the association differ between subregional tracts | None within tract; across outcomes as pre-specified | `final_models.py` |
| Quartiles | Metric averaged within nodes 0–24, 25–49, 50–74, 75–99 | Does the association vary along the tract; is it confined to a segment | False discovery rate (FDR) or maximum-statistic permutation across the four quartiles | `final_models.py` |
| Nodes | Metric at each of 100 nodes | Where along the tract is the association located | Cluster-extent family-wise error (FWE) by permutation | `permutation_one.R` |

## Whole-tract model

The metric is averaged across all 100 nodes, or across the retained range if end nodes are trimmed, and regressed on the outcome and covariates. When two subregional tracts share most of their course (posterior and anterior VTA → hippocampus), both are entered in one mixed model with a subregion term, two rows per participant, a random intercept for participant, and each row carrying its own streamline length and count. The metric × subregion interaction is tested by likelihood ratio; when it does not improve fit, the main effect is reported. This resolution has the greatest power when the effect is distributed along the tract, and it does not localize the effect.

## Quartile model

The same model is fitted with the metric averaged within each quartile. Because adjacent quartiles are correlated, correction across the four should either use the FDR or a maximum-statistic permutation that preserves their dependence. Uniformity along the tract is tested directly by contrasting the seed-end quartile against the target-end quartile with the mean and the difference entered together: when the mean carries the effect and the difference does not differ from zero, the effect is diffuse rather than localized.

## Node-wise model

At each node the outcome is regressed on the node's metric and the covariates, and the fit is compared with a reduced model omitting the metric.

```r
full    ~ metric_node + ICV + tract_length + streamline_count + motion + age
reduced ~               ICV + tract_length + streamline_count + motion + age
```

The observed *t* statistic at each node is evaluated against a Freedman–Lane permutation distribution (Freedman & Lane, 1983; Winkler et al., 2014): the residuals of the reduced model are permuted, all 100 nodes are refitted, and the procedure is repeated 5,000 times. Adjacent nodes with *p* < .05 form clusters, and a cluster is retained when its extent equals or exceeds the 95th percentile of the null distribution of maximum cluster extent. The script reads the wide analysis file produced in Step 8b and is called once per outcome, tract and metric: `Rscript permutation_one.R <analysis.csv> <outcome> <METRIC>_ <out_dir> <label>`. Covariate column names are taken from the `R_COVARIATES` environment variable (comma-separated; the default matches the example dataset). Outputs per analysis are `_nodewise.csv` (node, estimate, *t*, *p*), `_clusters.csv` and `_summary.csv`; each call requires a few minutes on one core.

This resolution localizes an effect along the tract. Its limitation is that cluster-extent correction detects contiguous runs of supra-threshold nodes; when an effect is uniform along the tract, per-node *t* statistics remain near threshold at every node and the outcome becomes sensitive to small changes in model specification. In that situation node-wise results are descriptive and the whole-tract or quartile model carries the inference.

## Covariates

Covariates comprise intracranial volume (ICV), mean streamline length and streamline count for the tract, absolute head motion and age. Length and count are tract-specific and index reconstruction quality. Streamline count can be strongly correlated with the metric under test (up to *r* = .80 with NDI in the example dataset), which reduces the residual variance available to the test. Its inclusion should be decided in advance and both specifications reported.

## Choosing a resolution

A hypothesis about a particular segment of a pathway calls for the quartile or node-wise model. A hypothesis about the pathway as a whole calls for the whole-tract model. Exploratory work is often best served by the whole-tract model for inference with the node-wise profile reported as description. Tests across several metrics, tracts and outcomes accumulate rapidly at any resolution; fixing the analytic hierarchy in advance (primary metric, primary outcome family) is more readily justified than correcting across all tests afterwards.

In the example dataset, three social-memory measures were associated with NDI in the whole-tract model with no subregion interaction. In the quartile model one of them (positivity bias in false memories) was significant in all four quartiles and the seed-end versus target-end contrast was null for all three, indicating uniform effects. Node-wise clusters were located at nodes 27 to 55 and changed with covariate specification. The results were therefore reported with the whole-tract model as primary, the quartile model as confirmation of uniformity, and node-wise profiles as description. The script `final_models.py`, shown below, reproduces the whole-tract and quartile analyses for that dataset.

## Preparing node-wise results for the Explorer

Node-wise outputs are stacked into a single long-format file for the Node-wise Tract Explorer, the browser-based viewer described in the [Explorer section](../explorer).

```bash
python 09_stack_for_explorer.py /path/to/permutation/results   # writes results_long.csv
```

The file contains one row per node with the columns `outcome, tract, metric, node, t, p`, together with `hemisphere, N, covariates, extent_threshold, cluster_p` and `passed`.

## Scripts

<!-- script:permutation_one.R -->
```r title="permutation_one.R"
# =========================================================================
# Node-wise cluster-extent permutation test (Freedman–Lane)
# Adapted from a reference implementation used in atlas construction
# =========================================================================
# Args (positional):
#   1. data_csv       — path to analysis-ready CSV
#   2. response_col   — outcome name (e.g. SOCIAL_dprime)
#   3. metric_prefix  — metric prefix incl underscore (e.g. FA_, NDI_, ODI_, FWF_)
#   4. out_dir        — output directory for results
#   5. base_label     — short label for filenames (e.g. lhpost_FA_SOCIAL_dprime)
# =========================================================================
suppressPackageStartupMessages({
  library(readr); library(dplyr); library(stringr)
  library(foreach); library(doParallel); library(parallel); library(tibble)
})

args <- commandArgs(trailingOnly = TRUE)
stopifnot(length(args) >= 5)
data_csv      <- args[1]
response_col  <- args[2]
metric_prefix <- args[3]
out_dir       <- args[4]
base          <- args[5]

# Covariates: set R_COVARIATES (comma-separated) to match the columns in the analysis CSV
covariate_cols <- strsplit(Sys.getenv("R_COVARIATES", unset = "ICV,Mean_tckstats,Count_tckstats,absolute_motion,maternal_age"), ",")[[1]]

alpha_node       <- 0.05
alpha_familywise <- 0.05
num_permutations <- as.integer(Sys.getenv("R_PERM_N", unset = "5000"))
rng_seed         <- 123
use_parallel     <- TRUE

dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

dat <- readr::read_csv(data_csv, show_col_types = FALSE)

# Collect node columns
node_cols <- grep(paste0("^", metric_prefix, "\\d+$"), names(dat), value = TRUE)
if (length(node_cols) == 0) {
  stop("No columns matching ", metric_prefix, "0.. in: ", data_csv)
}
node_idx  <- as.integer(sub(paste0("^", metric_prefix), "", node_cols))
ord       <- order(node_idx)
node_cols <- node_cols[ord]; node_idx <- node_idx[ord]
num_nodes <- length(node_cols)

# Numeric casts
dat[[response_col]] <- as.numeric(dat[[response_col]])
for (cc in covariate_cols) dat[[cc]] <- as.numeric(dat[[cc]])

# Drop incomplete
all_model_cols <- c(response_col, covariate_cols, node_cols)
mask <- complete.cases(dat[, all_model_cols])
n_dropped <- sum(!mask)
if (n_dropped) message("Dropping ", n_dropped, " incomplete subjects")
dat <- dat[mask, , drop = FALSE]
n_subj <- nrow(dat)
if (n_subj < 5) {
  message("Fewer than 5 complete subjects (", n_subj, ") — skipping ", base)
  quit(status = 0)
}

y <- dat[[response_col]]

# Formulas
full_formula <- as.formula(
  paste("y ~ node +", paste(covariate_cols, collapse = " + "))
)
red_formula  <- as.formula(
  paste("y ~", paste(covariate_cols, collapse = " + "))
)

# Nodewise fit
fit_node_full <- function(y, node, covariates_df) {
  df0 <- data.frame(y = y, node = node, covariates_df)
  df0 <- df0[complete.cases(df0), ]
  if (nrow(df0) < 3 || sd(df0$node) == 0)
    return(c(Estimate=NA, t=NA, p=NA, df=NA, n=nrow(df0)))
  fit <- lm(full_formula, data = df0)
  sm <- summary(fit)$coefficients
  if (!("node" %in% rownames(sm)))
    return(c(Estimate=NA, t=NA, p=NA, df=fit$df.residual, n=nrow(df0)))
  tval <- unname(sm["node","t value"])
  est  <- unname(sm["node","Estimate"])
  pval <- 2*pt(-abs(tval), df=fit$df.residual)
  c(Estimate=est, t=tval, p=pval, df=fit$df.residual, n=nrow(df0))
}

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

# Cluster helpers
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
max_cluster_size_from_sig <- function(sig, nodes_numeric) {
  cls <- clusters_from_sig(sig, nodes_numeric)
  if (length(cls)==0) 0L else max(vapply(cls, length, 1L))
}

sig_mask <- !is.na(node_stats_df$p_value) & node_stats_df$p_value < alpha_node
obs_clusters <- clusters_from_sig(sig_mask, node_stats_df$Node)
obs_sizes <- vapply(obs_clusters, length, 1L)
obs_max_size <- if (length(obs_sizes)) max(obs_sizes) else 0L
num_sig_nodes <- sum(sig_mask)
num_clusters  <- length(obs_clusters)

# Freedman-Lane
df_red_global <- data.frame(y=y, dat[, covariate_cols, drop=FALSE])
fit_red <- lm(red_formula, data=df_red_global)
yhat_red <- fitted(fit_red); resid_red <- resid(fit_red)

analysable <- vapply(seq_along(node_cols), function(i)
  sd(dat[[node_cols[i]]]) > 0, logical(1))

perm_fun <- function(.perm) {
  perm_idx <- sample.int(n_subj)
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

env_cores <- suppressWarnings(as.integer(Sys.getenv("R_PERM_CORES", unset = NA)))
if (!is.na(env_cores) && env_cores > 0L) {
  cores <- env_cores
} else {
  cores <- max(1L, parallel::detectCores() - 1L)
}

if (cores > 1L) {
  cl <- parallel::makeCluster(cores); registerDoParallel(cl)
  parallel::clusterSetRNGStream(cl, rng_seed)
  perm_max_sizes <- foreach(perm=1:num_permutations, .combine=c, .packages="stats") %dopar% perm_fun(perm)
  parallel::stopCluster(cl)
} else {
  perm_max_sizes <- vapply(1:num_permutations, perm_fun, integer(1))
}

extent_threshold <- as.integer(quantile(perm_max_sizes, probs=1-alpha_familywise, type=1))
cluster_p_from_size <- function(size) mean(perm_max_sizes >= size)

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
      PassExtentThreshold=length(nodes) >= extent_threshold
    )
  }))
} else {
  all_clusters_df <- tibble(
    ClusterID=integer(), Size=integer(), StartNode=integer(), EndNode=integer(),
    Nodes=character(), MeanTValue=double(), Direction=character(),
    MaxAbsTValue=double(), MaxAbsTNode=integer(),
    MeanEstimate=double(),
    ClusterPValue=double(), ExtentThresholdNodes=integer(), PassExtentThreshold=logical()
  )
}
write_csv(all_clusters_df, file.path(out_dir, paste0(base, "_clusters.csv")))

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
<!-- /script:permutation_one.R -->

<!-- script:final_models.py -->
```python title="final_models.py"
#!/usr/bin/env python3
"""
Final models for the VTA→hippocampus × motivated-memory analysis (ReadMe, Section C).

Reproduces the tables in §5b, §5c, §6b and §8 from the analysis-ready CSVs.

  1. Whole tract. NDI averaged over all 100 nodes, one value per subject per subregion,
     stacked long (two rows per subject: anterior, posterior). Mixed model:
         NDI ~ memory + subregion + ICV + tract length + streamline count + motion + age
     with a random intercept for subject; each row carries its own length and count.
     Fit by maximum likelihood. The interaction model adds memory × subregion and is
     compared by likelihood-ratio test (1 df). Main effect reported with the interaction dropped.
  2. Quartiles. Same model with NDI averaged within Q1 (nodes 0-24), Q2 (25-49),
     Q3 (50-74), Q4 (75-99).
  3. Metric comparison. The whole-tract model for ODI, FWF and FA.
  4. Hippocampal gray-matter NDI (corrected-dPar refit, scripts/run_noddi_gm.py), bilateral
     mean, regressed on each outcome with ICV, hippocampal volume, motion and age.
  5. HVLT. Collapsed whole-tract NDI (mean of both subregions) with each subregion's
     streamline count entered separately; trial 1, total recall, delayed recall.

Outcomes per domain: d′ (log-linear corrected), misattribution (false-alarm rate
residualised on criterion c), FABias (positive − negative false-alarm rate).

Out: data.check/final_models_summary.csv
"""
import os, warnings
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy.stats import chi2, pearsonr

warnings.filterwarnings('ignore')

BASE = os.environ.get('MC_EXAMPLE_ROOT', './example_dataset/')  # root of the example dataset's analysis-ready files
BIL  = BASE + 'data.check/analysis_ready_bilateral/'
HPC  = BASE + 'Impact-Analyses/hpc_density_gm.csv'
VOL  = BASE + 'Impact-Analyses/hpc_volumes.csv'
OUT  = BASE + 'data.check/final_models_summary.csv'

COVS = ['ICV', 'Mean_tckstats', 'Count_tckstats', 'absolute_motion', 'maternal_age']
COV  = ' + '.join(COVS)
OUTCOMES = [('Social FABias', 'SOCIAL_FABias'),
            ('Social d′', 'SOCIAL_dprime_loglinear'),
            ('Social misattribution', 'SOCIAL_misattrib'),
            ('Monetary FABias', 'MONETARY_FABias'),
            ('Monetary d′', 'MONETARY_dprime_loglinear'),
            ('Monetary misattribution', 'MONETARY_misattrib')]
SEGMENTS = [('Q1', 0, 25), ('Q2', 25, 50), ('Q3', 50, 75), ('Q4', 75, 100), ('Whole', 0, 100)]
z = lambda s: (s - s.mean()) / s.std()


def load(metric):
    a = pd.read_csv(BIL + f'vta_anthipp__{metric}__analysis.csv')
    p = pd.read_csv(BIL + f'vta_posthipp__{metric}__analysis.csv')
    nodes = [c for c in a.columns if c.startswith(metric + '_') and c.split('_')[-1].isdigit()]
    return a, p, nodes


def outcomes_table():
    """Memory outcomes keyed by Subject; misattribution computed here for both domains."""
    ref = pd.read_csv(BIL + 'vta_anthipp__NDI__analysis.csv').copy()
    for dom in ['SOCIAL', 'MONETARY']:
        m = ref[[f'{dom}_fa', f'{dom}_criterion']].dropna()
        ref[f'{dom}_misattrib'] = np.nan
        ref.loc[m.index, f'{dom}_misattrib'] = smf.ols(f'{dom}_fa ~ {dom}_criterion', m).fit().resid
    return ref[['Subject'] + [o for _, o in OUTCOMES] +
               ['hvlt_trial1', 'hvlt_totalrecall', 'hvlt_delayedrecall']]


Y = outcomes_table()


def long_frame(metric, lo, hi):
    a, p, nodes = load(metric)
    rows = []
    for sub, df in [('anterior', a), ('posterior', p)]:
        t = df[['Subject'] + COVS].copy()
        t['M'] = df[nodes].values.astype(float)[:, lo:hi].mean(1)
        t['subregion'] = sub
        rows.append(t.merge(Y, on='Subject', how='left'))
    return pd.concat(rows, ignore_index=True)


def mixed(L, o):
    d = L.dropna(subset=[o, 'M']).copy()
    d['Mz'] = z(d['M']); d['yz'] = z(d[o])
    m0 = smf.mixedlm(f'Mz ~ yz + subregion + {COV}', d, groups=d.Subject).fit(reml=False)
    m1 = smf.mixedlm(f'Mz ~ yz*subregion + {COV}', d, groups=d.Subject).fit(reml=False)
    p_int = chi2.sf(max(2 * (m1.llf - m0.llf), 0), 1)
    return p_int, m0.params['yz'], m0.pvalues['yz'], int(len(d) / 2)


rows = []
print('=== 1. WHOLE TRACT, NDI: memory × subregion mixed model ===')
print(f"  {'outcome':24s} {'n':>3s} {'interaction p':>14s} {'main b':>8s} {'main p':>8s}")
L = long_frame('NDI', 0, 100)
for lbl, o in OUTCOMES:
    pi, b, pm, n = mixed(L, o)
    rows.append(dict(analysis='whole_tract', metric='NDI', segment='Whole', outcome=lbl,
                     n=n, interaction_p=pi, main_b=b, main_p=pm))
    print(f"  {lbl:24s} {n:3d} {pi:14.3f} {b:+8.3f} {pm:8.4f}{' *' if pm < .05 else ''}")

print('\n=== 2. QUARTILES, NDI ===')
seg = {}
for s, lo, hi in SEGMENTS:
    Ls = long_frame('NDI', lo, hi)
    for lbl, o in OUTCOMES:
        seg[(s, lbl)] = mixed(Ls, o)
        if s != 'Whole':
            pi, b, pm, n = seg[(s, lbl)]
            rows.append(dict(analysis='quartile', metric='NDI', segment=s, outcome=lbl,
                             n=n, interaction_p=pi, main_b=b, main_p=pm))
for title, k in [('interaction p', 0), ('main-effect p', 2)]:
    print(f"  -- {title}")
    print(f"  {'outcome':24s}" + ''.join(f"{s:>8s}" for s, _, _ in SEGMENTS))
    for lbl, _ in OUTCOMES:
        print(f"  {lbl:24s}" + ''.join(f"{seg[(s, lbl)][k]:8.3f}" for s, _, _ in SEGMENTS))

print('\n=== 3. METRIC COMPARISON, whole tract: main-effect p ===')
mets = ['NDI', 'ODI', 'FWF', 'FA']
comp = {}
for met in mets:
    Lm = long_frame(met, 0, 100)
    for lbl, o in OUTCOMES:
        comp[(met, lbl)] = mixed(Lm, o)
        rows.append(dict(analysis='metric', metric=met, segment='Whole', outcome=lbl,
                         n=comp[(met, lbl)][3], interaction_p=comp[(met, lbl)][0],
                         main_b=comp[(met, lbl)][1], main_p=comp[(met, lbl)][2]))
print(f"  {'outcome':24s}" + ''.join(f"{m:>8s}" for m in mets))
for lbl, _ in OUTCOMES:
    print(f"  {lbl:24s}" + ''.join(f"{comp[(m, lbl)][2]:8.3f}" for m in mets))

print('\n=== 4. HIPPOCAMPAL GRAY-MATTER NDI (corrected dPar), bilateral, +HPC volume ===')
h = pd.read_csv(HPC); v = pd.read_csv(VOL)
a0 = pd.read_csv(BIL + 'vta_anthipp__NDI__analysis.csv')[['Subject', 'ICV', 'absolute_motion', 'maternal_age']]
d = a0.merge(Y, on='Subject').merge(h[['Subject', 'L_HPC_NDI', 'R_HPC_NDI']], on='Subject') \
      .merge(v[['Subject', 'L_HPC_vol_mm3', 'R_HPC_vol_mm3']], on='Subject', how='left')
d['NDI'] = d[['L_HPC_NDI', 'R_HPC_NDI']].mean(axis=1)
d['HPCvol'] = d[['L_HPC_vol_mm3', 'R_HPC_vol_mm3']].sum(axis=1)
print(f"  {'outcome':24s} {'n':>3s} {'beta':>8s} {'p':>8s}")
for lbl, o in OUTCOMES:
    x = d[['NDI', 'ICV', 'absolute_motion', 'maternal_age', 'HPCvol', o]].dropna().copy()
    for c in x.columns: x[c] = z(x[c])
    m = smf.ols(f'{o} ~ NDI + ICV + absolute_motion + maternal_age + HPCvol', x).fit()
    rows.append(dict(analysis='hpc_gm_ndi', metric='NDI', segment='ROI', outcome=lbl,
                     n=int(m.nobs), interaction_p=np.nan, main_b=m.params['NDI'], main_p=m.pvalues['NDI']))
    print(f"  {lbl:24s} {int(m.nobs):3d} {m.params['NDI']:+8.3f} {m.pvalues['NDI']:8.4f}"
          f"{' *' if m.pvalues['NDI'] < .05 else ''}")

print('\n=== 5. HVLT: collapsed whole-tract NDI, each subregion count entered separately ===')
a, p, nodes = load('NDI')
D = pd.DataFrame({'Subject': a['Subject'],
                  'WHOLE': (a[nodes].values.mean(1) + p[nodes].values.mean(1)) / 2,
                  'ICV': a['ICV'], 'mot': a['absolute_motion'], 'age': a['maternal_age'],
                  'len': (a['Mean_tckstats'] + p['Mean_tckstats']) / 2,
                  'cnt_a': a['Count_tckstats'], 'cnt_p': p['Count_tckstats']}).merge(Y, on='Subject')
for o, lbl in [('hvlt_trial1', 'HVLT trial 1'), ('hvlt_totalrecall', 'HVLT total recall'),
               ('hvlt_delayedrecall', 'HVLT delayed recall')]:
    x = D[['WHOLE', 'ICV', 'len', 'cnt_a', 'cnt_p', 'mot', 'age', o]].dropna().copy()
    for c in x.columns: x[c] = z(x[c])
    m = smf.ols(f'{o} ~ WHOLE + ICV + len + cnt_a + cnt_p + mot + age', x).fit()
    rows.append(dict(analysis='hvlt', metric='NDI', segment='Whole', outcome=lbl,
                     n=int(m.nobs), interaction_p=np.nan, main_b=m.params['WHOLE'], main_p=m.pvalues['WHOLE']))
    print(f"  {lbl:24s} {int(m.nobs):3d} {m.params['WHOLE']:+8.3f} {m.pvalues['WHOLE']:8.4f}"
          f"{' *' if m.pvalues['WHOLE'] < .05 else ''}")
hv = D[['hvlt_trial1', 'SOCIAL_dprime_loglinear']].dropna()
print(f"  r(HVLT trial 1, RAFT social d′) = {pearsonr(hv.iloc[:, 0], hv.iloc[:, 1])[0]:+.3f}  (n={len(hv)})")

pd.DataFrame(rows).to_csv(OUT, index=False)
print(f"\n-> wrote {OUT}")
```
<!-- /script:final_models.py -->

<!-- script:09_stack_for_explorer.py -->
```python title="09_stack_for_explorer.py"
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
```
<!-- /script:09_stack_for_explorer.py -->
