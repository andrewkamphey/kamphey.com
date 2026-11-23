#!/usr/bin/env python3
"""Pull the quiz/game section out of each Curious Kids transcript into batch files.

Usage: python3 -I extract_sections.py TRANSCRIPTS.json QUESTIONS.json OUT_DIR [--batch-size 30]

Writes OUT_DIR/batch-NN.txt (human-readable sections for review) and
OUT_DIR/episodes.json (title -> date, batch, regex Pick One hints).
Episodes are sorted by date (oldest first). Works for both the Rephonic set
(lines like "[00:04:56] Josh: ...") and whisper transcripts (no speaker labels).
"""
import argparse, json, re, datetime as dt
from pathlib import Path

START = re.compile(r"quick quiz|quiz time|pop quiz|\bquiz\b|see what you remember|"
                   r"what we learned today\?|let'?s see if you remember|"
                   r"true or false|what am i\b|would you rather|let'?s play", re.I)
END = re.compile(r"what kind of question do you think|keep asking questions|"
                 r"today we learned|see you tomorrow", re.I)
MONTHS = {m: i for i, m in enumerate(
    "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(), 1)}


def parse_date(meta, fetched):
    first = (meta or "").split("•")[0].strip()
    m = re.match(r"(\d{1,2}) (\w{3}) (\d{4})", first)
    if m:
        return dt.date(int(m[3]), MONTHS[m[2]], int(m[1])).isoformat()
    base = dt.date.fromisoformat(fetched[:10])
    if first.lower() == "yesterday":
        return (base - dt.timedelta(days=1)).isoformat()
    if first.lower() == "today":
        return base.isoformat()
    m = re.match(r"(\d+) days? ago", first, re.I)
    if m:
        return (base - dt.timedelta(days=int(m[1]))).isoformat()
    return ""


def clean_lines(text):
    out = []
    for line in text.splitlines():
        line = re.sub(r"^\[\d\d:\d\d:\d\d\]\s*", "", line).strip()
        if not line:
            continue
        line = re.sub(r"^Josh:\s*", "", line)  # Josh is the default speaker
        out.append(line)
    return "\n".join(out)


def section(text):
    t = clean_lines(text)
    n = len(t)
    start = None
    for m in START.finditer(t):
        if m.start() > n * 0.3:
            start = m.start()
            break
    if start is None:
        start = int(n * 0.45)
    # back up to the start of the line
    start = t.rfind("\n", 0, start) + 1
    end = n
    for m in END.finditer(t, start):
        # "today we learned" sometimes appears before the games; require some content
        if m.start() - start > 300:
            end = m.start()
            break
    return t[start:end].strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("transcripts")
    ap.add_argument("questions")
    ap.add_argument("out_dir")
    ap.add_argument("--batch-size", type=int, default=30)
    ap.add_argument("--only-whisper", action="store_true",
                    help="only episodes flagged source=whisper")
    ap.add_argument("--prefix", default="batch")
    a = ap.parse_args()
    data = json.load(open(a.transcripts))
    fetched = data.get("fetched", dt.date.today().isoformat())
    rows = json.load(open(a.questions))
    hints, qdates = {}, {}
    for r in rows:
        if r.get("date"):
            qdates.setdefault(r["episode"], r["date"])
        if r["category"] == "Pick One (quiz)":
            hints.setdefault(r["episode"], []).append(r["question"])
    eps = []
    for e in data["episodes"]:
        if a.only_whisper and e.get("source") != "whisper":
            continue
        date = e.get("date") or parse_date(e.get("meta"), fetched) or qdates.get(e["title"], "")
        eps.append({"title": e["title"], "date": date, "source": e.get("source", "rephonic"),
                    "section": section(e["text"])})
    # Episodes with no date in meta: borrow the date of the nearest older
    # episode in feed order (the feed is newest first).
    for i, e in enumerate(eps):
        if not e["date"]:
            later = [x["date"] for x in eps[i + 1:] if x["date"]]
            e["date"] = later[0] if later else ""
            e["date_inferred"] = True
    eps.sort(key=lambda x: (x["date"], x["title"]))
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    index = []
    for i in range(0, len(eps), a.batch_size):
        b = i // a.batch_size + 1
        parts = []
        for e in eps[i:i + a.batch_size]:
            parts.append(f"##### {e['title']} | {e['date']}\n{e['section']}\n")
            index.append({"title": e["title"], "date": e["date"], "batch": b,
                          "source": e["source"], "date_inferred": e.get("date_inferred", False),
                          "regex_hints": hints.get(e["title"], [])})
        (out / f"{a.prefix}-{b:02d}.txt").write_text("\n".join(parts))
    (out / f"{a.prefix}-episodes.json").write_text(json.dumps(index, indent=1))
    print(f"{len(eps)} episodes, {len(index)} indexed, "
          f"{sum(len(e['section']) for e in eps)} chars in sections")


if __name__ == "__main__":
    main()
