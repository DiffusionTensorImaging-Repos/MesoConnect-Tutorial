---
sidebar_position: 9
title: "8. Node profiles"
---

# Step 8. Along-tract profiles

Each cleaned bundle is converted to a 100-point profile of a scalar map: fractional anisotropy from the tensor fit, the neurite density index (NDI), orientation dispersion index (ODI) and free-water fraction (FWF) from NODDI (Zhang et al., 2012), or any other map on the diffusion grid. Profiling follows the tract-profile approach of Yeatman et al. (2012) as implemented in DIPY (Garyfallidis et al., 2014).

Two operations make profiles comparable across participants. First, because streamlines from `tckgen` run in either direction, each bundle is oriented against a QuickBundles centroid (Garyfallidis et al., 2012; `threshold=np.inf`, yielding one cluster) so that node 0 corresponds to the seed end and node 99 to the target end. The orientation should be confirmed once per tract by locating endpoint features in the profile. Second, `afq_profile` with `gaussian_weights` weights each streamline's contribution at a node by its Mahalanobis distance from the bundle core, reducing the influence of outlying streamlines.

## Procedure

```python
qb = QuickBundles(threshold=np.inf, metric=AveragePointwiseEuclideanMetric(ResampleFeature(nb_points=100)))
oriented = dts.orient_by_streamline(sl, qb.cluster(sl).centroids[0])
w = dsa.gaussian_weights(oriented)
profile = dsa.afq_profile(data, oriented, affine, nb_points=100, weights=w)
```

The full script, `08_node_profiles.py`, follows. The `METRICS` dictionary specifies the scalar maps; the script writes one long-format CSV per tract with one column per metric. Processing 57 participants and four tracts required 20 to 40 minutes.

## Scripts

<!-- script:08a_noddi_fit.py -->
```python title="08a_noddi_fit.py"
#!/usr/bin/env python3
"""Step 8a — NODDI fit with AMICO (run before step 8 if NODDI maps are wanted).

Writes $PROJECT/noddi/<subj>/fit_{NDI,ODI,FWF}.nii.gz plus fit_NDI_modulated / fit_ODI_modulated
(tissue-weighted partial-volume correction) and fit_RMSE.  Kernels are generated once; run this
script serially for the first participant before starting parallel jobs so that concurrent runs do
not regenerate the shared kernel directory.  Set NODDI_DPAR=1.1e-3 to refit for gray-matter ROIs
(white-matter default 1.7e-3).
"""
import os, sys
from pathlib import Path
import amico

PROJECT = Path(os.environ["PROJECT"]); subjects = [l.strip() for l in open(os.environ["SUBJECTS_FILE"]) if l.strip()]
if len(sys.argv) > 1: subjects = sys.argv[1:]
nthreads = int(os.environ.get("NODDI_NTHREADS", "4")); dpar = os.environ.get("NODDI_DPAR")
os.environ["OPENBLAS_NUM_THREADS"] = os.environ["OMP_NUM_THREADS"] = str(nthreads)
study = PROJECT / "noddi"; study.mkdir(exist_ok=True); amico.core.setup()

for s in subjects:
    d = PROJECT / "dwi" / s; out = study / s; out.mkdir(exist_ok=True)
    if os.environ.get("FORCE", "0") != "1" and (out / "fit_NDI_modulated.nii.gz").exists(): print(f"[{s}] exists"); continue
    dwi = Path(os.path.expandvars(os.environ.get("DWI_NII", "$PROJECT/dwi/$s/data.nii.gz").replace("$s", s)))
    bval = Path(os.path.expandvars(os.environ.get("BVALS", "$PROJECT/dwi/$s/bvals").replace("$s", s)))
    bvec = Path(os.path.expandvars(os.environ.get("BVECS", "$PROJECT/dwi/$s/bvecs").replace("$s", s)))
    mask = d / "nodif_brain_mask.nii.gz"
    if not all(p.exists() for p in (dwi, bval, bvec, mask)): print(f"[{s}] SKIP missing inputs"); continue
    scheme = out / f"{s}.scheme"; amico.util.fsl2scheme(str(bval), str(bvec), str(scheme), bStep=200)
    ae = amico.Evaluation(str(study), s, output_path=str(out))
    ae.set_config("doSaveModulatedMaps", True); ae.set_config("doComputeRMSE", True); ae.set_config("BLAS_nthreads", 1)
    ae.load_data(str(dwi), str(scheme), mask_filename=str(mask), b0_thr=100)
    ae.set_model("NODDI")
    if dpar: ae.model.set(float(dpar), 3.0e-3, ae.model.IC_VFs, ae.model.IC_ODs, False)   # dPar, dIso, IC volume fractions, ODs, isExvivo
    ae.generate_kernels(regenerate=False); ae.load_kernels(); ae.fit(); ae.save_results()
    print(f"[{s}] done")
print("DONE ->", study)
```
<!-- /script:08a_noddi_fit.py -->

