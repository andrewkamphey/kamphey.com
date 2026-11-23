# Pick One cleaning spec (input for batch workers)

Read batches/batch-NN.txt (sections start with "##### Title | date"; lines without a
speaker prefix are Josh). Regex hints per episode: batches/batch-episodes.json
(`regex_hints`, where batch == NN). Write clean/batch-NN.json:

{"items": [ {"episode", "date", "orig", "prompt", "answer", "choices": [w1, w2],
             "explain"?, "needsReview"?} ],
 "dropped": [ {"episode", "q": <regex hint text, verbatim>, "why": <code>} ]}

- `orig`: Josh's original question text (verbatim, incl. options he offered). Used to
  match regex rows for stats; stripped from final output.
- `episode` exactly as in the "#####" header; `date` from the header.
- prompt: Josh's wording, minus "And/So/Okay/Alright/Here's another one" lead-ins and
  minus giveaway hints ("it has lung in the name"). Replace pronouns that need context
  ("What gas do they get" -> "What gas do fish get"). Simplify only if a 5-year-old
  could not follow it.
- answer: 1 to 4 words ideally, button-sized, never Josh's full sentence. Capitalize first
  letter. Articles ok ("The root").
- choices: exactly 2 WRONG answers, same type/length/grammar as answer, clearly wrong to
  an adult, plausible to a 4-7 year old, not silly ("ice cream" only if Josh offered it).
  If Josh offered options, use his wrong ones (fill to 2 if he gave only 1).
- explain: optional, one short sentence from Josh's answer line, his words, no em dashes.
- needsReview: true when garbled/unsure, rather than guessing. Still fill all fields.

Include: quiz recall questions, "which of these" questions, standalone questions inside
other games, Captain Curious puzzle questions that stand alone (e.g. "How many letters
are in the word red?").
Skip (do not output): True/false, What am I? / riddles / "guess the sound" / "name that
thing" / guess-from-clues, Would you rather, More or less and two-way comparisons
("which is hotter, X or Y", "bigger or smaller", "faster or slower", "does it float or
fall", "is it nocturnal" sorting games), yes/no questions, open-ended questions, trick
questions, questions needing the audio or story context, questions whose answer is
missing/wrong in the transcript, ad reads, birthdays, Curious Kids Club submissions.
Within an episode, don't output two items testing the same fact.

`dropped` lists EVERY regex hint for the batch's episodes that you did not turn into
an item. why codes: fragment (not a real question: hint, option list piece, "Are you
ready?", "Remember...?"), other-category, yes-no, open-ended, audio-context, no-answer,
duplicate, trick, too-hard-to-shorten. A regex hint that you DID use needs no entry.
No em dashes anywhere.
