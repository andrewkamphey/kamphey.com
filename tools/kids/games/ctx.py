#!/usr/bin/env python3
"""Print cleaned transcript text around a phrase: ctx.py TRANSCRIPTS.json "phrase" [chars_after] [chars_before]"""
import json, re, sys
d = json.load(open(sys.argv[1]))
ph, after = sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 1200
before = int(sys.argv[4]) if len(sys.argv) > 4 else 100
for ep in d["episodes"]:
    t = re.sub(r"\[\d\d:\d\d:\d\d\]\s*(Josh:\s*)?", "", ep["text"]).replace("\n", " ")
    for m in re.finditer(re.escape(ph), t, re.I):
        print(f"== {ep['title']}\n{t[max(0, m.start() - before):m.start() + after]}\n")
