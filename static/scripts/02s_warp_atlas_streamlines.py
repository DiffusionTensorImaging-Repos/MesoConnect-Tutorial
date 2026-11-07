#!/usr/bin/env python3
"""Step 2s. Carry the atlas streamlines from MNI space into each participant's T1 space.

This is the streamline alternative to Steps 2 to 6. Nothing is tracked in the participant:
every vertex of the atlas .tck is pushed through the Step 1 registration, so the bundle that
comes out has the atlas's geometry placed on the participant's anatomy.

Inputs, per participant:
    $OUT/<s>/reg/mni2t1_0GenericAffine.mat     Step 1 affine
    $OUT/<s>/reg/mni2t1_1InverseWarp.nii.gz    Step 1 inverse warp field
    $PROJECT/anat/<s>/<s>_T1w_brain.nii.gz     fixed image of Step 1; also the audit mask
    $ATLAS_STREAMLINES_MNI                     atlas streamlines, MNI space (atlas package)
Output: $OUT/<s>/atlas_streamlines/<TRACT>_atlas_t1.tck
Run:    source 00_config.sh && python 02s_warp_atlas_streamlines.py
        (FORCE=1 redoes finished participants)
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import nibabel as nib
import numpy as np


# Read one variable exported by 00_config.sh, or stop with a hint.
def env(name):
    if name not in os.environ:
        sys.exit(f"{name} is not set: run `source 00_config.sh` first")
    return os.environ[name]


PROJECT = Path(env("PROJECT"))
OUT = Path(env("OUT"))
TRACT = env("TRACT")
ATLAS_TCK = Path(env("ATLAS_STREAMLINES_MNI"))
FORCE = os.environ.get("FORCE", "0") == "1"
# bash cannot export an array, so the ID list is re-read from the file.
SUBJECTS = Path(env("SUBJECTS_FILE")).read_text().split()

# antsApplyTransformsToPoints reads and writes LPS, nibabel gives and takes RAS.
# Flipping x and y converts between them, and the same multiplier undoes it afterwards.
RAS_TO_LPS = np.array([-1.0, -1.0, 1.0])

if not ATLAS_TCK.is_file():
    sys.exit(f"atlas streamlines not found: {ATLAS_TCK}")

atlas = nib.streamlines.load(str(ATLAS_TCK)).streamlines
if len(atlas) == 0:
    sys.exit(f"{ATLAS_TCK} holds no streamlines")
# Vertex counts are the only record of where one streamline ends and the next begins,
# because every vertex of every streamline is transformed in a single call.
lengths = [len(s) for s in atlas]
mni_points = np.vstack(atlas)
print(f"== atlas: {len(atlas)} streamlines, {len(mni_points)} vertices, "
      f"{min(lengths)}-{max(lengths)} points each")


def warp_points(points, affine, inverse_warp):
    """Push an (N, 3) array of RAS millimetre coordinates from MNI into T1 space."""
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "mni_lps.csv"
        dst = Path(tmp) / "t1_lps.csv"
        # comments='' keeps numpy from prefixing the header with "# ", which ANTs cannot read.
        np.savetxt(src, points * RAS_TO_LPS, delimiter=",", fmt="%.7f",
                   header="x,y,z", comments="")
        # Points move in the opposite sense to images: Step 2 warps the atlas IMAGE with the
        # forward warp and affine, so the same registration moves POINTS with the inverted
        # affine ([...,1]) and the inverse warp field. Do not substitute mni2t1_1Warp here.
        subprocess.run(
            ["antsApplyTransformsToPoints", "-d", "3",
             "-i", str(src), "-o", str(dst),
             "-t", f"[{affine},1]", "-t", str(inverse_warp)],
            check=True, stdout=subprocess.DEVNULL)
        # ANTs writes one header row and may add columns beyond x, y, z.
        out = np.loadtxt(dst, delimiter=",", skiprows=1, usecols=(0, 1, 2), ndmin=2)
    return out * RAS_TO_LPS


def fraction_in_brain(points, brain):
    """Share of vertices landing inside the non-zero part of the T1 brain image."""
    img = nib.load(str(brain))
    data = np.asarray(img.dataobj)
    ijk = np.rint(nib.affines.apply_affine(np.linalg.inv(img.affine), points)).astype(int)
    inside = np.all((ijk >= 0) & (ijk < np.array(data.shape)), axis=1)
    hit = np.zeros(len(points), dtype=bool)
    hit[inside] = data[tuple(ijk[inside].T)] > 0
    return hit.mean()


def warp_one(s):
    d = OUT / s / "atlas_streamlines"
    out_tck = d / f"{TRACT}_atlas_t1.tck"
    reg = OUT / s / "reg"
    affine = reg / "mni2t1_0GenericAffine.mat"
    inverse_warp = reg / "mni2t1_1InverseWarp.nii.gz"

    if not FORCE and out_tck.is_file():
        print(f"== {s} already warped")
        return
    missing = [p for p in (affine, inverse_warp) if not p.is_file()]
    if missing:
        print(f"!! {s} missing {missing[0]}")
        return
    d.mkdir(parents=True, exist_ok=True)

    t1_points = warp_points(mni_points, affine, inverse_warp)
    # The only automatic check that the transform did what was asked: every vertex came back,
    # and none of them is NaN or infinite. Anatomy still has to be inspected by eye.
    if t1_points.shape != mni_points.shape or not np.isfinite(t1_points).all():
        print(f"!! {s} transform returned {t1_points.shape}, expected {mni_points.shape}")
        return

    # float32 is the .tck storage type; the identity affine declares the vertices as
    # world millimetres, which is what Step 8's reader expects.
    streamlines = np.split(t1_points, np.cumsum(lengths)[:-1])
    tractogram = nib.streamlines.Tractogram(
        [np.asarray(s_, dtype=np.float32) for s_ in streamlines],
        affine_to_rasmm=np.eye(4))
    partial = out_tck.with_suffix(".partial.tck")
    nib.streamlines.save(tractogram, str(partial))
    partial.rename(out_tck)
    print(f">> {s} {len(streamlines)} streamlines")


for s in SUBJECTS:
    warp_one(s)

# --- Audit: a bundle that lands largely outside the brain means the registration is wrong ---
print(f"\nSubject\tStreamlines\tIn_brain")
for s in SUBJECTS:
    tck = OUT / s / "atlas_streamlines" / f"{TRACT}_atlas_t1.tck"
    brain = PROJECT / "anat" / s / f"{s}_T1w_brain.nii.gz"
    if not tck.is_file():
        print(f"{s}\tMISSING")
        continue
    warped = nib.streamlines.load(str(tck)).streamlines
    if brain.is_file():
        share = fraction_in_brain(np.vstack(warped), brain)
        print(f"{s}\t{len(warped)}\t{share:.3f}")
    else:
        print(f"{s}\t{len(warped)}\tno T1")
