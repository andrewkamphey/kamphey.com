"""List episodes where the raw transcript has game markers but no batch items: coverage.py TRANSCRIPTS.json EPISODES.json BATCH_DIR"""
import json, re, sys, glob, collections
d = json.load(open(sys.argv[1]))["episodes"]
eps = json.load(open(sys.argv[2]))
items = []
for f in sorted(glob.glob(sys.argv[3] + "/batch-*.json")):
    items += json.load(open(f))
have = collections.defaultdict(collections.Counter)
for it in items:
    have[it["ep"]][it["c"]] += 1
for e in eps:
    if e.get("club"): continue
    t = d[e["file_index"]]["text"]
    wyr = len(re.findall(r"would you rather", t, re.I))
    wai = len(re.findall(r"what am i\b|who am i\b|riddle", t, re.I))
    h = have[e["order"]]
    flag = []
    if wyr and not h["tot"]: flag.append(f"WYR={wyr}")
    if wai and not h["wai"]: flag.append(f"WAI={wai}")
    if flag: print(e["order"], e["title"][:60], " ".join(flag), dict(h))
