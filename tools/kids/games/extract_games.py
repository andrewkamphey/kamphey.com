#!/usr/bin/env python3
"""Pull the "What Am I?", "Would you rather" and comparison (more/less) game
segments out of Curious Kids Every Day transcripts into small batch files that
a person (or model) can read and clean by hand.

Usage:
  python3 -I extract_games.py TRANSCRIPTS.json OUT_DIR [--questions QUESTIONS.json] [--batch-size 30]
         [--only-source whisper] [--prefix extract]

TRANSCRIPTS.json: {"fetched": iso, "episodes": [{"title", "meta", "text", "source"?}]}
  text lines look like "[00:06:14] Josh: ..." (Rephonic) or plain text (whisper).
QUESTIONS.json (optional): regex rows [{episode, date, ...}] used only as a
  fallback for episode dates.

Writes OUT_DIR/<prefix>-episodes.json (order, title, date, source, club, file_index)
and OUT_DIR/<prefix>-NN.txt (one block per episode, oldest first).

Pipeline: extract_games.py -> hand-clean blocks into batch-NN.json -> merge_games.py
(dedupe, ids, validation) -> compare_regex.py (optional report against the regex rows).
"""
import argparse
import datetime as dt
import json
import os
import re

SENT_SPLIT = re.compile(r'(?<=[.?!])\s+(?=[A-Z"\'0-9])')
OUTRO = re.compile(
    r"today,? we learned|keep asking questions|what kind of question do you think"
    r"|turning (one|two|three|four|five|six|seven|eight|nine|ten)\b|happy birthday",
    re.I)
AD = re.compile(r"\.com\b|supportcuriouskids|curious camp|sponsor", re.I)
WYR = re.compile(r"would you rather", re.I)
WAI = re.compile(r"what am i\b|who am i\b|riddle|guess what i am|here are the clues|name that thing", re.I)
PAIR = re.compile(
    r"\b(\w+er|more|less|fewer) or (\w+er|more|less|fewer)\b", re.I)
NOT_COMPARATIVE = {"never", "forever", "brother", "sister", "together", "winter",
                   "summer", "underwater", "water", "under", "over", "after",
                   "ever", "other", "either", "whether", "number", "letter",
                   "paper", "river", "flower", "finger", "computer", "power"}
THAN_Q = re.compile(r"\b(\w+er|more|less|fewer) than\b[^?]*\?", re.I)
WHICH_Q = re.compile(
    r"(?<!, )(?<!,)\bwhich\b(?! means| is why| makes)[^.?!]{0,60}\b(\w{3,}er|more|less|fewer|most|least|\w+est)\b|tell me which|two versions", re.I)
WHICH_SKIP = re.compile(r"\b(remember|ever|never|other|together|water|answer|letter|number|computer|paper|over|under|after|whether|either)\b", re.I)



def clean_text(text):
    lines = []
    for ln in text.splitlines():
        ln = re.sub(r"^\[\d\d:\d\d:\d\d\]\s*", "", ln.strip())
        ln = re.sub(r"^Josh:\s*", "", ln)
        if ln:
            lines.append(ln)
    return " ".join(lines)


def is_pair(m):
    a, b = m.group(1).lower(), m.group(2).lower()
    return a not in NOT_COMPARATIVE and b not in NOT_COMPARATIVE and a != b


def parse_date(meta, fetched):
    first = meta.split(" • ")[0].strip()
    if first.lower() == "yesterday" and fetched:
        return (dt.date.fromisoformat(fetched[:10]) - dt.timedelta(days=1)).isoformat()
    if first.lower() == "today" and fetched:
        return fetched[:10]
    try:
        return dt.datetime.strptime(first, "%d %b %Y").date().isoformat()
    except ValueError:
        return ""


