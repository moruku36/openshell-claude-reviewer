#!/usr/bin/env python3
"""Check that relative links in Markdown files resolve and that every ``` fence is closed."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
errs = []
for md in ROOT.rglob("*.md"):
    if ".git" in md.parts or "reports" in md.parts:
        continue
    text = md.read_text()
    if text.count("```") % 2:
        errs.append(f"{md.relative_to(ROOT)}: unclosed code fence")
    for target in re.findall(r"\]\(([^)#\s]+)(?:#[^)]*)?\)", text):
        if re.match(r"[a-z]+:", target):
            continue
        if not (md.parent / target).resolve().exists():
            errs.append(f"{md.relative_to(ROOT)}: broken link {target}")
for e in errs:
    print(e, file=sys.stderr)
print("docs check:", "FAIL" if errs else "OK")
sys.exit(1 if errs else 0)
