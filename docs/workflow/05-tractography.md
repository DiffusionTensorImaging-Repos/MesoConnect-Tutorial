---
sidebar_position: 6
title: "5. Tractography"
---

# 5. Corridor-constrained tractography

The pilot command with production budgets. Seeding is unidirectional from the seed ROI; the target is required; everything outside the corridor is excluded.

```bash
tckgen "$PROJECT/dwi/$s/wm_fod_norm.mif" "$o/${TRACT}_${CUTOFF}.tck" \
  -seed_image "$d/${TRACT}_seed_diff.nii.gz" -seed_unidirectional \
  -include "$d/${TRACT}_target_diff.nii.gz" \
  -exclude "$d/${TRACT}_exclusion_mask.nii.gz" \
  -select 2500 -seeds 25000000 -cutoff 0.01 -minlength 35 -maxlength 65 \
  -stop -nthreads 8 -force
```

Script: [`05_tractography.sh`](pathname:///MesoConnect-Tutorial/scripts/05_tractography.sh). About two minutes per subject and hemisphere at 3 T with eight threads; about four hours for 57 subjects, both hemispheres, run serially.

## Parameters

| Flag | Value | Rationale |
|---|---|---|
| `-cutoff` | from step 4 (0.01 in the example) | The corridor makes a permissive cutoff usable. |
| `-select` | 2500 | Sufficient for stable profiles and endpoint maps. Streamline count is not a connectivity measure; subjects that stop short are retained. |
| `-seeds` | 25,000,000 | Ceiling on seeding attempts. The default (1000 × select) is sometimes insufficient to reach 2,500. |
| `-minlength` / `-maxlength` | 35 / 65 mm | Set for VTA → hippocampus at 7 T. The example dataset kept them at 3 T; mean lengths were 44 to 47 mm. Set per tract family from the pilot lengths. |
| `-seed_unidirectional` | on | Track away from the seed only. |
| `-stop` | on | Terminate on entering the target. |
| gradients | embedded in the `.mif` | Omit `-fslgrad` if the FOD image was built from a `.mif` with gradients. |

Streamline count and mean length per subject are recorded and used later as covariates; they index reconstruction quality and vary between subjects.

## Per tract family

| Family | Cutoff at 7 T (atlas construction) | Length bounds | Notes |
|---|---|---|---|
| VTA → hippocampus, posterior and anterior | 0.06 | 35 to 65 mm | Example dataset used 0.01 at 3 T with the corridor. |
| VTA → amygdala | 0.06 | pilot | Shorter tract; expect lower bounds. |
| VTA → accumbens, superior and inferior | 0.06 | pilot | 0.01 has been used with the corridor. |
| Ventral pallidum → VTA | 0.06 | pilot | |
| Hippocampus → accumbens, → ventral pallidum | 0.08 | pilot | Frequently reconstructs as two clusters; see cleaning. |

Where the table says pilot, run step 4 and take the bounds from the mean lengths in the summary.

## Audit

The script counts the subjects that reached the streamline target. Example dataset: all 114 hemisphere runs reached 2,500, using 0.5 to 2.0 million seeds (about 4% of the ceiling). The anterior tract also reached 2,500 in all 114 runs with higher seed usage (1.5 to 11 million), consistent with its smaller corridor.

A subject reaching 1,800 streamlines is retained. A subject reaching 50 belongs in the flagged list in step 7.