def segments(sents):
    """Return list of (start, end, label) windows over sentence indexes."""
    n = len(sents)
    outro = n
    # The outro starts at the first outro phrase after the last game marker, so a
    # topic word like "birthday" or an early "keep asking questions" can't cut games off.
    last_game = max([i for i, s in enumerate(sents)
                     if (WYR.search(s) or WAI.search(s)) and not AD.search(s)] or [0])
    for i in range(max(int(n * 0.35), last_game + 1), n):
        if OUTRO.search(sents[i]):
            outro = i
            break
    wins = []
    for i in range(outro):
        s = sents[i]
        if AD.search(s):
            continue
        if WYR.search(s):
            wins.append((i, min(i + 5, outro), "WYR"))
        if WAI.search(s):
            wins.append((max(i - 8, 0), min(i + 18, outro), "WAI"))
        which = WHICH_Q.search(s)
        if which and which.group(1) and WHICH_SKIP.fullmatch(which.group(1)):
            which = None
        if any(is_pair(m) for m in PAIR.finditer(s)) or THAN_Q.search(s) or which:
            wins.append((max(i - 1, 0), min(i + 12, outro), "CMP"))
    wins.sort()
    merged = []
    for a, b, lab in wins:
        if merged and a <= merged[-1][1]:
            pa, pb, plab = merged[-1]
            labs = plab if lab in plab.split("+") else plab + "+" + lab
            merged[-1] = (pa, max(pb, b), labs)
        else:
            merged.append((a, b, lab))
    return merged


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("transcripts")
    ap.add_argument("out_dir")
    ap.add_argument("--questions")
    ap.add_argument("--batch-size", type=int, default=30)
    ap.add_argument("--only-source", help="only episodes whose source field equals this (e.g. whisper)")
    ap.add_argument("--prefix", default="extract")
    args = ap.parse_args()

    data = json.load(open(args.transcripts))
    fetched = data.get("fetched", "")
    qdates = {}
    if args.questions:
        for r in json.load(open(args.questions)):
            if r.get("date"):
                qdates.setdefault(r["episode"], r["date"])

    eps = []
    for idx, ep in enumerate(data["episodes"]):
        if args.only_source and ep.get("source") != args.only_source:
            continue
        date = parse_date(ep.get("meta", ""), fetched) or ep.get("date", "") or qdates.get(ep["title"], "")
        eps.append({"title": ep["title"], "date": date, "file_index": idx,
                    "source": ep.get("source", "rephonic"),
                    "club": "curious kids club" in ep["title"].lower() or "curious kid club" in ep["title"].lower(),
                    "text": ep["text"]})
    # undated (meta holds a description): borrow the date of the next older dated
    # episode in file order, which is newest first
    dates = {e["file_index"]: e["date"] for e in eps}
    for e in eps:
        if not e["date"]:
            j = e["file_index"] + 1
            while j in dates and not dates[j]:
                j += 1
            e["date"] = dates.get(j, "")
            e["date_estimated"] = True
    # oldest first; the source file is newest first, so break ties by reverse file order
    eps.sort(key=lambda e: (e["date"] or "9999", -e["file_index"]))

    os.makedirs(args.out_dir, exist_ok=True)
    index = []
    for order, ep in enumerate(eps):
        ep["order"] = order
        index.append({k: ep[k] for k in ("order", "title", "date", "source", "club", "file_index")})
    json.dump(index, open(os.path.join(args.out_dir, f"{args.prefix}-episodes.json"), "w"), indent=1)

    for b in range(0, len(eps), args.batch_size):
        out = []
        for ep in eps[b:b + args.batch_size]:
            sents = [s.strip() for s in SENT_SPLIT.split(clean_text(ep["text"])) if s.strip()]
            segs = segments(sents)
            head = f"### [{ep['order']}] {ep['title']} | {ep['date'] or 'NODATE'}"
            if ep["club"]:
                head += " | CLUB"
            if ep["source"] != "rephonic":
                head += f" | {ep['source']}"
            out.append(head)
            for a, z, lab in segs:
                out.append(f"<{lab}> " + " ".join(sents[a:z]))
            out.append("")
        name = os.path.join(args.out_dir, f"{args.prefix}-{b // args.batch_size + 1:02d}.txt")
        open(name, "w").write("\n".join(out))
    print(f"{len(eps)} episodes -> {(len(eps) + args.batch_size - 1) // args.batch_size} batches in {args.out_dir}")


if __name__ == "__main__":
    main()
