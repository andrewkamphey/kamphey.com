#!/usr/bin/env python3
"""Rough first pass over a seg-NN.txt batch: split each episode's segment on
"true or false" markers and guess statement / verdict / reason.

Usage:
  python3 -I draft_tf.py SEG_TXT DRAFT_JSON [--show]

The draft is only a starting point for review; the review edits are applied
with apply_edits.py.
"""
import json
import re
import sys

NL = " "  # line-break marker inside the flattened segment
TF = re.compile(r"\btrue\s*(?:or|,)\s*false\b[\s?.,!:]*", re.I)
POSTFIX = re.compile(r"([^.?!" + NL + r"]{6,}[.?!,])\s*(?:is that|is it|is this|so is that|is this one)\s*$", re.I)
VERDICT_SENT = re.compile(
    r"(?:^|(?<=[.?!])\s+)((?:(?:yes|no|nope|yep|yeah|right|correct|oh|ooh|well|so|okay|ok|actually|good job|you got it)[,!.]*\s+)*"
    r"(?:that'?s|that is|that one is|this one is|this is|it'?s|it is|that one'?s|this one'?s)?\s*"
    r"(?:also |actually |definitely |totally |absolutely |completely |100% |really |so |very |kind of |sort of )?"
    r"(true|false)\b(?:\s+again|\s+too|\s+also)?)", re.I)
VERDICT_ANY = re.compile(r"\b(true|false)\b", re.I)
VERDICT_START = re.compile(r"^\W*(yes|yep|yeah|correct|right|you got it|nope|no|wrong|incorrect)\b", re.I)
STOP = re.compile(
    r"(would you rather|let'?s play|let'?s do|let'?s have|let'?s see|"
    r"(?:okay|ok|all right|alright|now),? (?:let'?s|we|here|one|now|time|last|next|are you|you ready|ready)|"
    r"here'?s (?:another|one more|the next|a|the last)|one more|next one|another one|last one|"
    r"what am i|this or that|we'?ve got one more game|time for|are you ready|ready for)", re.I)
LEAD = re.compile(
    r"^(?:(?:this is the last one|last one|one more|here'?s another one|here'?s another|here'?s one|next one|next|"
    r"and the last one|and|okay|ok|all right|alright|here we go|so|now|number \w+|question \w+|first one|"
    r"here'?s the first one|the first one|how about this one|what about this one|and finally|finally)[,.!:]?\s+)+", re.I)
INTRO = re.compile(r"^(are you ready|you ready|okay|ok|alright|all right|here we go|let'?s go|let'?s play|and we'?ll|"
                   r"i'?ll say|ready|i'?ve got (?:a few|some|\w+ (?:for you|questions))|here are|let'?s see|i'?m going to|i'?ll tell|you tell me|you decide|you shout|i'?ll read)", re.I)
FILLER = re.compile(r"^(very good|good job|great job|nice|nice job|you got it|good|awesome|wow|yes|yeah|yep|"
                    r"that'?s right|right|correct|exactly|one more|ok|okay|all right|alright|great|"
                    r"did you get it( right)?|how did you do|good guess|that'?s a tricky one|tricky|ooh|oh)\W*$", re.I)


def first_sentence(s):
    s = s.strip()
    m = re.match(r"(.+?[.!?])(\s|$)", s)
    return (m.group(1) if m else s).strip()


def clean_stmt(s):
    s = s.replace(NL, " ")
    s = re.sub(r"\s+", " ", s).strip(" ?.,:")
    s = LEAD.sub("", s).strip(" ?.,:")
    if not s:
        return ""
    return s[0].upper() + s[1:] + ("" if s.endswith((".", "!", "?")) else ".")


