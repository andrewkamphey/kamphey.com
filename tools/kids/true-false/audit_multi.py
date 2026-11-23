#!/usr/bin/env python3
"""Flag draft items whose answer text holds a second true/false verdict
(a statement read without a "true or false" marker). Usage: audit_multi.py SEG_TXT..."""
import re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import draft_tf as d
V = re.compile(r"(that'?s|that is|it'?s|is that) (also |actually )?(true|false)|\b(true|false)\.", re.I)
for p in sys.argv[1:]:
    text = open(p).read()
    for block in re.split(r"^=== ", text, flags=re.M)[1:]:
        head, _, seg = block.partition("\n")
        flat = seg.replace("\n", " ")
        marks = list(d.TF.finditer(flat))
        for k, m in enumerate(marks):
            end = marks[k + 1].start() if k + 1 < len(marks) else len(flat)
            chunk = flat[m.end():end]
            hits = list(V.finditer(chunk))
            if len(hits) >= 2:
                print(f"{p[-10:]} | {head.split('|')[0].strip()}\n    {chunk[:400]}")
