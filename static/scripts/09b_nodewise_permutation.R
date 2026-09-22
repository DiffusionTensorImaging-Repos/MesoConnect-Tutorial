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
