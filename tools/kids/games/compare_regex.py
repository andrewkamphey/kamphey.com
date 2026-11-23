#!/usr/bin/env python3
"""Compare final game files with the regex question rows.

Usage: python3 -I compare_regex.py QUESTIONS.json OUT_DIR EPISODES.json [EPISODES2.json ...]

Prints how many regex rows were kept, how many were dropped (with a rough reason),
and how many final items the regex never found.
"""
import collections
import difflib
import json
import os
import re
import sys

REGEX_CAT = {"What Am I?": "what-am-i.json", "This or That": "this-or-that.json", "More or Less": "more-or-less.json"}


def norm(s):
    return re.sub(r"[^a-z0-9 ]+", "", s.lower().replace("|", " ")).strip()


def text(it):
    return norm(" ".join(it["clues"]) if "clues" in it else it["prompt"])


STOP = set("a an the i im am me my you your and or of to in is it be can on with what".split())


def similar(a, b):
    """Best of plain similarity and word overlap (regex rows often carry extra junk sentences)."""
    ta, tb = set(a.split()) - STOP, set(b.split()) - STOP
    overlap = len(ta & tb) / min(len(ta), len(tb)) if ta and tb else 0
    return max(difflib.SequenceMatcher(None, a, b).ratio(), overlap * 0.9)


def main():
    qpath, out_dir, *ep_paths = sys.argv[1:]
    rows = [r for r in json.load(open(qpath)) if r["category"] in REGEX_CAT]
    club = set()
    for p in ep_paths:
        club |= {norm(e["title"]) for e in json.load(open(p)) if e.get("club")}
    finals = {c: json.load(open(os.path.join(out_dir, f))) for c, f in REGEX_CAT.items()}
    matched_ids = set()
    reasons = collections.Counter()
    examples = collections.defaultdict(list)
    kept = collections.Counter()
    for r in rows:
        cat, ep, q = r["category"], norm(r["episode"]), norm(r["question"])
        ans = norm(r.get("answer", ""))
        pool = finals[cat]
        same = [it for it in pool if norm(it["episode"]) == ep]
        # For What Am I? rows the regex often put the first clue in "answer" and junk in "question".
        if cat == "What Am I?" and len(ans) > 8:
            hit = [it for it in same if ans in text(it)]
            if hit:
                kept[cat] += 1
                matched_ids.add(hit[0]["id"])
                continue
        best = max(same, key=lambda it: similar(q, text(it)), default=None)
        ok = best and (similar(q, text(best)) >= 0.55 or
                       (cat == "What Am I?" and ans and ans == norm(best["answer"])) or
                       (cat == "More or Less" and q and q in text(best)))
        if ok:
            kept[cat] += 1
            matched_ids.add(best["id"])
            continue
        if ep in club:
            why = "Curious Kids Club episode"
        elif any(similar(q, text(it)) >= 0.7 for it in pool if norm(it["episode"]) != ep):
            why = "replay of an earlier episode"
        elif re.search(r"this sound|like this|listen to this|or this\b", r["question"] + " " + r.get("notes", ""), re.I):
            why = "audio-only"
        elif cat == "More or Less":
            why = "not a usable comparison (fragment or false positive)"
        elif cat == "This or That" and "rather" not in q:
            why = "not a would-you-rather (fragment or false positive)"
        elif cat == "What Am I?" and len(r["question"].split("|")) < 2:
            why = "fragment or garbled clues"
        else:
            why = "judged unusable (garbled, context-dependent, too technical, or no clear answer)"
        reasons[(cat, why)] += 1
        if len(examples[(cat, why)]) < 3:
            examples[(cat, why)].append(f"{r['episode']}: {r['question'][:90]}")
    print("regex rows kept (matched to a final item):", dict(kept))
    print("regex rows dropped:")
    for (cat, why), n in sorted(reasons.items()):
        print(f"  {cat:13} {n:4}  {why}")
        for ex in examples[(cat, why)]:
            print("        e.g.", ex)
    print("final items the regex missed:")
    for cat, pool in finals.items():
        missed = [it for it in pool if it["id"] not in matched_ids]
        print(f"  {cat:13} {len(missed)} of {len(pool)}")


if __name__ == "__main__":
    main()
