---
sidebar_position: 6
title: "5. Tractography"
---

# 5. Corridor-constrained tractography for every subject

Same command as the pilot with production budgets. Seed in the seed ROI, unidirectionally; require the target; exclude everything outside the corridor.

```bash
tckgen "$PROJECT/dwi/$s/wm_fod_norm.mif" "$o/${TRACT}_${CUTOFF}.tck" \
  -seed_image "$d/${TRACT}_seed_diff.nii.gz" -seed_unidirectional \
  -include "$d/${TRACT}_target_diff.nii.gz" \
  -exclude "$d/${TRACT}_exclusion_mask.nii.gz" \
  -select 2500 -seeds 25000000 -cutoff 0.01 -minlength 35 -maxlength 65 \
  -stop -nthreads 8 -force
```

Script: [`05_tractography.sh`](pathname:///MesoConnect-Tutorial/scripts/05_tractography.sh). About two minutes per subject and hemisphere at 3 T with eight threads; four hours for 57 subjects both sides, serially.

## Parameters

| Flag | Value | Why |
|---|---|---|
| `-cutoff` | from step 4 (0.01 in the example) | The corridor makes a permissive cutoff safe. |
| `-select` | 2500 | Enough streamlines for stable profiles and endpoint maps. Streamline count is not a connectivity measure; a subject that stops short is kept. |
| `-seeds` | 25,000,000 | Generous ceiling. The default (1000 × select) is sometimes not enough to reach 2,500. |
| `-minlength` / `-maxlength` | 35 / 65 mm | Set for VTA → hippocampus at 7 T; the example kept them at 3 T and mean lengths came out around 44 to 47 mm. Adjust per tract family from the pilot lengths. |
| `-seed_unidirectional` | on | Track away from the seed only. |
| `-stop` | on | Stop once the target is entered. |
| gradients | embedded in the `.mif` | If your FOD was built from a `.mif` with gradients, drop `-fslgrad`. |

Streamline count and mean length per subject are worth carrying forward as covariates in later models; they index reconstruction quality and vary between subjects.

## Per tract family

| Family | Cutoff at 7 T (atlas construction) | Length bounds | Notes |
|---|---|---|---|
| VTA → hippocampus, posterior and anterior | 0.06 | 35 to 65 mm | 3 T example used 0.01 with the corridor. |
| VTA → amygdala | 0.06 | pilot | Short tract; expect lower bounds. |
| VTA → accumbens, superior and inferior | 0.06 | pilot | 0.01 has been used with the corridor. |
| Ventral pallidum → VTA | 0.06 | pilot | |
| Hippocampus → accumbens, → ventral pallidum | 0.08 | pilot | Frequently reconstructs as two clusters; see cleaning. |

Where the table says pilot, run step 4 and read the mean lengths off the summary before setting bounds.

## Audit

The script counts how many subjects reached the streamline target. Example dataset: 114 of 114 hemisphere runs reached 2,500, using 0.5 to 2.0 million seeds (about 4% of the ceiling). The anterior tract also reached 2,500 in all 114, with slightly higher seed usage (1.5 to 11 million), which is expected for a smaller corridor.

A subject that reaches, say, 1,800 is not a failure. A subject at 50 is, and belongs in step 7's flagged list.
