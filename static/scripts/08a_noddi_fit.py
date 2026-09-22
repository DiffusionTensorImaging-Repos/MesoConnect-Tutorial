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
