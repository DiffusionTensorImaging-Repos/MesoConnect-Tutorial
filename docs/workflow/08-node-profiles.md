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
<summary>Script <code>08_node_profiles.py</code> (118 lines)</summary>

```python title="08_node_profiles.py"
#!/usr/bin/env python3
"""Step 8. Along-tract profiles at 100 nodes (AFQ, Gaussian-weighted).

Run in a shell where 00_config.sh has been sourced:

    source 00_config.sh
    python 08_node_profiles.py

Streamlines are first oriented to the bundle centroid and the centroid is oriented
so that it starts at the seed region; node 0 is therefore the seed end and node 99
the target end in every participant.  At each node, every streamline's value is
weighted by the inverse of its Mahalanobis distance from the bundle core
(Yeatman et al., 2012).

METRICS maps a column name to a scalar image; add or remove entries freely.  A metric
whose image exists for no participant (for example NODDI when Step 8a was not run) is
dropped with a notice; a participant missing any remaining image is skipped.

Output: $OUT/nodewise/<TRACT>_nodewise_all_subjects.csv
        (long format: Subject, Tract, Node, one column per metric)
"""
import os
import sys
from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd
from dipy.io.image import load_nifti
from dipy.io.streamline import load_tractogram
from dipy.segment.clustering import QuickBundles
from dipy.segment.featurespeed import ResampleFeature
from dipy.segment.metricspeed import AveragePointwiseEuclideanMetric
from dipy.stats.analysis import afq_profile, gaussian_weights
from dipy.tracking.streamline import Streamlines, orient_by_streamline


def env(name):
    if name not in os.environ:
        sys.exit(f"{name} is not set: run `source 00_config.sh` first")
    return os.environ[name]


PROJECT = Path(env("PROJECT"))
OUT = Path(env("OUT"))
TRACT = env("TRACT")
CUTOFF = env("CUTOFF")
SUBJECTS = Path(env("SUBJECTS_FILE")).read_text().split()

N_NODES = 100
MIN_STREAMLINES = 5
METRICS = {
    "FA": "dwi/{s}/fa.nii.gz",
    "NDI": "noddi/{s}/fit_NDI_modulated.nii.gz",
    "ODI": "noddi/{s}/fit_ODI_modulated.nii.gz",
    "FWF": "noddi/{s}/fit_FWF.nii.gz",
}


unavailable = [m for m, template in METRICS.items()
               if not any((PROJECT / template.format(s=s)).exists() for s in SUBJECTS)]
for m in unavailable:
    print(f"metric {m}: no image found for any participant; not profiled")
    del METRICS[m]
if not METRICS:
    sys.exit("no scalar images found")


def seed_centre_mm(s):
    """Centre of mass of the warped seed region, in scanner (mm) coordinates."""
    img = nib.load(str(OUT / s / "rois" / f"{TRACT}_seed_diff.nii.gz"))
    voxels = np.argwhere(img.get_fdata() > 0)
    return nib.affines.apply_affine(img.affine, voxels.mean(axis=0))


def orient_seed_to_target(streamlines, seed_mm):
    """Orient all streamlines alike, with node 0 at the seed end."""
    metric = AveragePointwiseEuclideanMetric(ResampleFeature(nb_points=N_NODES))
    centroid = QuickBundles(threshold=np.inf, metric=metric).cluster(streamlines).centroids[0]
    starts_at_target = (np.linalg.norm(centroid[0] - seed_mm)
                        > np.linalg.norm(centroid[-1] - seed_mm))
    if starts_at_target:
        centroid = centroid[::-1]
    return Streamlines(orient_by_streamline(streamlines, centroid))


def profile(image, streamlines, weights):
    data, affine = load_nifti(str(image))
    return afq_profile(data, streamlines, affine, n_points=N_NODES, weights=weights)


rows = []
for s in SUBJECTS:
    tck = OUT / s / "tckgen" / TRACT / f"{TRACT}_{CUTOFF}_cleaned.tck"
    maps = {m: PROJECT / template.format(s=s) for m, template in METRICS.items()}
    missing = [str(p) for p in [tck, *maps.values()] if not p.exists()]
    if missing:
        print(f"[{s}] SKIP: missing {missing[0]}")
        continue

    reference = next(iter(maps.values()))
    streamlines = load_tractogram(str(tck), str(reference), bbox_valid_check=False).streamlines
    if len(streamlines) < MIN_STREAMLINES:
        print(f"[{s}] SKIP: {len(streamlines)} streamlines")
        continue

    streamlines = orient_seed_to_target(streamlines, seed_centre_mm(s))
    weights = gaussian_weights(streamlines, n_points=N_NODES)
    profiles = {m: profile(p, streamlines, weights) for m, p in maps.items()}
    for node in range(N_NODES):
        rows.append({"Subject": s, "Tract": TRACT, "Node": node,
                     **{m: float(profiles[m][node]) for m in METRICS}})
    print(f"[{s}] {len(streamlines)} streamlines, {N_NODES} nodes, {len(METRICS)} metrics")

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
<summary>Script <code>08a_noddi_fit.py</code> (93 lines)</summary>

```python title="08a_noddi_fit.py"
#!/usr/bin/env python3
"""Step 8a. NODDI fit with AMICO (run before Step 8 when NODDI metrics are profiled).

Run in a shell where 00_config.sh has been sourced:

    source 00_config.sh
    python 08a_noddi_fit.py                  # every participant in $SUBJECTS_FILE
    python 08a_noddi_fit.py sub-01 sub-02    # selected participants

Writes fit_NDI, fit_ODI and fit_FWF, the tissue-weighted maps fit_NDI_modulated and
fit_ODI_modulated (Parker et al., 2021), and fit_RMSE.  Tract profiles use the
modulated NDI and ODI maps and the unmodulated FWF map.

The intrinsic parallel diffusivity defaults to the white-matter value (1.7e-3 mm2/s).
For gray-matter regions set NODDI_DPAR=1.1e-3; results are then written to
$PROJECT/noddi_gm so that white-matter maps are not overwritten.  Response kernels
are generated per participant (work/<subj>/kernels), so several instances of the
script can run concurrently on different participants.

Outputs: $PROJECT/noddi/<subj>/  (or $PROJECT/noddi_gm/<subj>/)
"""
import os
import sys
from pathlib import Path

