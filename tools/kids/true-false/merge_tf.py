#!/usr/bin/env python3
"""Merge cleaned batch files, dedupe, assign ids, validate, write the final JSON.

Usage:
  python3 -I merge_tf.py BATCH_DIR QUESTIONS_JSON OUT_JSON [--report REPORT_JSON]

BATCH_DIR holds batch-*.json (cleaned items) and batch-*.dropped.json.
QUESTIONS_JSON is the regex-extracted index; it is only used for the
comparison report (rows dropped / items the regex missed).
"""
import argparse
import difflib
import glob
import html
import json
import os
import re
import sys
from collections import Counter

STOP = {"a", "an", "the", "is", "are", "of", "to", "and", "that", "it", "can", "do", "does"}


def norm(s):
    s = html.unescape(s).lower().replace("’", "'")
    s = re.sub(r"(?<=\d),(?=\d)", "", s)
    return " ".join(w for w in re.findall(r"[a-z0-9']+", s) if w not in STOP)


def stem(w):
    return w[:-1] if len(w) > 3 and w.endswith("s") else w


def similar(a, b):
    """Near-identical prompts only: high character similarity, and any words
    that differ must be short filler (so "Yawning..." != "Blinking...")."""
    if a == b or a.replace(" ", "") == b.replace(" ", ""):
        return 1.0
    sa, sb = {stem(w) for w in a.split()}, {stem(w) for w in b.split()}
    if not sa or not sb or len(sa & sb) / len(sa | sb) < 0.5:
        return 0.0
    if any(len(w) > 4 for w in sa ^ sb):
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def fix_text(s):
    s = html.unescape(s).replace("\u2014", ", ").replace("\u2013", "-")
    return re.sub(r"\s+", " ", s).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("batch_dir")
    ap.add_argument("questions")
    ap.add_argument("out")
    ap.add_argument("--report")
    a = ap.parse_args()

    items, dropped = [], []
    for p in sorted(glob.glob(os.path.join(a.batch_dir, "batch-*.json"))):
        if p.endswith(".dropped.json"):
            dropped.extend(json.load(open(p)))
        else:
            items.extend(json.load(open(p)))
    items.sort(key=lambda it: it["date"])  # stable: keeps in-episode order

    kept, dupes = [], []
    seen = []  # (norm prompt, index into kept)
    for it in items:
        n = norm(it["prompt"])
        hit = next((j for sn, j in seen if similar(n, sn) >= 0.85), None)
        if hit is not None:
            dupes.append({"episode": it["episode"], "prompt": it["prompt"],
                          "dup_of": kept[hit]["prompt"], "dup_episode": kept[hit]["episode"]})
            continue
        seen.append((n, len(kept)))
        kept.append(it)

    out, errors = [], []
    for i, it in enumerate(kept, 1):
        rec = {"id": f"tf-{i:04d}", "category": "true-false", "prompt": fix_text(it["prompt"]),
               "answer": it["answer"]}
        if it.get("explain"):
            rec["explain"] = fix_text(it["explain"])
        rec["episode"] = fix_text(it["episode"])
        rec["date"] = it["date"]
        if it.get("source") == "whisper":
            rec["source"] = "whisper"
        if it.get("needsReview"):
            rec["needsReview"] = True
        if not isinstance(rec["answer"], bool) and not rec.get("needsReview"):
            errors.append(f"{rec['id']}: answer not boolean")
        for k in ("prompt", "episode", "date"):
            if not rec.get(k):
                errors.append(f"{rec['id']}: missing {k}")
        if "—" in json.dumps(rec, ensure_ascii=False):
            errors.append(f"{rec['id']}: em dash")
        out.append(rec)
    if errors:
        sys.exit("validation failed:\n" + "\n".join(errors))

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
        f.write("\n")

    # Comparison with the regex index
    rows = [r for r in json.load(open(a.questions)) if r["category"] == "True or False"]
    by_ep = {}
    for it in items:
        by_ep.setdefault(norm(it["episode"]), []).append(norm(it["prompt"]))
    drop_by_ep = {}
    for d in dropped:
        drop_by_ep.setdefault(norm(d["episode"]), []).append((norm(d["prompt"]), d["reason"]))
    final_keys = {(norm(r["episode"]), norm(r["prompt"])) for r in out}
    reasons = Counter()
    matched_items = set()
    for r in rows:
        ep, q = norm(r["episode"]), norm(r["question"])
        cands = by_ep.get(ep, [])
        best = max(cands, key=lambda c: difflib.SequenceMatcher(None, q, c).ratio(), default=None)
        if best is not None and difflib.SequenceMatcher(None, q, best).ratio() >= 0.6:
            matched_items.add((ep, best))
            if (ep, best) in final_keys:
                reasons["kept"] += 1
            else:
                reasons["dropped: duplicate of an earlier episode (rerun/replay)"] += 1
            continue
        dc = drop_by_ep.get(ep, [])
        bd = max(dc, key=lambda c: difflib.SequenceMatcher(None, q, c[0]).ratio(), default=None)
        if bd and difflib.SequenceMatcher(None, q, bd[0]).ratio() >= 0.6:
            reasons["dropped: " + bd[1]] += 1
        else:
            reasons["dropped: not a real statement (regex fragment / mis-split)"] += 1
    missed = sum(1 for it in items if (norm(it["episode"]), norm(it["prompt"])) not in matched_items
                 and (norm(it["episode"]), norm(it["prompt"])) in final_keys)
    report = {"final": len(out), "needsReview": sum(1 for r in out if r.get("needsReview")),
              "reviewed_items": len(items), "dupes_removed": len(dupes), "manual_drops": len(dropped),
              "regex_rows": len(rows), "regex_rows_kept": reasons["kept"],
              "regex_rows_dropped": len(rows) - reasons["kept"],
              "regex_drop_reasons": {k: v for k, v in reasons.most_common() if k != "kept"},
              "final_items_regex_missed": missed}
    print(json.dumps(report, indent=1))
    if a.report:
        json.dump(report | {"dupes": dupes, "drops": dropped}, open(a.report, "w"), indent=1,
                  ensure_ascii=False)


if __name__ == "__main__":
    main()