<!-- script:08_node_profiles.py -->
```python title="08_node_profiles.py"
#!/usr/bin/env python3
"""Step 8 — 100-node tract profiles (AFQ-style, Gaussian-weighted) for any scalar map.

METRICS maps a column name to the scalar image per subject. Streamlines are oriented to a
QuickBundles centroid first so node 0 is always the seed end and node 99 the target end.
Output: one long CSV per tract — Subject, Tract, Node, <metric columns>.
"""
import os, csv
from pathlib import Path
import numpy as np
import dipy.stats.analysis as dsa, dipy.tracking.streamline as dts
from dipy.io.streamline import load_tractogram
from dipy.io.image import load_nifti
from dipy.segment.clustering import QuickBundles
from dipy.segment.metricspeed import AveragePointwiseEuclideanMetric
from dipy.segment.featurespeed import ResampleFeature

PROJECT = Path(os.environ["PROJECT"]); OUT = Path(os.environ["OUT"]); TRACT = os.environ["TRACT"]; CUTOFF = os.environ["CUTOFF"]
subjects = [l.strip() for l in open(os.environ["SUBJECTS_FILE"]) if l.strip()]
NODES, MIN_STREAMLINES = 100, 5
METRICS = {  # column -> path template; add or remove freely
    "FA":  "dwi/{s}/fa.nii.gz",
    "NDI": "noddi/{s}/fit_NDI_modulated.nii.gz",
    "ODI": "noddi/{s}/fit_ODI_modulated.nii.gz",
    "FWF": "noddi/{s}/fit_FWF.nii.gz",
}

def orient_to_centroid(sl):
    qb = QuickBundles(threshold=np.inf, metric=AveragePointwiseEuclideanMetric(ResampleFeature(nb_points=NODES)))
    return dts.Streamlines(dts.orient_by_streamline(sl, qb.cluster(sl).centroids[0]))

def profile(img, sl):
    data, aff = load_nifti(str(img)); w = dsa.gaussian_weights(sl)
    return np.asarray(dsa.afq_profile(data, sl, aff, nb_points=NODES, weights=w), float)

out_dir = OUT / "nodewise"; out_dir.mkdir(exist_ok=True)
with open(out_dir / f"{TRACT}_nodewise_all_subjects.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["Subject", "Tract", "Node"] + list(METRICS))
    for s in subjects:
        tck = OUT / s / "tckgen" / TRACT / f"{TRACT}_{CUTOFF}_cleaned.tck"
        maps = {m: PROJECT / p.format(s=s) for m, p in METRICS.items()}
        if not tck.exists() or not all(p.exists() for p in maps.values()): print(f"[{s}] SKIP missing inputs"); continue
        sl = load_tractogram(str(tck), str(next(iter(maps.values()))), bbox_valid_check=False).streamlines
        if len(sl) < MIN_STREAMLINES: print(f"[{s}] SKIP {len(sl)} streamlines"); continue
        sl = orient_to_centroid(sl); prof = {m: profile(p, sl) for m, p in maps.items()}
        for n in range(NODES): w.writerow([s, TRACT, n] + [float(prof[m][n]) for m in METRICS])
        print(f"[{s}] {NODES} nodes x {len(METRICS)} metrics")
print("DONE ->", out_dir)
```
<!-- /script:08_node_profiles.py -->

