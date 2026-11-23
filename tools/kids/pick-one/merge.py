#!/usr/bin/env python3
"""Merge cleaned Pick One batches into the app's data file.

Usage: python3 -I merge.py CLEAN_DIR QUESTIONS.json OUT.json [--report report.json]

CLEAN_DIR holds batch-*.json files ({"items": [...], "dropped": [...]}) written
while reading the extracted quiz sections (see extract_sections.py). This script
dedupes (keeps the earliest episode), validates, assigns ids po-0001.. in
episode-date order and writes OUT.json. It also prints coverage stats against
the regex-extracted questions file.
"""
import argparse, collections, difflib, glob, json, re, sys
from pathlib import Path

FIELDS = ["id", "category", "prompt", "answer", "choices", "explain",
          "episode", "date", "needsReview"]


def norm(s):
    s = s.lower().replace("’", "'")
    s = re.sub(r"[^a-z0-9' ]+", " ", s)
    s = re.sub(r"^(and|so|okay|ok|alright|all right|now|then)\s+", "", s.strip())
    return re.sub(r"\s+", " ", s).strip()


def similar(a, b):
    return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()


def is_dup(x, y):
    """Same question asked again (replay or repeated fact)."""
    p = similar(x["prompt"], y["prompt"])
    if re.search(r"\d", x["answer"] + y["answer"]):
        same_answer = norm(x["answer"]) == norm(y["answer"])
    else:
        same_answer = similar(x["answer"], y["answer"]) >= 0.8
    return p >= 0.97 or (same_answer and p >= 0.8)


def validate(it):
    errs = []
    for k in ("prompt", "answer", "episode", "date"):
        if not str(it.get(k, "")).strip():
            errs.append(f"empty {k}")
    ch = it.get("choices", [])
    if len(ch) != 2 or any(not str(c).strip() for c in ch):
        errs.append("need exactly 2 non-empty choices")
    lows = [norm(it.get("answer", ""))] + [norm(c) for c in ch]
    if len(set(lows)) != len(lows):
        errs.append("choices repeat the answer or each other")
    for k in ("prompt", "answer", "explain", *[f"c{i}" for i in range(len(ch))]):
        v = it.get(k) if not k.startswith("c") else ch[int(k[1:])]
        if v and ("—" in v or "–" in v):
            errs.append(f"dash in {k}")
    return errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("clean_dir")
    ap.add_argument("questions")
    ap.add_argument("out")
    ap.add_argument("--report")
    ap.add_argument("--manual-dups", help="JSON list of {episode, prompt} to drop as "
                    "same-fact repeats of an earlier episode")
    a = ap.parse_args()

    items, dropped = [], []
    for f in sorted(glob.glob(str(Path(a.clean_dir) / "*.json"))):
        d = json.load(open(f))
        for it in d["items"]:
            it["_file"] = Path(f).name
            items.append(it)
        dropped += d.get("dropped", [])

    bad = [(it["episode"], it.get("prompt"), validate(it)) for it in items if validate(it)]
    if bad:
        for b in bad:
            print("INVALID", b, file=sys.stderr)
        sys.exit(1)

    manual = set()
    if a.manual_dups:
        manual = {(m["episode"], m["prompt"]) for m in json.load(open(a.manual_dups))}
    items.sort(key=lambda x: (x["date"], x["episode"]))
    kept, dups = [], []
    for it in items:
        hit = next((k for k in kept if is_dup(it, k)), None)
        if not hit and (it["episode"], it["prompt"]) in manual:
            hit = {"episode": "(manual)", "prompt": "same fact asked in an earlier episode"}
        if hit:
            dups.append({"dropped": it, "kept": hit})
        else:
            kept.append(it)

    out = []
    for i, it in enumerate(kept, 1):
        row = {"id": f"po-{i:04d}", "category": "pick-one"}
        for k in FIELDS[2:]:
            if k in it and it[k] not in (None, "", False):
                row[k] = it[k]
        out.append(row)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")

    # Coverage vs regex rows
    rows = [r for r in json.load(open(a.questions)) if r["category"] == "Pick One (quiz)"]
    by_ep = collections.defaultdict(list)
    for it in items:
        by_ep[it["episode"]].append(it)
    logged = {(d["episode"], norm(d["q"])): d["why"] for d in dropped}
    kept_ids = {id(k) for k in kept}
    used, used_then_deduped, unused = 0, 0, []
    for r in rows:
        q = norm(r["question"])
        if (r["episode"], q) in logged:
            unused.append(r)
            continue
        hits = [it for it in by_ep.get(r["episode"], [])
                if q and (q in norm(it.get("orig", "")) or similar(q, it.get("orig", "")) > 0.8)]
        if not hits:
            unused.append(r)
        elif any(id(h) in kept_ids for h in hits):
            used += 1
        else:
            used_then_deduped += 1
    unlogged = [r for r in unused if (r["episode"], norm(r["question"])) not in logged]
    regex_by_ep = collections.defaultdict(list)
    for r in rows:
        regex_by_ep[r["episode"]].append(norm(r["question"]))
    missed = [it for it in items
              if not any(q and (q in norm(it.get("orig", "")) or similar(q, it.get("orig", "")) > 0.8)
                         for q in regex_by_ep.get(it["episode"], []))]
    missed_kept = [it for it in missed if id(it) in kept_ids]
    why = collections.Counter(d["why"] for d in dropped)
    stats = {
        "cleaned_items": len(items), "duplicates_removed": len(dups), "final": len(out),
        "needsReview": sum(1 for r in out if r.get("needsReview")),
        "regex_rows": len(rows), "regex_rows_in_final": used,
        "regex_rows_used_but_cross_episode_duplicate": used_then_deduped,
        "regex_rows_dropped": len(unused), "regex_rows_dropped_unlogged": len(unlogged), "drop_reasons_logged": dict(why),
        "found_not_in_regex": len(missed), "found_not_in_regex_final": len(missed_kept),
    }
    print(json.dumps(stats, indent=1))
    if a.report:
        Path(a.report).write_text(json.dumps({
            "stats": stats,
            "duplicates": [{"dropped": (d["dropped"]["episode"], d["dropped"]["prompt"]),
                            "kept": (d["kept"]["episode"], d["kept"]["prompt"])} for d in dups],
            "regex_unused": [(r["episode"], r["question"]) for r in unused],
            "regex_unlogged": [(r["episode"], r["question"]) for r in unlogged],
        }, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
