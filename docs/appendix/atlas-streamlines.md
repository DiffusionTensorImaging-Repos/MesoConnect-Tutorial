---
sidebar_position: 1
title: "Warping the atlas streamlines"
---

# Warping the atlas streamlines

Alongside the volumetric maps, the atlas package distributes the group-average streamlines of each pathway as MRtrix tractograms (`.tck`), two per pathway, one per hemisphere. In this approach those streamlines are carried into a participant with a registration and microstructure is sampled along them, so along-tract profiles are obtained without reconstructing the tract in the participant's own data.

The trajectory represents the group rather than the participant, so this approach suits studies whose outcome is microstructure measured along a pathway. For questions about tract geometry, an individual's trajectory or connectivity, tractography in the participant's own data remains the recommended method and is documented in this site's workflow section. Accuracy depends on the registration: where registration is poor, or anatomy varies between participants, the streamlines sample tissue displaced from the intended location, and this displacement is spatially systematic rather than random noise. The atlas authors report that warped streamlines recover node-wise profiles similar to those obtained by tracking in the participant's own data, while identifying registration uncertainty and between-participant anatomical variation as the principal concerns in using these files.

## Procedure

The registration is the one produced in [Step 1](../workflow/registration), with the Montreal Neurological Institute (MNI) template as the moving image and the participant's T1 as the fixed image. No separate registration is needed.

Streamlines are transformed by moving their vertices, not by resampling an image, and vertices move in the opposite sense to images. Step 2 carries the atlas *image* into the participant with the forward warp and the affine; the same registration carries *points* with the inverted affine and the inverse warp field, `mni2t1_1InverseWarp.nii.gz`, which `antsRegistrationSyNQuick.sh` writes in Step 1. Every vertex of every streamline is transformed in one call, and the per-streamline vertex counts are the only record of where one streamline ends and the next begins, so they are kept and used to reassemble the bundle.

```bash
antsApplyTransformsToPoints -d 3 -i mni_lps.csv -o t1_lps.csv \
  -t "[mni2t1_0GenericAffine.mat,1]" -t mni2t1_1InverseWarp.nii.gz
```

The coordinate files are in left-posterior-superior (LPS) order, while tractogram vertices are read and written in right-anterior-superior (RAS) order, so the x and y signs are flipped before the call and again afterwards. The script below performs the whole operation for every participant and audits the result.

<!-- script:02s_warp_atlas_streamlines.py -->
<details>
<summary>Script <code>02s_warp_atlas_streamlines.py</code> (143 lines)</summary>

```python title="02s_warp_atlas_streamlines.py"
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
```

</details>
<!-- /script:02s_warp_atlas_streamlines.py -->

Sampling requires the scalar maps and the warped streamlines to be in the same space. Where the maps are already in anatomical space, as in output from containerized pipelines that reconstruct in a resampled anatomical space, they can be sampled directly. Where the maps are in diffusion space, as in [Step 8a](../workflow/node-profiles), the diffusion-to-T1 direction of the Step 2 transform brings them onto the T1 grid; when the T1 and the diffusion images are header-aligned and differ only in grid, the two spaces already coincide and nothing is applied.

```bash
convert_xfm -omat diff2str.mat -inverse "$PROJECT/xfm/$s/str2diff.mat"
flirt -in "$NDI" -ref "$T1" -applyxfm -init diff2str.mat -interp trilinear -out ndi_in_T1.nii.gz
```

Each scalar map is then sampled at 100 nodes along the bundle, with the profiler of [Step 8](../workflow/node-profiles), which reads the bundle from `$OUT/<participant>/tckgen/<tract>/`; the warped file is either copied there or that path is changed to the `atlas_streamlines` folder written above. Two of that step's operations are unnecessary here: every streamline in the distributed files carries exactly 100 vertices, so no resampling is required, and the streamlines of a given file share a common orientation, so no reorientation against the seed region is required. Group-level models follow [Step 9](../workflow/nodewise-stats) unchanged, since the result is a 100-node profile per participant in the same form.

## Verification

The script transforms every vertex of every streamline in a single call and compares the returned array's shape with the input's. A different vertex count or any non-finite coordinate stops processing for that participant without writing a file. This failure indicates a wrong or missing transform rather than an inaccurate one.

The script reports, per participant, the proportion of warped vertices inside the non-zero part of that participant's T1-weighted brain image. This proportion is interpreted relative to the sample: a value well below those of other participants indicates a failed registration.

The warped streamlines are overlaid on the participant's own image to confirm that their endpoints occupy the intended anatomical regions. No numeric summary substitutes for this visual inspection of the trajectory. The atlas authors identify registration accuracy as the principal concern in using these files.

The warp preserves vertex order within each streamline, carrying the source atlas file's orientation unchanged into every participant. When hemisphere profiles are combined, the two source files are checked for the same anatomical direction. If their directions differ, node 1 in one hemisphere corresponds to the opposite tract end from node 1 in the other, so averaging combines anatomically opposite positions.

The first check automatically reports failure and prevents file creation. Poor but unbroken registration, misplaced endpoints, and reversed hemispheric correspondence all pass that check: files are written, profiles are computed, and numbers are returned without an error, leaving these failures undetected unless the remaining checks are performed.

## Other routes

Streamline registration is not specific to ANTs; MRtrix `tcktransform` applies a warp field to a tractogram and serves the same purpose.

For data that already has a whole-brain tractogram, RecoBundles, implemented in DIPY (Garyfallidis et al., 2014), can extract bundles matching an atlas template. The atlas authors report that whole-brain settings often fail to reconstruct these pathways, whose small size makes them sensitive to fibre orientation distribution amplitude and termination criteria, and that amplitude thresholds had to be relaxed. It is therefore a possible route for existing tractograms rather than a substitute for targeted tractography, and what it extracts should be inspected against the intended pathway.

## Reporting

Reports should state that profiles were sampled along group-average atlas streamlines warped into each participant, name the registration and the transform direction used, and give the quality-control criteria applied to the warped bundles. The profiles should not be described as participant-level tractography, and the limits of a group trajectory should be stated where the outcome concerns anatomy rather than microstructure.
