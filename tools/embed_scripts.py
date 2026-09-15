#!/usr/bin/env python3
"""Embed the full text of each script from static/scripts into the docs page that uses it.
Pages contain marker pairs:   <!-- script:NAME -->  ...  <!-- /script:NAME -->
Everything between the markers is regenerated from the file. Run before `docusaurus build`."""
import re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; SCRIPTS = ROOT / "static" / "scripts"
LANG = {".sh": "bash", ".py": "python", ".R": "r"}
def block(name):
    p = SCRIPTS / name
    if not p.exists(): sys.exit(f"missing script: {p}")
    code = p.read_text().rstrip("\n").replace("```", "` ` `")
    return (f"<!-- script:{name} -->\n<details>\n<summary><code>{name}</code> ({len(code.splitlines())} lines)</summary>\n\n"
            f"```{LANG[p.suffix]} title=\"{name}\"\n{code}\n```\n\n</details>\n<!-- /script:{name} -->")
n = 0
for md in (ROOT / "docs").rglob("*.md"):
    s = md.read_text(); new = re.sub(r"<!-- script:([^\s]+) -->.*?<!-- /script:\1 -->", lambda m: block(m.group(1)), s, flags=re.S)
    if new != s: md.write_text(new); n += 1
print(f"embedded scripts into {n} page(s)")