N_THREADS = os.environ.get("NODDI_NTHREADS", "4")
os.environ["OPENBLAS_NUM_THREADS"] = N_THREADS     # must be set before amico is imported
os.environ["OMP_NUM_THREADS"] = N_THREADS

import amico


def env(name):
    if name not in os.environ:
        sys.exit(f"{name} is not set: run `source 00_config.sh` first")
    return os.environ[name]


PROJECT = Path(env("PROJECT"))
FORCE = os.environ.get("FORCE", "0") == "1"
SUBJECTS = sys.argv[1:] or Path(env("SUBJECTS_FILE")).read_text().split()

D_PAR = os.environ.get("NODDI_DPAR")     # mm2/s; unset = AMICO default for white matter
D_ISO = 3.0e-3                           # isotropic (free water) diffusivity, mm2/s
B0_THRESHOLD = 100                       # volumes with b below this are treated as b = 0
B_STEP = 200                             # b-values are rounded to the nearest multiple

STUDY = PROJECT / ("noddi_gm" if D_PAR else "noddi")
STUDY.mkdir(parents=True, exist_ok=True)
amico.setup()

for s in SUBJECTS:
    dwi_dir = PROJECT / "dwi" / s
    dwi = dwi_dir / "data.nii.gz"
    bvals = dwi_dir / "bvals"
    bvecs = dwi_dir / "bvecs"
    mask = dwi_dir / "nodif_brain_mask.nii.gz"
    out = STUDY / s

    if (out / "fit_NDI_modulated.nii.gz").exists() and not FORCE:
        print(f"[{s}] NODDI maps exist")
        continue
    missing = [p.name for p in (dwi, bvals, bvecs, mask) if not p.exists()]
    if missing:
        print(f"[{s}] SKIP: missing {', '.join(missing)}")
        continue
    # AMICO empties the output directory when it saves, so the scheme file and
    # the response kernels are kept in a separate working directory.
    work = STUDY / "work" / s
    work.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)

    scheme = work / f"{s}.scheme"
    amico.util.fsl2scheme(str(bvals), str(bvecs), str(scheme), bStep=B_STEP)

    ae = amico.Evaluation(str(STUDY), s, str(out))
    ae.set_config("nthreads", int(N_THREADS))
    ae.set_config("BLAS_nthreads", 1)
    ae.set_config("doSaveModulatedMaps", True)
    ae.set_config("doComputeRMSE", True)
    ae.load_data(str(dwi), str(scheme), str(mask), b0_thr=B0_THRESHOLD)

    ae.set_model("NODDI")
    ae.set_config("ATOMS_path", str(work / "kernels"))     # after set_model, which resets it
    if D_PAR:
        ae.model.set(float(D_PAR), D_ISO, ae.model.IC_VFs, ae.model.IC_ODs, False)
    ae.generate_kernels(regenerate=True)
    ae.load_kernels()
    ae.fit()
    ae.save_results()
    print(f"[{s}] NODDI maps written (dPar = {ae.model.dPar})")

