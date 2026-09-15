# MesoConnect Atlas Tutorial

Public tutorial for the MesoConnect Atlas, a 7 T probabilistic atlas of mesolimbic white-matter pathways. The site teaches corridor-guided tractography: warp a tract atlas into a subject, dilate it into a corridor, run the subject's own MRtrix tractography through it, clean with pyAFQ, profile microstructure at 100 nodes, and test node-wise. A 3 T dataset (57 subjects, VTA → hippocampus) is the worked example.

Live site: https://diffusiontensorimaging-repos.github.io/MesoConnect-Tutorial/
Preprocessing prerequisite: https://diffusiontensorimaging-repos.github.io/TUBRIC-DTI/

## Layout

```
docs/          tutorial pages (Docusaurus markdown)
  atlas/       what the atlas is, tract families and ROIs, downloads
  workflow/    the nine steps
  appendix/    whole-tract extraction, synthetic streamlines
  reference/   parameters, troubleshooting, software, scripts, citation
static/atlas/    VTA-hippocampus ROIs and atlases (MNI 1 mm)
static/scripts/  generalized step scripts (00_config.sh drives them) + permutation_one.R + final_models.py
static/explorer/ Node-wise Tract Explorer (self-contained HTML) + sample data
static/img/      worked-example figures
src/pages/       landing page
```

## Develop

```bash
npm install
npm run start          # dev server
npm run build          # static site in build/
npm run serve          # serve the build locally
```

Deploys to GitHub Pages from `build/` (`npm run deploy` with `GIT_USER` set, or a Pages workflow).
