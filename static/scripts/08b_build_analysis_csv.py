#!/usr/bin/env python3
"""Step 8b. Assemble the analysis files read by the Step 9 scripts.

Step 8 leaves the profiles in long format, one row per participant and node, so 100 rows
per participant and one column per metric.  The Step 9 models want the opposite shape,
one row per participant with the 100 node values spread across columns, sitting next to
the covariates, the outcomes and the two bundle statistics from Step 6.  This script does
that reshape and join once per metric.  It is plain pandas, ignores FORCE (everything is
recomputed on every run, which is cheap) and finishes in seconds on a full sample.

Run in a shell where 00_config.sh has been sourced:

    source 00_config.sh
    python 08b_build_analysis_csv.py

Inputs (all three must exist; a missing file is a pandas FileNotFoundError, not a skip)
    $OUT/nodewise/<TRACT>_nodewise_all_subjects.csv   node profiles (Step 8)
    $OUT/nodewise/<TRACT>_tract_stats.csv             cleaned-bundle count and length (Step 6)
    $COVARIATES_CSV                                   Subject, covariates, outcomes

Output, one file per metric, one row per participant:
    $OUT/analysis/<TRACT>__<METRIC>__analysis.csv
    Subject, covariates, outcomes, Streamline_count, Mean_length_mm, <METRIC>_0 ... <METRIC>_99

The double underscore in the name is what separates the fields, since TRACT itself has
single underscores in it (l_vta_l_hipp).  Step 9a rebuilds exactly this name from TRACT
and --metric, and Step 9b takes the path on its command line, so do not rename the files.

What to look at when it finishes.  One "<file>: N participants, 100 nodes" line per
metric (FA alone if Step 8a was skipped; FA, NDI, ODI, FWF otherwise).  N is the number
of participants who have a covariate row AND a cleaned bundle AND a profile, so it can be
smaller than subjects.txt.  Anyone profiled in Step 8 but missing from the covariate file
is named on a final line; add them to covariates.csv and rerun.  Nodes must read 100.

Where the files go next: python 09a_tract_models.py --metric NDI ... and
Rscript 09b_nodewise_permutation.R "$OUT/analysis/<TRACT>__NDI__analysis.csv" ...
both read them straight from $OUT/analysis.
"""
import os
import sys
from pathlib import Path

# Standard library plus pandas; no imaging libraries are needed for this step.
import pandas as pd


# Read one exported variable or stop with a clear message.  Argument: the variable name.
# Returns its value as a string.  os.environ only holds what the shell exported, which is
# why the docstring says "source 00_config.sh": every export in that file lands here.
# "bash 00_config.sh" would run it in a throwaway shell and export nothing.  sys.exit with
# a string prints it to stderr and exits with status 1, so a missing variable stops the
# run before any file is read or written.
def env(name):
    if name not in os.environ:
        sys.exit(f"{name} is not set: run `source 00_config.sh` first")
    return os.environ[name]


# Three config values are read: OUT and TRACT here, COVARIATES_CSV a few lines down.
# A stale TRACT (edited in 00_config.sh but not re-sourced) would silently build files for
# the wrong tract, so check the file names this script prints against what you meant.
OUT = Path(env("OUT"))
TRACT = env("TRACT")

# Load the three inputs.  dtype={"Subject": str} is not decoration.  Left to itself pandas
# guesses the ID type per file: an all-digit column comes back as integers (0123 turns
# into 123), and if one file also holds an ID like sub-01 it is read as text instead, and
# merge() then refuses to join the two ("trying to merge on int64 and object columns").
# Forcing str in all three keeps the IDs exactly as written in subjects.txt.
profiles = pd.read_csv(OUT / "nodewise" / f"{TRACT}_nodewise_all_subjects.csv",
                       dtype={"Subject": str})
