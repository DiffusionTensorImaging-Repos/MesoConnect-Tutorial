---
sidebar_position: 9
title: "Step 8. Node profiles"
---

# Step 8. Along-tract profiles

Each cleaned bundle is converted to a 100-point profile of a scalar map: fractional anisotropy (FA) from the tensor fit; the neurite density index (NDI), orientation dispersion index (ODI) and free-water fraction (FWF) from neurite orientation dispersion and density imaging (NODDI; Zhang et al., 2012); or any other map on the diffusion grid. Profiling follows the tract-profile approach of Yeatman et al. (2012) as implemented in DIPY (Garyfallidis et al., 2014).

Two operations make profiles comparable across participants. First, because streamlines in a tractogram file may run in either direction, each bundle is oriented against its QuickBundles centroid (Garyfallidis et al., 2012; `threshold=np.inf`, yielding one cluster), and the centroid is itself oriented so that it begins at the end nearer the warped seed region. Node 0 therefore corresponds to the seed end and node 99 to the target end in every participant. Second, `afq_profile` with `gaussian_weights` weights each streamline's contribution at a node by its Mahalanobis distance from the bundle core, reducing the influence of outlying streamlines.

## Procedure

```python
metric = AveragePointwiseEuclideanMetric(ResampleFeature(nb_points=100))
centroid = QuickBundles(threshold=np.inf, metric=metric).cluster(streamlines).centroids[0]
if distance(centroid[0], seed_centre) > distance(centroid[-1], seed_centre):
    centroid = centroid[::-1]                       # node 0 at the seed end
oriented = orient_by_streamline(streamlines, centroid)
weights = gaussian_weights(oriented, n_points=100)
profile = afq_profile(data, oriented, affine, n_points=100, weights=weights)
```

The `METRICS` dictionary in the script specifies the scalar maps; the script writes one long-format CSV per tract with one column per metric. Processing 57 participants and four tracts required 20 to 40 min.

<!-- script:08_node_profiles.py -->
<details>
<summary>Script <code>08_node_profiles.py</code> (251 lines)</summary>

