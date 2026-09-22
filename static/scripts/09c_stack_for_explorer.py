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
