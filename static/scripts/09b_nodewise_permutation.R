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
