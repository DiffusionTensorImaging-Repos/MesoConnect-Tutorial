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
