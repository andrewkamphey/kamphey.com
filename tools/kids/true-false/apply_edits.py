#!/usr/bin/env python3
"""Apply review edits to a draft batch and write the cleaned batch.

Usage:
  python3 -I apply_edits.py DRAFT_JSON EDITS_TXT OUT_JSON

EDITS_TXT, one directive per line (K = draft item number "k"):
  # comment
  -K reason             drop item K (reason is recorded)
  K p=...               override prompt
  K a=T | a=F           override answer
  K e=...               override explain ("e=" clears it)
  K r                   mark needsReview
  (several fields on one line are separated by " ;; ")
  +K T | prompt | explain        add an item after K, same episode
  +@Episode title@ T | prompt | explain   add an item for an episode with no draft items
Items left with no answer cause an error. Dropped items go to OUT_JSON with
".dropped.json" suffix.
"""
import json
import re
import sys


def fix(s):
    s = s.replace("\u2014", ", ").replace("\u2013", "-").strip()
    return re.sub(r"\s+", " ", s)


def main():
    draft_p, edits_p, out_p = sys.argv[1:4]
    draft = json.load(open(draft_p))
    by_k = {it["k"]: it for it in draft}
    eps = {it["episode"]: it for it in draft}
    adds_after, extra, dropped = {}, [], []
    meta_p = re.sub(r"/[^/]+$", "", draft_p) + "/../segs/seg-episodes.json"
    for line in open(edits_p):
        line = line.rstrip("\n")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith("-"):
            k, _, reason = line[1:].partition(" ")
            by_k[int(k)]["_drop"] = reason.strip() or "dropped"
            continue
        if line.startswith("+"):
            m = re.match(r"\+(?:@(.+?)@|(\d+))\s+([TF?])\s*\|\s*(.*?)\s*(?:\|\s*(.*))?$", line)
            if not m:
                sys.exit(f"bad add line: {line}")
            title, k, a, prompt, expl = m.groups()
            if k:
                base = by_k[int(k)]
                src = {"episode": base["episode"], "date": base["date"], "source": base["source"]}
            else:
                base = eps.get(title)
                if not base:
                    sys.exit(f"unknown episode for add (give date via draft): {title}")
                src = {"episode": base["episode"], "date": base["date"], "source": base["source"]}
            it = dict(src, prompt=prompt, answer={"T": True, "F": False}.get(a), explain=expl or "", added=True)
            if a == "?":
                it["needsReview"] = True
            (adds_after.setdefault(int(k), []) if k else extra).append(it)
            continue
        m = re.match(r"(\d+)\s+(.*)$", line)
        if not m:
            sys.exit(f"bad line: {line}")
        it = by_k[int(m.group(1))]
        for part in m.group(2).split(" ;; "):
            part = part.strip()
            if part == "r":
                it["needsReview"] = True
            elif part.startswith("p="):
                it["prompt"] = part[2:]
            elif part.startswith("e="):
                it["explain"] = part[2:]
            elif part.startswith("a="):
                it["answer"] = {"T": True, "F": False}[part[2:].strip()]
            else:
                sys.exit(f"bad field: {part} in {line}")
    out = []
    for it in draft:
        if "_drop" in it:
            dropped.append({"episode": it["episode"], "prompt": it["prompt"], "reason": it["_drop"]})
        else:
            out.append(it)
        out.extend(adds_after.get(it["k"], []))
    out.extend(extra)
    clean = []
    for it in out:
        if it.get("answer") is None and not it.get("needsReview"):
            sys.exit(f"no answer: {it.get('k')} {it['prompt']}")
        c = {"prompt": fix(it["prompt"]), "answer": it["answer"], "explain": fix(it.get("explain", "")),
             "episode": it["episode"], "date": it["date"], "source": it["source"]}
        if it.get("needsReview"):
            c["needsReview"] = True
        if it.get("added"):
            c["added"] = True
        clean.append(c)
    json.dump(clean, open(out_p, "w"), indent=1, ensure_ascii=False)
    json.dump(dropped, open(out_p.replace(".json", ".dropped.json"), "w"), indent=1, ensure_ascii=False)
    print(f"{len(clean)} kept, {len(dropped)} dropped, "
          f"{sum(1 for c in clean if c.get('needsReview'))} needsReview -> {out_p}")


if __name__ == "__main__":
    main()