```python title="08_node_profiles.py"
#!/usr/bin/env python3
"""Step 8. Along-tract profiles at 100 nodes (AFQ, Gaussian-weighted).

Run in a shell where 00_config.sh has been sourced:

    source 00_config.sh
    python 08_node_profiles.py

What this does.  For every participant it loads the cleaned bundle from Step 6, lines
the streamlines up so they all run seed -> target, resamples each one to 100 points
(nodes) and, at every node, averages a scalar map (FA, NODDI) over the streamlines.
The result is one curve of 100 values per metric per participant: the tract profile of
Yeatman et al. (2012), computed with DIPY's afq_profile.

Streamlines are first oriented to the bundle centroid and the centroid is oriented
so that it starts at the seed region; node 0 is therefore the seed end and node 99
the target end in every participant.  At each node, every streamline's value is
weighted by the inverse of its Mahalanobis distance from the bundle core
(Yeatman et al., 2012), so a stray that survived Step 6 counts for less than the core.

METRICS maps a column name to a scalar image; add or remove entries freely.  A metric
whose image exists for no participant (for example NODDI when Step 8a was not run) is
dropped with a notice; a participant missing any remaining image is skipped.

Needs, per participant:
    $OUT/<s>/tckgen/<TRACT>/<TRACT>_<CUTOFF>_cleaned.tck   cleaned bundle (Step 6)
    $OUT/<s>/rois/<TRACT>_seed_diff.nii.gz                 seed region in diffusion space
                                                           (Step 2); says which end is 0
    $PROJECT/dwi/<s>/fa.nii.gz                             FA map (preprocessing)
    $PROJECT/noddi/<s>/fit_*.nii.gz                        NODDI maps (Step 8a, optional)

Output: $OUT/nodewise/<TRACT>_nodewise_all_subjects.csv
        (long format: Subject, Tract, Node, one column per metric)
Step 8b pivots this into one wide file per metric for the Step 9 models.

Runtime: the tutorial page quotes 20 to 40 min for 57 participants and four tracts, so
roughly 5 to 10 min for one run of this script.  There is no FORCE switch; every run
rebuilds the CSV from scratch.

What to look for.  The DONE line gives the participant count, which should equal the
number of IDs in subjects.txt minus the SKIP lines above it; the CSV then has exactly
100 x that many rows (5,700 for 57 participants).  If you run both hemispheres, check
the orientation: the across-participant correlation of node i on the left with node i
on the right is strongly positive when both sides run seed -> target and strongly
negative when one side is reversed (Step 8 page, Verification).  Nodes 0-4 and 95-99
sit in or next to gray matter and are partial-volume mixtures; whether Step 9 trims
them (--trim in 09a) is a decision to make before modelling, not after.
"""
import os
import sys
from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd
# DIPY does the real work.  load_nifti and load_tractogram read the scalar maps and the
# .tck; QuickBundles with the feature and metric classes builds the bundle centroid;
# orient_by_streamline flips streamlines to match it; gaussian_weights and afq_profile
# are DIPY's implementation of the AFQ tract profile.
from dipy.io.image import load_nifti
from dipy.io.streamline import load_tractogram
from dipy.segment.clustering import QuickBundles
from dipy.segment.featurespeed import ResampleFeature
from dipy.segment.metricspeed import AveragePointwiseEuclideanMetric
from dipy.stats.analysis import afq_profile, gaussian_weights
from dipy.tracking.streamline import Streamlines, orient_by_streamline


# Read one exported variable, or stop with a hint.  Argument: the variable name.
# Returns its value as a string.  The Python steps cannot source 00_config.sh
# themselves; they only see what "source 00_config.sh" exported into the shell that
# launched them, so a missing name almost always means the config was not sourced (or
# was sourced in a different terminal).  sys.exit with a string prints it and exits 1.
def env(name):
    if name not in os.environ:
        sys.exit(f"{name} is not set: run `source 00_config.sh` first")
    return os.environ[name]


# Values from 00_config.sh.  PROJECT holds the raw data (dwi/, noddi/); OUT is where the
# workflow writes.  TRACT and CUTOFF are spliced into file names, so they must be the
# values Steps 5 and 6 ran with or the cleaned .tck is not found and everyone is
# skipped.  CUTOFF stays a string because it only ever appears in a file name.
PROJECT = Path(env("PROJECT"))
OUT = Path(env("OUT"))
TRACT = env("TRACT")
CUTOFF = env("CUTOFF")
# bash cannot export an array, so the ID list is re-read from the file.  read_text()
# gives the whole file as one string and split() breaks it on any whitespace, so blank
# lines, CRLF endings and a missing final newline are all harmless (the same tolerance
# read_subjects has in 00_config.sh).
SUBJECTS = Path(env("SUBJECTS_FILE")).read_text().split()

# 100 nodes is the AFQ convention and the rest of the workflow is built on it: Step 9a's
# quartiles are nodes 0-24, 25-49, 50-74, 75-99 and Step 9c counts analyses in blocks
# of 100.  Change this and those two need editing as well.
N_NODES = 100
# Below this many streamlines the participant is skipped rather than profiled.  A real
# bundle has hundreds (the smallest cleaned bundle in the example dataset had 659), so a
# handful means tracking or cleaning failed, not a bundle worth a curve.  The per-node
# covariance in gaussian_weights is also estimated across streamlines, so with this few
# the weights mean little.  Why exactly 5 is not written down anywhere.
MIN_STREAMLINES = 5
# Column name -> image path under $PROJECT, with {s} standing in for the participant ID.
# Every image must be in diffusion space, where the streamlines are; the first one is
# also the reference grid when the .tck is loaded.  NDI and ODI use the modulated
# (tissue-weighted) maps from Step 8a; FWF has no modulated form.  Add a line for any
# other diffusion-space map you want profiled; the key becomes the CSV column and, via
# Step 8b, the <METRIC> in the Step 9 file names.
METRICS = {
    "FA": "dwi/{s}/fa.nii.gz",
    "NDI": "noddi/{s}/fit_NDI_modulated.nii.gz",
    "ODI": "noddi/{s}/fit_ODI_modulated.nii.gz",
    "FWF": "noddi/{s}/fit_FWF.nii.gz",
}


# Drop any metric that no participant has an image for, e.g. the three NODDI entries
# when Step 8a was never run.  any(...) over the participants stops at the first image
# it finds, so this costs almost nothing.  The list is built first because a dict cannot
# shrink while it is being iterated.  A metric that exists for only some participants
# is kept; the participants without it are skipped in the main loop.
unavailable = [m for m, template in METRICS.items()
               if not any((PROJECT / template.format(s=s)).exists() for s in SUBJECTS)]
for m in unavailable:
    print(f"metric {m}: no image found for any participant; not profiled")
    del METRICS[m]
# Not even FA was found: PROJECT is probably wrong, or fa.nii.gz is not where the layout
# in 00_config.sh expects it.
if not METRICS:
    sys.exit("no scalar images found")


# Centre of mass of the participant's warped seed region.  Argument: participant ID.
# Returns (x, y, z) in scanner mm, the same space the streamlines are loaded into
# below, so the two can be compared directly.
# get_fdata() pulls the voxel array; argwhere lists the (i, j, k) index of every
# non-zero voxel; mean(axis=0) is their centroid in voxel units; apply_affine pushes
# that through the image's voxel-to-world matrix into mm.
def seed_centre_mm(s):
    """Centre of mass of the warped seed region, in scanner (mm) coordinates."""
    img = nib.load(str(OUT / s / "rois" / f"{TRACT}_seed_diff.nii.gz"))
    voxels = np.argwhere(img.get_fdata() > 0)
    return nib.affines.apply_affine(img.affine, voxels.mean(axis=0))


# Flip streamlines so they all run seed -> target.  Arguments: the loaded streamlines
# and the seed centre from seed_centre_mm.  Returns a new Streamlines object; the input
# is left alone.
# Streamlines in a .tck may run in either direction, so without this node 0 would be
# the seed end for some streamlines and the target end for others, and the profile
# would blend the two directions.
def orient_seed_to_target(streamlines, seed_mm):
    """Orient all streamlines alike, with node 0 at the seed end."""
    # One reference streamline: the QuickBundles centroid.  ResampleFeature puts every
    # streamline on N_NODES points, AveragePointwiseEuclideanMetric compares two
    # streamlines by the mean distance between matching points, and threshold=np.inf
    # means "everything is close enough", so there is exactly one cluster and
    # .centroids[0] is its mean streamline.  QuickBundles tries each streamline both
    # ways before folding it into the running mean, so mixed directions in the file do
    # not smear the centroid (checked on a synthetic bundle with half of it reversed).
    metric = AveragePointwiseEuclideanMetric(ResampleFeature(nb_points=N_NODES))
    centroid = QuickBundles(threshold=np.inf, metric=metric).cluster(streamlines).centroids[0]
    # The centroid itself may run either way.  Compare its two ends with the seed
    # centre (np.linalg.norm is Euclidean distance) and, if the first point is the far
    # one, reverse it ([::-1] is the array backwards).  This is what makes node 0 the
    # seed end in every participant, not just "the same end within one participant".
    starts_at_target = (np.linalg.norm(centroid[0] - seed_mm)
                        > np.linalg.norm(centroid[-1] - seed_mm))
    if starts_at_target:
        centroid = centroid[::-1]
    # orient_by_streamline resamples each streamline and the centroid to 12 points,
    # sums the point-to-point distances as is and flipped, and reverses the streamline
    # when flipped is closer.  It works on a copy.  Streamlines() keeps the result as
    # the array-sequence type the DIPY calls below expect.
    return Streamlines(orient_by_streamline(streamlines, centroid))


# Sample one scalar map along the bundle.  Arguments: image path, the oriented
# streamlines, and the (n_streamlines x N_NODES) weight matrix from gaussian_weights.
# Returns a 1-D array of N_NODES values.
# load_nifti returns the voxel array and its voxel-to-world affine.  afq_profile
# resamples each streamline to n_points, reads the map at every point (the affine maps
# mm back to voxels; values are trilinearly interpolated between voxels), then averages
# across streamlines at each node with np.average and the given weights.  DIPY checks
# that the weights sum to 1 per node and raises otherwise.
def profile(image, streamlines, weights):
    data, affine = load_nifti(str(image))
    return afq_profile(data, streamlines, affine, n_points=N_NODES, weights=weights)


# Main loop, one participant at a time.  rows collects one dict per node per
# participant and becomes the CSV at the end.
rows = []
for s in SUBJECTS:
    # The cleaned bundle from Step 6.  CUTOFF is part of the name, so editing it in the
    # config after Step 5 points this at a file that does not exist.
    tck = OUT / s / "tckgen" / TRACT / f"{TRACT}_{CUTOFF}_cleaned.tck"
    # Full path of every scalar map for this participant, keyed by column name.
    maps = {m: PROJECT / template.format(s=s) for m, template in METRICS.items()}
    # The .tck and every map must exist.  [tck, *maps.values()] is one list of all the
    # paths (the * unpacks the dict values into it).  Only the first missing path is
    # printed, to keep the log readable; fix it, rerun, and see if there is another.
    missing = [str(p) for p in [tck, *maps.values()] if not p.exists()]
    if missing:
        print(f"[{s}] SKIP: missing {missing[0]}")
        continue

    # load_tractogram needs a reference image for the grid and affine.  Any of the maps
    # will do, since they all sit on the diffusion grid, so the first one is used
    # (next(iter(...)) is "the first value in the dict").  Streamlines come back in
    # scanner mm (DIPY's default space), the same units as seed_centre_mm.
    # bbox_valid_check=False: DIPY otherwise refuses a tractogram with any point outside
    # the image's bounding box; Step 6 turned the check off for these same files, so we
    # do too.  .streamlines drops the tractogram wrapper and keeps the coordinates.
    reference = next(iter(maps.values()))
    streamlines = load_tractogram(str(tck), str(reference), bbox_valid_check=False).streamlines
    # Too small to weight or to trust; see MIN_STREAMLINES above.
    if len(streamlines) < MIN_STREAMLINES:
        print(f"[{s}] SKIP: {len(streamlines)} streamlines")
        continue

    # Orientation first, then the weights: the weights are computed per node and only
    # make sense once node i is the same place along the bundle in every streamline.
    # gaussian_weights resamples to N_NODES and, at each node, takes the mean and
    # covariance of the streamline positions, computes each streamline's Mahalanobis
    # distance from that mean, and returns 1/distance normalised to sum to 1 across
    # streamlines.  Streamlines near the bundle core dominate the average; strays that
    # survived Step 6's 3 SD cut count for little.  The weights depend on geometry
    # only, so the same matrix is reused for every metric.
    streamlines = orient_seed_to_target(streamlines, seed_centre_mm(s))
    weights = gaussian_weights(streamlines, n_points=N_NODES)
    # One 100-value profile per metric, keyed by column name.
    profiles = {m: profile(p, streamlines, weights) for m, p in maps.items()}
    # Long format: one row per node with Subject, Tract and Node as keys and every
    # metric as a column.  The ** splices the metric values into the row dict; float()
    # turns each numpy scalar into a plain number.  Tract is constant within a run but
    # lets CSVs from several tracts be stacked and still told apart.
    for node in range(N_NODES):
        rows.append({"Subject": s, "Tract": TRACT, "Node": node,
                     **{m: float(profiles[m][node]) for m in METRICS}})
    print(f"[{s}] {len(streamlines)} streamlines, {N_NODES} nodes, {len(METRICS)} metrics")

# Write the table.  mkdir(parents=True, exist_ok=True) creates $OUT/nodewise if needed
# and is silent if it already exists.  index=False keeps pandas' row numbers out of the
# file.  len(rows) // N_NODES is the number of participants profiled; Step 8b reads
# this file next and pivots it to one wide row per participant.
out = OUT / "nodewise" / f"{TRACT}_nodewise_all_subjects.csv"
out.parent.mkdir(parents=True, exist_ok=True)
pd.DataFrame(rows).to_csv(out, index=False)
print(f"DONE -> {out}  ({len(rows) // N_NODES} participants)")
```

