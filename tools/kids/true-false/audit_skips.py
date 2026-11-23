#!/usr/bin/env python3
"""List markers the draft parser skipped whose following text is substantial
(possible missed statements). Usage: python3 -I audit_skips.py SEG_TXT..."""
import re, sys
sys.path.insert(0, __import__("os").path.dirname(__file__))
import draft_tf as d
for p in sys.argv[1:]:
    text = open(p).read()
    for block in re.split(r"^=== ", text, flags=re.M)[1:]:
        head, _, seg = block.partition("\n")
        flat = seg.replace("\n", f" {d.NL} ")
        marks = list(d.TF.finditer(flat))
        for k, m in enumerate(marks):
            end = marks[k + 1].start() if k + 1 < len(marks) else len(flat)
            chunk = flat[m.end():end]
            stmt, _, rest = chunk.partition(d.NL)
            s = d.clean_stmt(stmt)
            if (not s or (d.INTRO.match(s) and len(s) < 70)) and len(rest.strip()) > 30:
                print(f"{p[-10:]} | {head.split('|')[0].strip()} | stmt={s!r}\n    {rest.replace(d.NL,' ')[:300]}")
