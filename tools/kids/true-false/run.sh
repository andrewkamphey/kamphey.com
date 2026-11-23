#!/bin/sh
# Regenerate true-false.json from the reviewed batches.
# Usage: sh run.sh TRANSCRIPTS_JSON TRANSCRIPTS_ALL_JSON QUESTIONS_JSON OUT_JSON
#   TRANSCRIPTS_JSON      Rephonic set (curious-kids-transcripts.json, 495 episodes)
#   TRANSCRIPTS_ALL_JSON  merged set with the whisper episodes (curious-kids-transcripts-all.json)
# Steps: extract game sections -> rough draft per batch -> apply review edits -> merge/dedupe.
# edits/edits-NN.txt and edits/wedits-NN.txt are keyed to draft item numbers, so keep
# extract_tf.py / draft_tf.py behaviour unchanged (or re-review) when regenerating.
set -e
D=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$D/segs" "$D/drafts" "$D/batches" "$D/out"

# Rephonic episodes
python3 -I "$D/extract_tf.py" "$1" "$D/segs"
for s in "$D"/segs/seg-[0-9]*.txt; do
  n=$(basename "$s" .txt | sed 's/seg-//')
  python3 -I "$D/draft_tf.py" "$s" "$D/drafts/draft-$n.json"
  python3 -I "$D/apply_edits.py" "$D/drafts/draft-$n.json" "$D/edits/edits-$n.txt" "$D/batches/batch-$n.json"
done

# Whisper episodes: only titles not in the Rephonic set; whisper lines are short, so keep more tail
python3 -I "$D/extract_tf.py" "$2" "$D/segs" --only-new "$D/rephonic-titles.txt" --prefix wseg --tail 10
for s in "$D"/segs/wseg-[0-9]*.txt; do
  n=$(basename "$s" .txt | sed 's/wseg-//')
  python3 -I "$D/draft_tf.py" "$s" "$D/drafts/wdraft-$n.json"
  python3 -I "$D/apply_edits.py" "$D/drafts/wdraft-$n.json" "$D/edits/wedits-$n.txt" "$D/batches/batch-w$n.json"
done

python3 -I "$D/merge_tf.py" "$D/batches" "$3" "$4" --report "$D/out/report.json"