tract_stats = pd.read_csv(OUT / "nodewise" / f"{TRACT}_tract_stats.csv", dtype={"Subject": str})
covariates = pd.read_csv(env("COVARIATES_CSV"), dtype={"Subject": str})
# Every column in the profile file that is not an identifier is a metric, so this list
# follows whatever Step 8 actually profiled and nothing here needs editing when METRICS
# changes there.  Tract is constant within the file (it is just TRACT) and is dropped.
metrics = [c for c in profiles.columns if c not in ("Subject", "Tract", "Node")]

# parents=True also creates $OUT if it is missing; exist_ok=True means no error on reruns.
analysis_dir = OUT / "analysis"
analysis_dir.mkdir(parents=True, exist_ok=True)

# One wide file per metric rather than one giant table.  Step 9 is run per metric anyway,
# and a 100-column file is easier to open and eyeball than a 400-column one.
for metric in metrics:
    # Long to wide.  Participants become rows, the 100 Node values become 100 columns, and
    # each cell is this metric's value at that node.  pivot() refuses to guess if a
    # participant/node pair appears twice ("Index contains duplicate entries"); the usual
    # cause is an ID listed twice in subjects.txt, since Step 8 then profiles it twice.
    # A participant with fewer than 100 rows would get NaN at the missing nodes.  Step 8
    # always writes all 100, but if it happened 9b would drop them and 9a would average
    # over the nodes present.
    wide = profiles.pivot(index="Subject", columns="Node", values=metric)
    # pivot() leaves bare node numbers (0 ... 99) as the column labels.  Rename them to
    # NDI_0 ... NDI_99 so each column says which metric it is.  This naming is a contract
    # with both Step 9 scripts (9a rebuilds f"{METRIC}_{node}", 9b greps ^<METRIC>_\d+$),
    # so keep prefix, underscore, integer.  int() strips a stray .0 if Node were ever read
    # back as float.
    wide.columns = [f"{metric}_{int(node)}" for node in wide.columns]
    # Only the two bundle statistics travel on; Count_uncleaned and Retention_pct stay in
    # the Step 6 table.  Both are in COVARIATES by default (00_config.sh), so they have to
    # be in this file or Step 9a stops with "columns not found".  00_config.sh also has the
    # note on why Streamline_count is the covariate to think twice about.
    bundle = tract_stats[["Subject", "Streamline_count", "Mean_length_mm"]]
    # Two inner joins on Subject (pandas' default, how="inner").  A participant survives
    # only with a covariate row, a Step 6 row (a cleaned bundle) and a Step 8 profile.
    # Dropping rather than padding with NaN is deliberate, since Step 9 drops incomplete
    # rows anyway, but it is why the count printed below can be smaller than subjects.txt;
    # the check at the bottom names the ones lost at the covariate join.  wide carries
    # Subject as its index after pivot(), so reset_index() turns it back into a column
    # that merge() can match on.
    table = covariates.merge(bundle, on="Subject").merge(wide.reset_index(), on="Subject")
    # index=False stops pandas writing its own 0..N-1 row index as an unnamed first
    # column, which would only be clutter in every downstream file.
    path = analysis_dir / f"{TRACT}__{metric}__analysis.csv"
    table.to_csv(path, index=False)
    # The line to read.  Participants is the number of IDs present in all three inputs,
    # so never more than the smallest of them; nodes should be 100.
    print(f"{path.name}: {len(table)} participants, {wide.shape[1]} nodes")

# Who fell out at the covariate join.  "profiled - covariates" is set arithmetic, the IDs
# in the first set that are not in the second.  Only this direction is reported because
# it is the one you fix here, by adding rows to covariates.csv and rerunning; a
# participant missing from tract_stats has no _cleaned.tck, and Step 6 prints a SKIP
# line for the usual reasons (no tractogram, 0 streamlines).  The reverse case (in the
# covariate file but never profiled) is silent, so compare the counts above with
# wc -l subjects.txt if they look low.  Nothing is printed when the sets match.
profiled = set(profiles["Subject"])
absent = sorted(profiled - set(covariates["Subject"]))
if absent:
    print(f"profiled but absent from the covariate file: {', '.join(absent)}")
