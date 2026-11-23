#!/usr/bin/env python3
"""Pull the "true or false" game section out of each Curious Kids Every Day transcript.

Usage:
  python3 -I extract_tf.py TRANSCRIPTS_JSON OUT_DIR [--per-batch 30] [--only-new SEEN_TITLES_TXT]
                           [--prefix seg] [--tail 3]

Writes OUT_DIR/episodes.json (title, date, source, order) and
OUT_DIR/seg-NN.txt batch files, oldest episode first. Each segment runs from
the line holding the first "true or false" up to a couple of lines after the
last one, stopping at the outro. Timestamps and speaker labels are stripped.
"""
import argparse
import datetime as dt
import json
import os
import re

TF = re.compile(r"true\s*(?:or|,)\s*false", re.I)
OUTRO = re.compile(r"today we learned|keep asking questions|stay curious kids|see you tomorrow", re.I)
LINE_PREFIX = re.compile(r"^\[\d\d:\d\d(?::\d\d)?\]\s*(?:[A-Z][\w .'-]{0,30}:\s*)?")


def parse_date(meta, fetched):
    first = (meta or "").split("•")[0].strip()
    fetched_day = dt.date.fromisoformat(fetched[:10])
    if first.lower() == "today":
        return fetched_day.isoformat()
    if first.lower() == "yesterday":
        return (fetched_day - dt.timedelta(days=1)).isoformat()
    for fmt in ("%d %b %Y", "%d %B %Y", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(first, fmt).date().isoformat()
        except ValueError:
            pass
    return ""


def segment(text, tail=3):
    lines = [LINE_PREFIX.sub("", l).strip() for l in text.split("\n")]
    lines = [l for l in lines if l]
    hits = [i for i, l in enumerate(lines) if TF.search(l)]
    if not hits:
        return None
    start = max(0, hits[0] - 1)  # one line of lead-in for "Let's play" context
    end = min(len(lines), hits[-1] + tail)
    for j in range(hits[-1] + 1, end):
        if OUTRO.search(lines[j]):
            end = j + 1
            break
    return "\n".join(lines[start:end])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("transcripts")
    ap.add_argument("out_dir")
    ap.add_argument("--per-batch", type=int, default=30)
    ap.add_argument("--only-new", help="text file of titles already processed; skip them")
    ap.add_argument("--prefix", default="seg")
    ap.add_argument("--tail", type=int, default=3,
                    help="lines kept after the last marker (whisper lines are short; use ~10)")
    a = ap.parse_args()

    data = json.load(open(a.transcripts))
    fetched = data.get("fetched") or dt.date.today().isoformat()
    eps = data["episodes"]
    skip = set()
    if a.only_new:
        skip = {l.strip() for l in open(a.only_new) if l.strip()}

    rows = []
    n = len(eps)
    for idx, e in enumerate(eps):
        date = e.get("date") or parse_date(e.get("meta", ""), fetched)
        # source lists newest first; reverse index keeps same-day order stable
        rows.append({"title": e["title"], "date": date, "source": e.get("source", "rephonic"),
                     "order": n - idx, "seg": segment(e.get("text", ""), a.tail)})
    # Undated episodes (meta holds a description instead): place them one day
    # after the next-older dated episode, since the source is newest first.
    for i, r in enumerate(rows):
        if not r["date"]:
            older = next((x["date"] for x in rows[i + 1:] if x["date"]), "")
            if older:
                r["date"] = (dt.date.fromisoformat(older) + dt.timedelta(days=1)).isoformat()
                r["date_inferred"] = True
    rows.sort(key=lambda r: (r["date"], r["order"]))

    os.makedirs(a.out_dir, exist_ok=True)
    meta = [{k: r[k] for k in ("title", "date", "source", "order")}
            | {"has_tf": r["seg"] is not None, "date_inferred": r.get("date_inferred", False)}
            for r in rows]
    json.dump(meta, open(os.path.join(a.out_dir, f"{a.prefix}-episodes.json"), "w"), indent=1)

    todo = [r for r in rows if r["seg"] and r["title"] not in skip]
    for b in range(0, len(todo), a.per_batch):
        chunk = todo[b:b + a.per_batch]
        path = os.path.join(a.out_dir, f"{a.prefix}-{b // a.per_batch + 1:02d}.txt")
        with open(path, "w") as f:
            for r in chunk:
                f.write(f"=== {r['title']} | {r['date']} | {r['source']}\n{r['seg']}\n\n")
    print(f"{len(rows)} episodes, {len(todo)} with true/false, "
          f"{(len(todo) + a.per_batch - 1) // a.per_batch} batches -> {a.out_dir}")


if __name__ == "__main__":
    main()
