#!/usr/bin/env python3
"""Step 8a. Fit NODDI with AMICO so Step 8 can profile NDI, ODI and FWF along the bundle.

Inputs:  $PROJECT/dwi/<subj>/{data.nii.gz, bvals, bvecs, nodif_brain_mask.nii.gz}
Outputs: $PROJECT/noddi/<subj>/fit_{NDI,ODI,FWF,NDI_modulated,ODI_modulated,RMSE}.nii.gz
         (noddi_gm/ instead when NODDI_DPAR is set); work/<subj>/ is scratch, safe to delete
Run:     source 00_config.sh && python 08a_noddi_fit.py [sub-01 sub-02 ...]
"""
import os
import sys
from pathlib import Path

N_THREADS = os.environ.get("NODDI_NTHREADS", "4")
# numpy's BLAS reads these at import time, and importing amico imports numpy.
os.environ["OPENBLAS_NUM_THREADS"] = N_THREADS     # must be set before amico is imported
os.environ["OMP_NUM_THREADS"] = N_THREADS

import amico


# Read a variable exported by 00_config.sh, or stop with a message naming it.
def env(name):
    if name not in os.environ:
        sys.exit(f"{name} is not set: run `source 00_config.sh` first")
    return os.environ[name]


PROJECT = Path(env("PROJECT"))
FORCE = os.environ.get("FORCE", "0") == "1"
SUBJECTS = sys.argv[1:] or Path(env("SUBJECTS_FILE")).read_text().split()

# dPar is fixed, not fitted, so it must suit the tissue: 1.7e-3 white matter, 1.1e-3 gray.
D_PAR = os.environ.get("NODDI_DPAR")     # mm2/s; unset = AMICO default for white matter
D_ISO = 3.0e-3                           # isotropic (free water) diffusivity, mm2/s
B0_THRESHOLD = 100                       # volumes with b below this are treated as b = 0
B_STEP = 200                             # b-values are rounded to the nearest multiple

STUDY = PROJECT / ("noddi_gm" if D_PAR else "noddi")
STUDY.mkdir(parents=True, exist_ok=True)
# One-off: caches AMICO's rotation matrices in ~/.dipy, so only the first call is slow.
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
    # AMICO clears the output directory on save, so the scheme and kernels live in work/.
    # One work directory per participant: with AMICO's shared default, concurrent runs collide.
    work = STUDY / "work" / s
    work.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)

    scheme = work / f"{s}.scheme"
    amico.util.fsl2scheme(str(bvals), str(bvecs), str(scheme), bStep=B_STEP)

    # Evaluation(study_dir, participant, output_path): the maps go straight to noddi/<subj>/.
    ae = amico.Evaluation(str(STUDY), s, str(out))
    # BLAS_nthreads=1 so the two thread counts do not multiply and oversubscribe the machine.
    ae.set_config("nthreads", int(N_THREADS))
    ae.set_config("BLAS_nthreads", 1)
    ae.set_config("doSaveModulatedMaps", True)
    ae.set_config("doComputeRMSE", True)
    ae.load_data(str(dwi), str(scheme), str(mask), b0_thr=B0_THRESHOLD)

    ae.set_model("NODDI")
    ae.set_config("ATOMS_path", str(work / "kernels"))     # after set_model, which resets it
    # model.set(dPar, dIso, IC_VFs, IC_ODs, isExvivo); only dPar changes here.
    if D_PAR:
        ae.model.set(float(D_PAR), D_ISO, ae.model.IC_VFs, ae.model.IC_ODs, False)
    # regenerate=True so a half-written kernel set from a killed run is never picked up.
    ae.generate_kernels(regenerate=True)
    ae.load_kernels()
    ae.fit()
    ae.save_results()
    print(f"[{s}] NODDI maps written (dPar = {ae.model.dPar})")

print(f"DONE -> {STUDY}")
