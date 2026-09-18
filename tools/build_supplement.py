#!/usr/bin/env python3
"""Compile the tutorial into one Supplementary Methods document (HTML -> PDF and DOCX via LibreOffice).
Tables and figures are renumbered S1, S2, ... across the document; scripts move to an appendix.
Requires node (marked, from node_modules) and LibreOffice.  Not run in CI; outputs are committed."""
import re, subprocess, base64, datetime, shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; DOCS=ROOT/"docs"; IMG=ROOT/"static"/"img"; OUT=ROOT/"static"/"supplement"; OUT.mkdir(exist_ok=True)
SITE="https://diffusiontensorimaging-repos.github.io/MesoConnect-Tutorial"
ORDER=["intro.md","atlas/overview.md","atlas/tracts.md","atlas/downloads.md","workflow/overview.md","workflow/01-registration.md","workflow/02-warp-rois.md",
 "workflow/03-corridor-mask.md","workflow/04-tune-cutoff.md","workflow/05-tractography.md","workflow/06-cleaning.md","workflow/07-visual-qc.md","workflow/08-node-profiles.md",
 "workflow/09-nodewise-stats.md","explorer.md","appendix/whole-tract.md","appendix/synthetic-streamlines.md","reference/parameters.md","reference/troubleshooting.md",
 "reference/software.md","reference/scripts.md","reference/methods-text.md","reference/abbreviations.md","reference/citation.md","reference/references.md"]
FLOW="""1. Step 1. Registration of the MNI template to native T1 space (ANTs SyN).
2. Step 2. Warping of the seed, target and atlas into diffusion space.
3. Step 3. Corridor construction (dilate, add seed and target, invert).
4. Step 4. Cutoff selection by pilot sweep and side-by-side comparison.
5. Step 5. Corridor-constrained tractography (tckgen).
6. Step 6. Bundle cleaning (Mahalanobis outlier removal).
7. Step 7. Quality control (tract-density overlays).
8. Step 8. Along-tract profiles (100 nodes; FA and NODDI).
9. Step 9. Group-level inference (whole tract, quartiles, nodes), with node-wise results viewed in the Node-wise Tract Explorer."""
IMG_RE=re.compile(r"!\[([^\]]*)\]\(/img/([^)\s]+)\)")
def embed(m):
    data=base64.b64encode((IMG/m.group(2)).read_bytes()).decode()
    return f'\n\n<p><img alt="{m.group(1)}" width="560" src="data:image/png;base64,{data}"></p>\n\n'
tn=fn=0; scripts=[]; parts=[]; nimg=0
for rel in ORDER:
    s=(DOCS/rel).read_text(); s=re.sub(r"^---.*?---\s*","",s,flags=re.S)
    for m in re.finditer(r"<!-- script:([^\s]+) -->",s):                       # scripts are read from the files, not the page
        name=m.group(1); src=ROOT/"static"/"scripts"/name
        if name not in [x[0] for x in scripts]: scripts.append((name,{".sh":"bash",".py":"python",".R":"r"}[src.suffix],src.read_text()))
    s=re.sub(r"<!-- script:([^\s]+) -->.*?<!-- /script:\1 -->",lambda m:f"*The script `{m.group(1)}` is reproduced in the Supplementary Scripts appendix.*",s,flags=re.S)
    s=re.sub(r"```mermaid.*?```",FLOW,s,flags=re.S)
    tmap={}; fmap={}
    for m in re.finditer(r"^\*\*(Table|Figure) (\d+)\*\*$",s,flags=re.M):
        if m.group(1)=="Table": tn+=1; tmap[m.group(2)]=f"S{tn}"
        else: fn+=1; fmap[m.group(2)]=f"S{fn}"
    def ren(m):
        mp=tmap if m.group(1).startswith("Table") else fmap
        out=f"{m.group(1)} {mp.get(m.group(2),m.group(2))}"
        if m.group(3): out+=f" {m.group(3)} {mp.get(m.group(4),m.group(4))}"
        return out
    s=re.sub(r"\b(Tables?|Figures?) (\d+)(?: (to|and) (\d+))?",ren,s)
    nimg+=len(IMG_RE.findall(s)); s=IMG_RE.sub(embed,s)                                  # images first
    s=s.replace("](pathname:///MesoConnect-Tutorial/","]("+SITE+"/")
    s=re.sub(r"(?<!\!)\[([^\]]+)\]\((?!https?:|data:|#)[^)]+\)",r"\1",s)                # internal doc links -> plain text
    parts.append(s)
