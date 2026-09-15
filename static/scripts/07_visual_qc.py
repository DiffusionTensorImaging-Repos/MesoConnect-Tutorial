#!/usr/bin/env python3
"""Step 7 — Tract-density overlays for every cleaned bundle, with automatic flags."""
import os, subprocess
from pathlib import Path
import nibabel as nib, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
PROJECT = Path(os.environ["PROJECT"]); OUT = Path(os.environ["OUT"]); TRACT = os.environ["TRACT"]; CUTOFF = os.environ["CUTOFF"]
subjects = [l.strip() for l in open(os.environ["SUBJECTS_FILE"]) if l.strip()]
qc = OUT / "qc" / TRACT; qc.mkdir(parents=True, exist_ok=True); flags = []
for s in subjects:
    tck = OUT / s / "tckgen" / TRACT / f"{TRACT}_{CUTOFF}_cleaned.tck"; ref = PROJECT / "dwi" / s / "nodif_brain_mask.nii.gz"
    bg_f = PROJECT / "dwi" / s / "mean_b0.nii.gz"
    if not tck.exists(): flags.append((s, "MISSING")); continue
    if os.environ.get("FORCE","0")!="1" and (qc / f"{s}_{TRACT}_qc.png").exists(): print(f"[{s}] QC image exists"); continue
    tdi = qc / f"{s}_tdi.nii.gz"
    subprocess.run(["tckmap", str(tck), str(tdi), "-template", str(ref), "-force", "-quiet"], check=True)
    d = nib.load(str(tdi)).get_fdata(); nvox = int((d > 0).sum()); mx = float(d.max())
    flag = "LOW_VOXELS" if nvox < 50 else "HIGH_VOXELS" if nvox > 5000 else "LOW_DENSITY" if mx < 5 else None
    if flag: flags.append((s, f"{flag} ({nvox} vox, max {mx:.0f})"))
    bg = nib.load(str(bg_f)).get_fdata() if bg_f.exists() else nib.load(str(ref)).get_fdata()
    ax_i = int(np.argmax(d.sum(axis=(0, 1)))); co_i = int(np.argmax(d.sum(axis=(0, 2))))
    fig, axes = plt.subplots(1, 2, figsize=(10, 5)); fig.suptitle(f"{s} · {TRACT} · cleaned", fontweight="bold")
    for ax, (b, t, title) in zip(axes, [(bg[:, :, ax_i], d[:, :, ax_i], "axial"), (bg[:, co_i, :], d[:, co_i, :], "coronal")]):
        ax.imshow(np.rot90(b), cmap="gray"); ax.imshow(np.rot90(np.ma.masked_where(t <= 0, t)), cmap="hot", alpha=.7); ax.set_title(title); ax.axis("off")
    if flag: fig.text(.5, .01, f"FLAG: {flag}", ha="center", color="red", fontweight="bold")
    plt.tight_layout(); plt.savefig(qc / f"{s}_{TRACT}_qc.png", dpi=100, bbox_inches="tight"); plt.close(); tdi.unlink()
    print(f"[{s}] {'FLAG '+flag if flag else 'ok'} ({nvox} voxels)")
print("\nflagged:", flags if flags else "none")
