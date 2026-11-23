#!/usr/bin/env python3
"""Print transcript context around a regex in one episode.
Usage: python3 -I ctx.py TRANSCRIPTS_JSON "title substring" "regex" [chars]"""
import json, re, sys
d = json.load(open(sys.argv[1]))
n = int(sys.argv[4]) if len(sys.argv) > 4 else 600
for e in d["episodes"]:
    if sys.argv[2].lower() in e["title"].lower():
        t = re.sub(r"\[\d\d:\d\d(?::\d\d)?\] ?(Josh: )?", "", e["text"])
        for m in re.finditer(sys.argv[3], t, re.I):
            print(f"--- {e['title']} @{m.start()}\n{t[max(0, m.start() - n // 3):m.end() + n]}\n")