</details>
<!-- /script:08_node_profiles.py -->

## Node range

Nodes near the ends of the profile (0 to 4 and 95 to 99) lie in or adjacent to gray matter and are affected by partial-volume contamination from the seed and target regions. Deep white matter spans approximately nodes 25 to 75. Whether end nodes are trimmed should be decided before modelling.

## NODDI inputs

NODDI is fitted with AMICO (Daducci et al., 2015) on the eddy-corrected data; the script `08a_noddi_fit.py`, shown below, performs the fit. The modulated NDI and ODI maps (`fit_NDI_modulated.nii.gz`, `fit_ODI_modulated.nii.gz`), which incorporate the tissue-weighted partial-volume correction of Parker et al. (2021), are used for profiling; FWF has no modulated form and `fit_FWF.nii.gz` is used. Settings used in the example dataset were `bStep=200` during scheme conversion (rounding jittered *b*-values), `b0_thr=100`, `doSaveModulatedMaps=True`, `doComputeRMSE=True` and `BLAS_nthreads=1`. By default AMICO writes its response kernels to a directory shared by all participants, and concurrent jobs then delete one another's files; the script instead generates the kernels in a working directory for each participant, so several instances can be run at once on different participants (`python 08a_noddi_fit.py sub-01 sub-02`). AMICO also empties its output directory when saving, so nothing else should be stored there.

