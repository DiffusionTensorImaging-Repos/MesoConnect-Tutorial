# MesoConnect Atlas Tutorial

Documentation site for the MesoConnect Atlas, a 7 T probabilistic atlas of mesolimbic white-matter pathways. The site describes corridor-constrained tractography: a tract atlas is warped into each participant and dilated into a corridor, the participant's own MRtrix3 tractography is run within it, the bundle is cleaned with pyAFQ, microstructure is profiled at 100 nodes, and group-level models are fitted at the whole-tract, quartile and node level. A 3 T dataset (57 participants, ventral tegmental area → hippocampus) serves as the example.

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
static/scripts/  step scripts 00b to 09c, driven by 00_config.sh
static/explorer/ Node-wise Tract Explorer (self-contained HTML) and sample data
static/img/      example-dataset figures (de-identified)
static/supplement/  Supplementary Methods (PDF, DOCX) compiled from the pages
tools/           embed_scripts.py (scripts -> pages; runs before every build)
                 build_supplement.py (pages -> Supplementary Methods; run manually)
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
