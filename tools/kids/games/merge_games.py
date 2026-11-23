#!/usr/bin/env python3
"""Merge hand-cleaned batch files into the three final game JSON files.

Usage:
  python3 -I merge_games.py BATCH_DIR OUT_DIR --episodes EPISODES.json [--episodes w=WHISPER_EPISODES.json]
         [--report REPORT.json]

Batch files (BATCH_DIR/batch-*.json) hold compact items:
  {"c": "wai"|"tot"|"mol", "ep": <order> or "<prefix><order>", ...fields}
"ep" is an episode order index from an episodes file written by extract_games.py.
A bare int uses the unprefixed --episodes file; "w12" uses the file given as w=...

Steps: join episode title and date, drop near-duplicates (replays; the earliest
copy wins), sort by date and order, assign ids, fill defaults, validate, and write
what-am-i.json, this-or-that.json and more-or-less.json to OUT_DIR.
"""
import argparse
import difflib
import glob
import json
import os
import re
import sys

CATS = {
    "wai": ("what-am-i", "wai", "what-am-i.json"),
    "tot": ("this-or-that", "tot", "this-or-that.json"),
    "mol": ("more-or-less", "mol", "more-or-less.json"),
}
DASHES = re.compile("[—–]")


def norm(s):
    return re.sub(r"[^a-z0-9 ]+", "", s.lower().replace("-", " ")).strip()


def dedupe_text(it):
    if it["c"] == "wai":
        return norm(" ".join(it["clues"])) + " => " + norm(it["answer"])
    if it["c"] == "mol":
        return norm(it["prompt"]) + " => " + norm(it["answer"])
    return norm(it["prompt"])


def load_episodes(specs):
    eps = {}
    for spec in specs:
        prefix, path = spec.split("=", 1) if "=" in spec else ("", spec)
        for e in json.load(open(path)):
            eps[f"{prefix}{e['order']}"] = e
    return eps


def validate(it):
    errs = []
    c = it["category"]
    if c == "what-am-i":
        if not 2 <= len(it["clues"]) <= 4:
            errs.append(f"{len(it['clues'])} clues")
        if not it["answer"].strip():
            errs.append("empty answer")
        if not isinstance(it["accept"], list):
            errs.append("accept not a list")
    else:
        opts = it["options"]
        lo, hi = (2, 3) if c == "this-or-that" else (2, 2)
        if not lo <= len(opts) <= hi:
            errs.append(f"{len(opts)} options")
        for o in opts:
            if not 1 <= len(o.split()) <= 4:
                errs.append(f"option '{o}' has {len(o.split())} words")
        if len(set(o.lower() for o in opts)) != len(opts):
            errs.append("duplicate options")
        if c == "this-or-that" and "joshPick" in it and it["joshPick"] not in range(len(opts)):
            errs.append("bad joshPick")
        if c == "more-or-less" and it["answer"] not in opts:
            errs.append("answer not in options")
    if not it["date"]:
        errs.append("no date")
    if DASHES.search(json.dumps(it, ensure_ascii=False)):
        errs.append("em/en dash")
    return errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("batch_dir")
    ap.add_argument("out_dir")
    ap.add_argument("--episodes", action="append", required=True)
    ap.add_argument("--report", help="write a JSON report of dropped duplicates")
    ap.add_argument("--threshold", type=float, default=0.88,
                    help="similarity at or above which two items count as duplicates")
    a = ap.parse_args()

    eps = load_episodes(a.episodes)
    items = []
    for f in sorted(glob.glob(os.path.join(a.batch_dir, "batch-*.json"))):
        for it in json.load(open(f)):
            key = str(it["ep"])
            if key not in eps:
                sys.exit(f"{f}: unknown episode {key}")
            e = eps[key]
            it["_episode"], it["_date"] = e["title"], e["date"]
            it["_sort"] = (e["date"] or "9999", 0 if key[0].isdigit() else 1, e["order"])
            it["_file"] = os.path.basename(f)
            items.append(it)

    items.sort(key=lambda x: x["_sort"])
    kept, dropped = [], []
    seen = {c: [] for c in CATS}
    for it in items:
        t = dedupe_text(it)
        dup = None
        # Replays live in a different episode, so items from the same episode are never
        # duplicates (games like "faster or slower than a tornado?" repeat one template).
        # More or Less prompts are short templates, so they need a stricter match.
        thr = max(a.threshold, 0.95) if it["c"] == "mol" else a.threshold
        for prev_t, prev in seen[it["c"]]:
            if prev["_episode"] == it["_episode"] and prev["ep"] == it["ep"]:
                continue
            # A replay under the same title (only casing or punctuation changed) gets a looser match.
            pthr = 0.7 if norm(prev["_episode"]) == norm(it["_episode"]) else thr
            if prev_t == t or (abs(len(prev_t) - len(t)) < 0.3 * max(len(t), 1)
                               and difflib.SequenceMatcher(None, prev_t, t).ratio() >= pthr):
                dup = prev
                break
        if dup:
            dropped.append({"category": it["c"], "episode": it["_episode"], "date": it["_date"],
                            "text": t[:120], "kept_episode": dup["_episode"], "kept_date": dup["_date"]})
            continue
        seen[it["c"]].append((t, it))
        kept.append(it)

    os.makedirs(a.out_dir, exist_ok=True)
    problems = 0
    summary = {}
    for c, (cat, prefix, fname) in CATS.items():
        out = []
        for n, it in enumerate([x for x in kept if x["c"] == c], 1):
            rec = {"id": f"{prefix}-{n:04d}", "category": cat}
            if c == "wai":
                rec["clues"] = it["clues"]
                rec["answer"] = it["answer"]
                rec["accept"] = it.get("accept", [])
                rec["explain"] = it.get("explain", "")
            elif c == "tot":
                rec["prompt"] = it["prompt"]
                rec["options"] = it["options"]
                if "joshPick" in it:
                    rec["joshPick"] = it["joshPick"]
                if it.get("joshSays"):
                    rec["joshSays"] = it["joshSays"]
            else:
                rec["prompt"] = it["prompt"]
                rec["options"] = it["options"]
                rec["answer"] = it["answer"]
                rec["explain"] = it.get("explain", "")
            if it.get("needsReview"):
                rec["needsReview"] = True
            rec["episode"] = it["_episode"]
            rec["date"] = it["_date"]
            for e in validate(rec):
                problems += 1
                print(f"INVALID {rec['id']} ({it['_file']} ep {it['ep']}): {e}", file=sys.stderr)
            out.append(rec)
        with open(os.path.join(a.out_dir, fname), "w") as fh:
            json.dump(out, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        summary[cat] = {"count": len(out), "needsReview": sum(1 for r in out if r.get("needsReview"))}

    if a.report:
        with open(a.report, "w") as fh:
            json.dump({"summary": summary, "duplicates_dropped": dropped}, fh, indent=2, ensure_ascii=False)
    print(json.dumps(summary))
    print(f"{len(dropped)} duplicates dropped, {problems} validation problems")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
