#!/usr/bin/env python3
"""Embed each script from static/scripts into the docs page that uses it.

Pages contain marker pairs:

    <!-- script:NAME -->
    ...
    <!-- /script:NAME -->

Everything between the markers is regenerated from static/scripts/NAME as a collapsed
<details> block holding the full script.  Runs before every build (npm "prebuild").
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "static" / "scripts"
LANGUAGE = {".sh": "bash", ".py": "python", ".R": "r"}
MARKERS = re.compile(r"<!-- script:([^\s]+) -->.*?<!-- /script:\1 -->", flags=re.S)


def block(name):
    path = SCRIPTS / name
    if not path.exists():
        sys.exit(f"missing script: {path}")
    code = path.read_text().rstrip("\n").replace("```", "` ` `")
    n_lines = code.count("\n") + 1
    return (f"<!-- script:{name} -->\n"
            f"<details>\n"
            f"<summary>Script <code>{name}</code> ({n_lines} lines)</summary>\n\n"
            f"```{LANGUAGE[path.suffix]} title=\"{name}\"\n{code}\n```\n\n"
            f"</details>\n"
            f"<!-- /script:{name} -->")


changed = 0
for page in (ROOT / "docs").rglob("*.md"):
    text = page.read_text()
    updated = MARKERS.sub(lambda m: block(m.group(1)), text)
    if updated != text:
        page.write_text(updated)
        changed += 1
print(f"embedded scripts into {changed} page(s)")