<!-- script:08b_build_analysis_csv.py -->
```python title="08b_build_analysis_csv.py"
#!/usr/bin/env python3
"""Step 8b — Build the wide analysis CSV that permutation_one.R and final_models.py read.

Inputs: $OUT/nodewise/<TRACT>_nodewise_all_subjects.csv (long, from step 8),
        $OUT/nodewise/<TRACT>_tract_stats.csv (Subject, Count_tckstats, Mean_tckstats, from step 5),
        $COVARIATES_CSV (Subject + covariates + outcomes; e.g. ICV, absolute_motion, age, outcome columns).
Output: $OUT/analysis/<TRACT>__<METRIC>__analysis.csv, one row per participant, with columns
        Subject, <covariates>, <outcomes>, Count_tckstats, Mean_tckstats, <METRIC>_0 ... <METRIC>_99.
"""
import os
from pathlib import Path
import pandas as pd

OUT = Path(os.environ["OUT"]); TRACT = os.environ["TRACT"]; COV = Path(os.environ["COVARIATES_CSV"])
long = pd.read_csv(OUT / "nodewise" / f"{TRACT}_nodewise_all_subjects.csv")
stats = pd.read_csv(OUT / "nodewise" / f"{TRACT}_tract_stats.csv")
cov = pd.read_csv(COV)
metrics = [c for c in long.columns if c not in ("Subject", "Tract", "Node")]
(OUT / "analysis").mkdir(exist_ok=True)
for m in metrics:
    wide = long.pivot(index="Subject", columns="Node", values=m)
    wide.columns = [f"{m}_{int(n)}" for n in wide.columns]; wide = wide.reset_index()
    df = cov.merge(stats, on="Subject", how="inner").merge(wide, on="Subject", how="inner")
    p = OUT / "analysis" / f"{TRACT}__{m}__analysis.csv"; df.to_csv(p, index=False)
    print(f"{p.name}: {len(df)} participants x {wide.shape[1]-1} nodes (+ {len(cov.columns)-1} covariate/outcome columns)")
print("Then, per outcome:  Rscript permutation_one.R <analysis.csv> <outcome> <METRIC>_ <out_dir> <label>")
```
<!-- /script:08b_build_analysis_csv.py -->


## Node range

Nodes near the ends of the profile (0 to 4 and 95 to 99) lie in or adjacent to gray matter and are affected by partial-volume contamination from the seed and target regions. Deep white matter spans approximately nodes 25 to 75. Whether end nodes are trimmed should be decided before modelling.

## NODDI inputs

NODDI is fitted with AMICO (Daducci et al., 2015) on the eddy-corrected data; the script `08a_noddi_fit.py` performs the fit with the settings below. The modulated NDI and ODI maps (`fit_NDI_modulated.nii.gz`, `fit_ODI_modulated.nii.gz`), which incorporate the tissue-weighted partial-volume correction of Parker et al. (2021), are used for profiling; FWF has no modulated form and `fit_FWF.nii.gz` is used. Settings used in the example dataset were `bStep=200` during scheme conversion (rounding jittered b-values), `b0_thr=100`, `doSaveModulatedMaps=True`, `doComputeRMSE=True` and `BLAS_nthreads=1`. AMICO regenerates its kernels in a shared directory; when participants are fitted in parallel, kernels should be generated once on a single participant before the pool is started, otherwise concurrent jobs delete one another's files.

When NODDI is sampled within a gray-matter region (for example the hippocampus), the model should be refitted with the gray-matter intrinsic parallel diffusivity (approximately 1.1 × 10⁻³ mm²/s rather than the white-matter default of 1.7 × 10⁻³). The white-matter fit is not appropriate in gray matter and the two fits can yield different results.

## Example profiles

![FA profile](/img/step27_fa_profile_s1000_posterior_l.png)

*Figure 1.* Fractional anisotropy along the left posterior VTA → hippocampus tract, one participant. FA peaks in deep white matter and declines toward the hippocampal end.

![NDI](/img/step30_NDI_profile_s1000_posterior_l.png)
![ODI](/img/step30_ODI_profile_s1000_posterior_l.png)
![FWF](/img/step30_FWF_profile_s1000_posterior_l.png)

*Figure 2.* NDI (top), ODI (middle) and FWF (bottom) for the same bundle. NDI is high near the VTA and increases again toward the hippocampus; ODI is higher at both ends where fibres fan; FWF rises sharply at the hippocampal end adjacent to cerebrospinal fluid.

![Anterior NDI](/img/step30_NDI_profile_s1000_anterior_l.png)

*Figure 3.* NDI along the anterior tract for the same participant, sharing the early trajectory and diverging late.

## Analysis file

Inference in step 9 reads a wide file with one row per participant: the covariates and outcomes, the tract's streamline count and mean length from step 5, and the 100 node values as columns `<METRIC>_0` to `<METRIC>_99`. The script `08b_build_analysis_csv.py` builds one such file per tract and metric from the long profile CSV, the tract statistics file and a participant-level covariates file (`COVARIATES_CSV` in the configuration; columns `Subject` plus covariates and outcomes).

## Verification

The row count of each CSV should equal the number of participants × 100. In the example dataset every tract and metric produced 5,700 rows with no skipped participants.

When both hemispheres are processed, alignment should be confirmed before averaging. The across-participant correlation between node *i* on the left and node *i* on the right is strongly positive when the profiles are aligned (approximately +.98 in the example dataset) and strongly negative when one side is reversed. Mid-tract averages (nodes 25 to 74) correlated across hemispheres at approximately .8 to .9 for NDI and ODI and .5 for FA.
