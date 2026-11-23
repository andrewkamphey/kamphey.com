"""Print snippets around game markers for given episode orders: snip.py TRANSCRIPTS.json EPISODES.json ORDER[,ORDER...] [after]"""
import json, re, sys
d = json.load(open(sys.argv[1]))["episodes"]
eps = {e["order"]: e for e in json.load(open(sys.argv[2]))}
after = int(sys.argv[4]) if len(sys.argv) > 4 else 500
for o in map(int, sys.argv[3].split(",")):
    t = re.sub(r"\[\d\d:\d\d:\d\d\]\s*(Josh:\s*)?", "", d[eps[o]["file_index"]]["text"]).replace("\n", " ")
    print(f"##### [{o}] {eps[o]['title']}")
    last = -1
    for m in re.finditer(r"would you rather|what am i\b|who am i\b|riddle", t, re.I):
        if m.start() < last: continue
        print("  ..." + t[max(0, m.start() - 150):m.start() + after] + "\n")
        last = m.start() + after