When NODDI is sampled within a gray-matter region (for example the hippocampus), the model should be refitted with the gray-matter intrinsic parallel diffusivity (approximately 1.1 × 10⁻³ mm²/s rather than the white-matter default of 1.7 × 10⁻³ mm²/s) by setting `NODDI_DPAR=1.1e-3`; the script then writes to `$PROJECT/noddi_gm` so that the white-matter maps are retained. The white-matter fit is not appropriate in gray matter and the two fits can yield different results.

<!-- script:08a_noddi_fit.py -->
<details>
<summary>Script <code>08a_noddi_fit.py</code> (192 lines)</summary>

```python title="08a_noddi_fit.py"
#!/usr/bin/env python3
"""Step 8a. NODDI fit with AMICO (run before Step 8 when NODDI metrics are profiled).

Fits the NODDI model (Zhang et al., 2012) to each participant's preprocessed diffusion
data with AMICO (Daducci et al., 2015).  AMICO recasts the fit as a linear problem
against a precomputed dictionary of response kernels, which is why a whole brain takes
minutes here rather than hours.  Step 8 then samples the maps along the cleaned bundle.
If you only want FA profiles, skip this script; Step 8 notices the missing maps and
drops the NODDI columns with a message.

Run in a shell where 00_config.sh has been sourced:

    source 00_config.sh
    python 08a_noddi_fit.py                  # every participant in $SUBJECTS_FILE
    python 08a_noddi_fit.py sub-01 sub-02    # selected participants

Needs, per participant (all from preprocessing; nothing from Steps 1 to 7):
    $PROJECT/dwi/<subj>/data.nii.gz               eddy-corrected multi-shell DWI
    $PROJECT/dwi/<subj>/bvals, bvecs              FSL-format b-values and directions
    $PROJECT/dwi/<subj>/nodif_brain_mask.nii.gz   brain mask; only voxels inside are fitted
NODDI needs at least two b > 0 shells; one shell cannot separate its compartments.

Writes fit_NDI, fit_ODI and fit_FWF, the tissue-weighted maps fit_NDI_modulated and
fit_ODI_modulated (Parker et al., 2021), and fit_RMSE.  Tract profiles use the
modulated NDI and ODI maps and the unmodulated FWF map.
    $PROJECT/noddi/<subj>/fit_NDI.nii.gz            neurite density index, 0 to 1
    $PROJECT/noddi/<subj>/fit_ODI.nii.gz            orientation dispersion index, 0 to 1
    $PROJECT/noddi/<subj>/fit_FWF.nii.gz            free-water (isotropic) fraction, 0 to 1
    $PROJECT/noddi/<subj>/fit_NDI_modulated.nii.gz  NDI x (1 - FWF)
    $PROJECT/noddi/<subj>/fit_ODI_modulated.nii.gz  ODI x (1 - FWF)
    $PROJECT/noddi/<subj>/fit_RMSE.nii.gz           fit error per voxel, for QC only
    $PROJECT/noddi/work/<subj>/                     scheme file and kernels; safe to delete
AMICO may add a few housekeeping files of its own next to the maps; Step 8 ignores them.
Step 8 (08_node_profiles.py) reads the two modulated maps and fit_FWF through its
METRICS dictionary.  The modulated maps matter: a plain NDI mean over a stretch of
tract that borders CSF is pulled around by how much free water each voxel holds;
weighting each voxel by its tissue fraction (1 - FWF) down-weights the CSF-heavy ones
(Parker et al., 2021).  FWF has no modulated form, so the plain map is profiled.

The intrinsic parallel diffusivity defaults to the white-matter value (1.7e-3 mm2/s).
For gray-matter regions set NODDI_DPAR=1.1e-3; results are then written to
$PROJECT/noddi_gm so that white-matter maps are not overwritten.  Response kernels
are generated per participant (work/<subj>/kernels), so several instances of the
script can run concurrently on different participants.  Step 8 reads noddi/ only; to
profile the gray-matter fit, point its METRICS entries at noddi_gm/ yourself.

Runtime: a few minutes per participant at four threads (NODDI_NTHREADS, default 4;
export it before running to change it); the per-participant kernels are part of that.
What to look for: one "NODDI maps written" line per participant, then open a fit_NDI
and fit_FWF pair in fsleyes.  NDI should be highest in dense white matter, ODI lowest
in the corpus callosum and FWF close to 1 in the ventricles.  fit_RMSE should be low
and fairly flat inside the brain; a region that lights up is where the model or the
data went wrong and is worth a look before profiling.

Outputs: $PROJECT/noddi/<subj>/  (or $PROJECT/noddi_gm/<subj>/)
"""
import os
import sys
from pathlib import Path

# Thread count for this process.  It is not in 00_config.sh; it comes straight from the
# environment, so "export NODDI_NTHREADS=8" before running changes it.  Peak load on a
# shared machine is this number times the instances you start (see the note on NTHREADS
# and MAXJOBS in 00_config.sh).
N_THREADS = os.environ.get("NODDI_NTHREADS", "4")
# numpy's BLAS (OpenBLAS in the pip wheels) is loaded when numpy is imported and reads
# these variables then, and "import amico" pulls numpy in.  Set them later and they do
# nothing.
os.environ["OPENBLAS_NUM_THREADS"] = N_THREADS     # must be set before amico is imported
os.environ["OMP_NUM_THREADS"] = N_THREADS

import amico


# Read one variable exported by 00_config.sh, or stop with a message that says which one
# is missing.  Every Python script in the workflow starts with this same helper.
def env(name):
    if name not in os.environ:
        sys.exit(f"{name} is not set: run `source 00_config.sh` first")
    return os.environ[name]


PROJECT = Path(env("PROJECT"))
# FORCE=1 in the environment (or in 00_config.sh) redoes participants whose maps exist.
FORCE = os.environ.get("FORCE", "0") == "1"
# IDs on the command line win; with none given, "or" falls through to the list in
# $SUBJECTS_FILE.  split() on whitespace tolerates CRLF endings and blank lines, the same
# things read_subjects in 00_config.sh guards against for the shell scripts.
SUBJECTS = sys.argv[1:] or Path(env("SUBJECTS_FILE")).read_text().split()

# Model constants.  dPar is the diffusivity along the neurites inside the stick
# compartment and is fixed, not fitted, so it has to suit the tissue: 1.7e-3 for white
# matter (AMICO's default, used when NODDI_DPAR is unset) and about 1.1e-3 for gray
# matter.  The white-matter value is not appropriate in gray matter, and the tutorial
# page notes the two fits can give different results.
D_PAR = os.environ.get("NODDI_DPAR")     # mm2/s; unset = AMICO default for white matter
# Free-water compartment, fixed at the diffusivity of water at body temperature; this is
# also AMICO's own default.
D_ISO = 3.0e-3                           # isotropic (free water) diffusivity, mm2/s
# Scanners often report small nonzero b (5, 10...) for the b = 0 volumes; anything under
# 100 is treated as b = 0 so those volumes normalise the signal instead of forming a shell.
B0_THRESHOLD = 100                       # volumes with b below this are treated as b = 0
# Jittered b-values (995, 1003...) are rounded to the nearest multiple of B_STEP so AMICO
# sees clean shells.  Keep it smaller than the gap between your closest shells or two
# shells can round to the same value, and check the scheme file once: a shell that is
# not itself a multiple gets moved (3250 becomes 3200), so its kernels are built for 3200.
B_STEP = 200                             # b-values are rounded to the nearest multiple

# Output tree.  The directory is chosen by whether NODDI_DPAR is set at all, not by its
# value, so a white-matter run with NODDI_DPAR=1.7e-3 exported would still land in
# noddi_gm.  Unset it for the normal run.
STUDY = PROJECT / ("noddi_gm" if D_PAR else "noddi")
STUDY.mkdir(parents=True, exist_ok=True)
# One-off AMICO housekeeping: precomputes the rotation matrices it uses to turn kernels
# towards each voxel's fibre direction and caches them as pickles in ~/.dipy.  The first
# call takes a while; later calls find the cache and return at once.
amico.setup()

for s in SUBJECTS:
    # Inputs come from preprocessing, in the layout 00_config.sh documents.
    dwi_dir = PROJECT / "dwi" / s
    dwi = dwi_dir / "data.nii.gz"
    bvals = dwi_dir / "bvals"
    bvecs = dwi_dir / "bvecs"
    mask = dwi_dir / "nodif_brain_mask.nii.gz"
    out = STUDY / s

    # Done already?  The modulated NDI map is the one Step 8 needs, so it is the test.
    if (out / "fit_NDI_modulated.nii.gz").exists() and not FORCE:
        print(f"[{s}] NODDI maps exist")
        continue
    # Report every missing input at once, then skip the participant.
    missing = [p.name for p in (dwi, bvals, bvecs, mask) if not p.exists()]
    if missing:
        print(f"[{s}] SKIP: missing {', '.join(missing)}")
        continue
    # AMICO empties the output directory when it saves, so the scheme file and
    # the response kernels are kept in a separate working directory.
    # The working directory is also per participant on purpose: AMICO's default puts
    # every participant's kernels in one shared folder, and two instances running at once
    # then delete each other's files (the FileNotFoundError listed in Troubleshooting).
    work = STUDY / "work" / s
    work.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)

    # AMICO reads the acquisition as one scheme file (a row per volume with the gradient
    # direction and b-value together), not FSL's separate bvals and bvecs.  fsl2scheme
    # converts them; bStep is the rounding described at B_STEP above.
    scheme = work / f"{s}.scheme"
    amico.util.fsl2scheme(str(bvals), str(bvecs), str(scheme), bStep=B_STEP)

    # Evaluation(study directory, participant ID, output_path) is AMICO's handle for one
    # fit.  Left to itself it would write under <study>/<ID>/AMICO/NODDI/; giving
    # output_path explicitly puts the maps straight in noddi/<subj>/ where Step 8 looks.
    ae = amico.Evaluation(str(STUDY), s, str(out))
    # nthreads: voxels fitted in parallel.  BLAS_nthreads: threads inside each linear
    # algebra call; 1 as on the tutorial page, so the two do not multiply and oversubscribe.
    ae.set_config("nthreads", int(N_THREADS))
    ae.set_config("BLAS_nthreads", 1)
    # Also write the tissue-weighted maps (NDI and ODI times 1 - FWF) that Step 8 profiles.
    ae.set_config("doSaveModulatedMaps", True)
    # Also write fit_RMSE, the per-voxel error between measured and fitted signal.
    ae.set_config("doComputeRMSE", True)
    # b0_thr is B0_THRESHOLD above.  Only voxels inside the mask are fitted; the rest
    # come out as zero in every map.
    ae.load_data(str(dwi), str(scheme), str(mask), b0_thr=B0_THRESHOLD)

    # set_model picks NODDI and, as a side effect, resets ATOMS_path (where the kernels
    # live) to AMICO's shared default, which is why the per-participant path is set only
    # afterwards.  Swap the order and the parallel-run problem above comes back.
    ae.set_model("NODDI")
    ae.set_config("ATOMS_path", str(work / "kernels"))     # after set_model, which resets it
    # model.set(dPar, dIso, IC_VFs, IC_ODs, isExvivo).  Only dPar changes here; IC_VFs
    # and IC_ODs are handed back unchanged so the kernel grid (the intra-cellular volume
    # fractions and dispersions AMICO tabulates) stays at its default, and False keeps
    # the in vivo model, i.e. no ex vivo "dot" compartment.
    if D_PAR:
        ae.model.set(float(D_PAR), D_ISO, ae.model.IC_VFs, ae.model.IC_ODs, False)
    # Build the kernel dictionary for this scheme and dPar in ATOMS_path.  regenerate=True
    # recomputes even if files are there, so a half-written set from a killed run is never
    # picked up.  load_kernels then projects them onto this participant's gradient scheme.
    ae.generate_kernels(regenerate=True)
    ae.load_kernels()
    # The fit itself: per voxel, a non-negative linear fit of the signal against the kernel
    # dictionary, then the kernel weights are turned into NDI, ODI and FWF.  save_results
    # writes the fit_*.nii.gz files into out (after clearing it; see the note at "work").
    ae.fit()
    ae.save_results()
    # dPar is printed so a log shows which tissue setting produced the maps.
    print(f"[{s}] NODDI maps written (dPar = {ae.model.dPar})")

print(f"DONE -> {STUDY}")
```