def parse_episode(title, date, source, seg):
    flat = seg.replace("\n", f" {NL} ")
    marks = list(TF.finditer(flat))
    # For each marker work out where its statement starts and where the answer starts.
    spans = []
    for m in marks:
        before = flat[:m.start()]
        line_before = before.rsplit(NL, 1)[-1]
        pm = POSTFIX.search(line_before) or POSTFIX.search(before[-200:])
        if pm:  # "Birds can fly. Is that true or false?"
            stmt_start = m.start() - (len(before[-200:]) - pm.start(1)) if not POSTFIX.search(line_before) \
                else m.start() - (len(line_before) - pm.start(1))
            spans.append({"kind": "post", "s0": stmt_start, "s1": m.start(), "a0": m.end(), "mark": m})
        else:
            spans.append({"kind": "pre", "s0": m.end(), "s1": None, "a0": None, "mark": m})
    items = []
    for k, sp in enumerate(spans):
        nxt = spans[k + 1]["s0"] if k + 1 < len(spans) else len(flat)
        nxt_mark = spans[k + 1]["mark"].start() if k + 1 < len(spans) else len(flat)
        if sp["kind"] == "post":
            stmt = flat[sp["s0"]:sp["s1"]]
            stmt = re.sub(r"(?:is that|is it|is this|so is that|is this one)\s*$", "", stmt.strip(), flags=re.I)
            rest = flat[sp["a0"]:min(nxt, nxt_mark)]
        else:
            chunk = flat[sp["s0"]:min(nxt, nxt_mark)]
            if NL in chunk:
                stmt, rest = chunk.split(NL, 1)
            else:
                stmt, rest = chunk, ""
            # verdict spoken on the same line as the statement
            vm = VERDICT_SENT.search(stmt)
            if vm and vm.start(1) > 5:
                rest = stmt[vm.start(1):] + " " + rest
                stmt = stmt[:vm.start(1)]
            elif not rest.replace(NL, "").strip():
                mm = re.match(r"(.+?[?])\s+(.*)", stmt)
                if mm:
                    stmt, rest = mm.group(1), mm.group(2)
        before = flat[max(0, sp["mark"].start() - 25):sp["mark"].start()].lower()
        stmt_c = clean_stmt(stmt)
        rest = re.sub(r"\s+", " ", rest.replace(NL, " ")).strip()
        if not stmt_c or (re.search(r"(play|game of|round of|some)\s*$", before) and len(stmt_c) < 4):
            continue
        if INTRO.match(stmt_c) and len(stmt_c) < 70:
            continue
        ans, after = None, rest
        vm = VERDICT_SENT.search(rest[:120])
        if vm:
            ans = vm.group(2).lower() == "true"
            after = rest[vm.end():]
        else:
            vs = VERDICT_START.match(rest)
            if vs:
                ans = vs.group(1).lower() not in ("nope", "no", "wrong", "incorrect")
                after = rest[vs.end():]
            else:
                va = VERDICT_ANY.search(rest[:60])
                if va:
                    ans = va.group(1).lower() == "true"
                    after = rest[va.end():]
        after = after.lstrip(" .!,")
        sm = STOP.search(after)
        expl = after[:sm.start()] if sm else after
        expl = first_sentence(expl) if expl.strip() else ""
        expl = re.sub(r"^(?:remember|and|so|well|but|now|see|ok|okay|oh|ooh)[,!]?\s+", "", expl, flags=re.I)
        if FILLER.match(expl) or len(expl) < 8 or expl.endswith("?"):
            expl = ""
        expl = expl[:1].upper() + expl[1:]
        items.append({"episode": title, "date": date, "source": source, "prompt": stmt_c,
                      "answer": ans, "explain": expl, "raw": rest[:240]})
    return items


def main():
    seg_path, out_path = sys.argv[1], sys.argv[2]
    text = open(seg_path).read()
    eps = re.split(r"^=== ", text, flags=re.M)[1:]
    out = []
    for block in eps:
        head, _, seg = block.partition("\n")
        title, date, source = [x.strip() for x in head.split("|")]
        out.extend(parse_episode(title, date, source, seg.strip()))
    for i, it in enumerate(out):
        it["k"] = i
    json.dump(out, open(out_path, "w"), indent=1, ensure_ascii=False)
    if "--show" in sys.argv:
        cur = None
        for it in out:
            if it["episode"] != cur:
                cur = it["episode"]
                print(f"\n## {cur}")
            a = {True: "T", False: "F", None: "?"}[it["answer"]]
            print(f"{it['k']} [{a}] {it['prompt']}  {{e: {it['explain']}}}\n   > {it['raw']}")


if __name__ == "__main__":
    main()