body="\n\n".join(parts)+"\n\n# Supplementary scripts\n\nThe scripts below are those distributed with the tutorial, in run order.\n\n"+"\n\n".join(f"## {n}\n\n```{l}\n{c}```" for n,l,c in scripts)
md=OUT/"_supplement.md"; md.write_text(body)
js="const {marked}=require('marked');const fs=require('fs');marked.setOptions({gfm:true});process.stdout.write(marked.parse(fs.readFileSync(process.argv[1],'utf8')));"
htm=subprocess.run(["node","-e",js,str(md)],capture_output=True,text=True,cwd=ROOT,check=True).stdout; md.unlink()
# APA-style tables: rule above, below, and under the header row
htm=htm.replace("<table>",'<table width="100%" cellpadding="4" cellspacing="0" frame="hsides" rules="groups" border="1">')
# code listings: one block, single-spaced (each <pre> line becomes a paragraph in Writer, so margins must be zero)
htm=re.sub(r"<pre><code[^>]*>(.*?)</code></pre>",lambda m:'<pre class="code">'+m.group(1)+'</pre>',htm,flags=re.S)
css="""@page{size:8.5in 11in;margin:1in}
body{font-family:'Times New Roman',Times,serif;font-size:12pt;line-height:1.2;color:#000}
h1,h2,h3,h4{font-family:'Times New Roman',Times,serif;color:#000}
h1{font-size:12pt;font-weight:bold;text-align:center;margin:0 0 12pt;page-break-before:always}
h2{font-size:12pt;font-weight:bold;text-align:left;margin:14pt 0 6pt}
h3{font-size:12pt;font-weight:bold;font-style:italic;text-align:left;margin:12pt 0 6pt}
p{margin:0 0 8pt} li{margin:0 0 3pt}
table{font-size:9.5pt;line-height:1.15;margin:2pt 0 10pt} th{text-align:left;font-weight:bold;vertical-align:bottom} td{vertical-align:top}
pre.code{font-family:'Courier New',Courier,monospace;font-size:8pt;line-height:1.15;margin:0;padding:0;border:0;white-space:pre-wrap}
code{font-family:'Courier New',Courier,monospace;font-size:10pt} a{color:#000;text-decoration:none}"""
today=datetime.date.today().strftime("%B %Y")
title=("<p align='center' style='margin-top:150pt;font-size:14pt'><b>MesoConnect Atlas Tutorial</b></p>"
       "<p align='center'><b>Supplementary Methods</b></p>"
       "<p align='center'>Corridor-constrained tractography and along-tract microstructure for mesolimbic pathways</p>"
       f"<p align='center'>{today}</p><p align='center'>{SITE}/</p>")
full=f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>MesoConnect Atlas Tutorial: Supplementary Methods</title><style>{css}</style></head><body>{title}{htm}</body></html>"
hp=OUT/"MesoConnect_Supplementary_Methods.html"; hp.write_text(full)
soffice=shutil.which("soffice") or "/Applications/LibreOffice.app/Contents/MacOS/soffice"
for flt in ["pdf:writer_pdf_Export","docx:MS Word 2007 XML"]:      # import as a text document so pictures are embedded on export
    subprocess.run([soffice,"--headless","--infilter=HTML (StarWriter)","--convert-to",flt,"--outdir",str(OUT),str(hp)],check=True,capture_output=True,timeout=600)
hp.unlink(); print(f"tables S1-S{tn}, figures S1-S{fn}, images embedded {nimg}, scripts {len(scripts)}")
