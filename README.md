# MesoConnect Atlas Tutorial

Documentation site for the MesoConnect Atlas, a 7 T probabilistic atlas of mesolimbic white-matter pathways. The site describes corridor-guided tractography: a tract atlas is warped into a subject and dilated into a corridor, the subject's own MRtrix tractography is run through it, the bundle is cleaned with pyAFQ, microstructure is profiled at 100 nodes, and node-wise statistics are computed. A 3 T dataset (57 subjects, VTA → hippocampus) serves as the example.

Site: https://diffusiontensorimaging-repos.github.io/MesoConnect-Tutorial/
Preprocessing prerequisite: https://diffusiontensorimaging-repos.github.io/TUBRIC-DTI/

## Layout

```
docs/            tutorial pages (Docusaurus markdown)
  atlas/         atlas overview, tract families and ROIs, downloads
  workflow/      the nine steps
  appendix/      whole-tract extraction, synthetic streamlines
  reference/     parameters, troubleshooting, software, scripts, citation
static/atlas/    VTA-hippocampus ROIs and atlases (MNI 1 mm)
static/scripts/  step scripts driven by 00_config.sh, plus permutation_one.R and final_models.py
static/explorer/ Node-wise Tract Explorer (self-contained HTML) and sample data
static/img/      example-dataset figures
src/pages/       landing page
```

## Development

```bash
npm install
npm run start          # development server
npm run build          # static site in build/
npm run serve          # serve the build locally
```

Pushes to `main` are built and deployed to GitHub Pages by `.github/workflows/deploy.yml`.
