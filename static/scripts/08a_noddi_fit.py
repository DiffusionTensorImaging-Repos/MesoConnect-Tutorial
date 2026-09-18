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