</details>
<!-- /script:08a_noddi_fit.py -->

## Analysis file

Inference in Step 9 reads a wide file with one row per participant: the covariates and outcomes, the streamline count and mean length of the cleaned bundle from Step 6, and the 100 node values as columns `<METRIC>_0` to `<METRIC>_99`. The script `08b_build_analysis_csv.py`, shown below, builds one such file per tract and metric from the long profile CSV, the tract statistics file and a participant-level covariates file (`COVARIATES_CSV` in the configuration; columns `Subject` plus covariates and outcomes).

<!-- script:08b_build_analysis_csv.py -->
<details>
<summary>Script <code>08b_build_analysis_csv.py</code> (131 lines)</summary>

```python title="08b_build_analysis_csv.py"
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
```

</details>
<!-- /script:08b_build_analysis_csv.py -->

## Example profiles

Figures 1 to 3 show profiles from one participant in the example dataset.

**Figure 1**

*Fractional Anisotropy Along the Left Posterior VTA → Hippocampus Tract*

![FA profile](/img/fig_profile_fa.png)

*Note.* FA peaks in deep white matter and declines toward the hippocampal end. VTA = ventral tegmental area.

**Figure 2**

*NODDI Indices Along the Same Bundle*

![NDI profile](/img/fig_profile_ndi.png)
![ODI profile](/img/fig_profile_odi.png)
![FWF profile](/img/fig_profile_fwf.png)

*Note.* NDI (top), ODI (middle) and FWF (bottom). NDI is high near the VTA and increases again toward the hippocampus; ODI is higher at both ends where fibres fan; FWF rises sharply at the hippocampal end adjacent to cerebrospinal fluid.

**Figure 3**

*NDI Along the Anterior Tract for the Same Participant*

![NDI profile, anterior tract](/img/fig_profile_ndi_anterior.png)

*Note.* The anterior tract shares the early trajectory and diverges late.

## Verification

The row count of each CSV should equal the number of participants × 100. In the example dataset every tract and metric produced 5,700 rows with no skipped participants.

When both hemispheres are processed, alignment should be confirmed before averaging. The across-participant correlation between node *i* on the left and node *i* on the right is strongly positive when the profiles are aligned (approximately *r* = .98 in the example dataset) and strongly negative when one side is reversed. Mid-tract averages (nodes 25 to 74) correlated across hemispheres at approximately *r* = .80 to .90 for NDI and ODI and *r* = .50 for FA.
