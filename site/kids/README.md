# Curious Kids question tester (`/kids`)

A throwaway test app for playing questions from the *Curious Kids Every Day* podcast with a kid, one at a time, before designing a board game around them. Not public: `noindex` meta tag plus an `X-Robots-Tag` header (`site/_headers`), not linked from the homepage, no sitemap. This README is kept out of deploys by `site/.assetsignore`.

## Files

- `index.html`: markup and styles. `app.js`: all the logic, no build step.
- `data/<category>.json`: one array per category: `true-false`, `pick-one`, `what-am-i`, `this-or-that`, `more-or-less`.
- Regeneration scripts and the hand-reviewed batches live outside the deployed folder, in `tools/kids/` at the repo root.

## How the app behaves

- It picks a random category from the chips that are on (never the same one twice in a row), then a random unseen question from it. Once a category's pool runs out, that category starts over.
- All state lives in `localStorage` (`ck.settings`, `ck.session`, `ck.seen`, `ck.flags`). The score button opens the session stats, the settings (read aloud, skip unchecked), and Export flags, which downloads `curious-kids-flags-YYYY-MM-DD.json`.
- Questions marked `needsReview` show a small "unchecked" tag.

## How the data was made

1. **Transcripts.** 495 episodes came from Rephonic (`~/Downloads/curious-kids-transcripts.json`). The missing episodes were transcribed locally with mlx-whisper large-v3-turbo using `~/Downloads/transcribe_missing.py`, then merged into `~/Downloads/curious-kids-transcripts-all.json`. Whisper episodes carry `"source": "whisper"`.
2. **Regex index.** A first regex pass produced `curious-kids-questions.json` (3,729 rows). It was messy, so it was used only as a hint and for episode dates.
3. **Cleanup.** For each category, a script cut each episode's game section out of the transcripts into batches. A Claude agent then read every batch and wrote cleaned items in Josh's wording, with these rules:
   - Drop audio-only references, ad reads, shout-outs and Curious Kids Club items.
   - Drop items with an answer that can't be fixed from the transcript.
   - Mark doubtful items `needsReview` instead of guessing.
   - The Pick One wrong choices were written by the agent for 4 to 7 year olds. Josh's own options are used where he gave them.
4. **Merge.** A merge script dedupes replays (keeping the earliest airing), validates every item, assigns ids in date order, and writes `data/*.json`.

## Regenerating

All scripts take paths as arguments. Run them with `python3 -I`.

| Category | Folder | Command |
|---|---|---|
| True or False | `tools/kids/true-false/` | `sh run.sh TRANSCRIPTS.json TRANSCRIPTS-ALL.json QUESTIONS.json site/kids/data/true-false.json` replays extract, draft, `edits/` (plus `wedits-*` for the Whisper episodes) and merge. Keep `draft_tf.py` unchanged, because the edits are keyed to its item numbers. |
| Pick One | `tools/kids/pick-one/` | `extract_sections.py TRANSCRIPTS.json QUESTIONS.json OUT_DIR` makes batches. The reviewed items are in `clean/`. `merge.py clean QUESTIONS.json site/kids/data/pick-one.json --manual-dups manual-dups.json` merges them. Rules are in `SPEC.md`. |
| What Am I?, This or That, More or Less | `tools/kids/games/` | `extract_games.py TRANSCRIPTS.json OUT_DIR --questions QUESTIONS.json` makes batches. The reviewed items are in `batches/`. From inside the folder, `merge_games.py batches ../../../site/kids/data --episodes ext/extract-episodes.json --episodes w=ext_w/whisper-episodes.json` writes all three files. Batch items point at episodes by their number in the stored index files, so keep those files rather than re-extracting. |

To add new episodes:

1. Re-run `transcribe_missing.py` and rebuild the merged transcript file.
2. Extract only the new episodes (`--only-new`, `--only-whisper` or `--only-source whisper`, depending on the script).
3. Have an agent review the new batches by the same rules.
4. Re-merge.

## Using the flags

Play, flag questions ("Bad question", "Too hard", "Great one"), then export. The export lists each flagged question's id, text, answer and episode, which is enough to fix or cut items in the batch files and re-merge.