print(f"DONE -> {STUDY}")
```

</details>
<!-- /script:08a_noddi_fit.py -->

## Analysis file

Inference in Step 9 reads a wide file with one row per participant: the covariates and outcomes, the streamline count and mean length of the cleaned bundle from Step 6, and the 100 node values as columns `<METRIC>_0` to `<METRIC>_99`. The script `08b_build_analysis_csv.py`, shown below, builds one such file per tract and metric from the long profile CSV, the tract statistics file and a participant-level covariates file (`COVARIATES_CSV` in the configuration; columns `Subject` plus covariates and outcomes).

<!-- script:08b_build_analysis_csv.py -->
<details>
<summary>Script <code>08b_build_analysis_csv.py</code> (55 lines)</summary>

```python title="08b_build_analysis_csv.py"
#!/usr/bin/env python3
"""Step 8b. Assemble the analysis files read by the Step 9 scripts.

Run in a shell where 00_config.sh has been sourced:

    source 00_config.sh
    python 08b_build_analysis_csv.py

Inputs
    $OUT/nodewise/<TRACT>_nodewise_all_subjects.csv   node profiles (Step 8)
    $OUT/nodewise/<TRACT>_tract_stats.csv             cleaned-bundle count and length (Step 6)
    $COVARIATES_CSV                                   Subject, covariates, outcomes

Output, one file per metric, one row per participant:
    $OUT/analysis/<TRACT>__<METRIC>__analysis.csv
    Subject, covariates, outcomes, Streamline_count, Mean_length_mm, <METRIC>_0 ... <METRIC>_99
"""
import os
import sys
from pathlib import Path

import pandas as pd


def env(name):
    if name not in os.environ:
        sys.exit(f"{name} is not set: run `source 00_config.sh` first")
    return os.environ[name]


OUT = Path(env("OUT"))
TRACT = env("TRACT")

profiles = pd.read_csv(OUT / "nodewise" / f"{TRACT}_nodewise_all_subjects.csv",
                       dtype={"Subject": str})
tract_stats = pd.read_csv(OUT / "nodewise" / f"{TRACT}_tract_stats.csv", dtype={"Subject": str})
covariates = pd.read_csv(env("COVARIATES_CSV"), dtype={"Subject": str})
metrics = [c for c in profiles.columns if c not in ("Subject", "Tract", "Node")]

analysis_dir = OUT / "analysis"
analysis_dir.mkdir(parents=True, exist_ok=True)

for metric in metrics:
    wide = profiles.pivot(index="Subject", columns="Node", values=metric)
    wide.columns = [f"{metric}_{int(node)}" for node in wide.columns]
    bundle = tract_stats[["Subject", "Streamline_count", "Mean_length_mm"]]
    table = covariates.merge(bundle, on="Subject").merge(wide.reset_index(), on="Subject")
    path = analysis_dir / f"{TRACT}__{metric}__analysis.csv"
    table.to_csv(path, index=False)
    print(f"{path.name}: {len(table)} participants, {wide.shape[1]} nodes")

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
