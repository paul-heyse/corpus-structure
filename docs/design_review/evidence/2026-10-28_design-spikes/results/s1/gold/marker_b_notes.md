# Marker B notes

Independent annotation of the 85 worksheet blocks, done by reading only (no sentence splitter).
134 sentences total. The boundaries were chosen by hand. A small stdlib script only cut each block
at the hand-picked sentence starts and checked that each segment is an exact substring and that
together they cover the block with only whitespace dropped.

## Uncertain or judgment-call blocks

- **B060**: a display formula is followed directly by "The function is well defined…" with no
  period. Under rule 3 I split after `\]`, so sentence 1 ends with the display. A reader could
  also treat the display as running on into the next clause, but the capitalized "The" starts
  an independent clause.
- **B072**: "…the radius of the hole." is followed by a bare formula `\(\P(Y - X \lt 0) = 0.0028\)`
  that has no verb and no period (it's an answer). I marked it as its own sentence. The other
  reading attaches it to the first sentence, but the period after "hole" is a clear terminal.
- **B020**: the last sentence "But \[X = … \]" ends in display math with no final period. It
  stays one sentence, ending at the block end.
- **B004, B065, B070, B082**: a display is followed by a lowercase continuation ("so the
  result…", "which we recognize…", "and hence…"). Each is one sentence, because the display
  continues the grammatical sentence (rule 3). I'm fairly confident about these.
- **B018, B025, B032 (2nd), B039, B046, B053, B081, B085**: the block ends in display math with
  no terminal period. Each final sentence runs to the block end.
- **B073**: sentence 1 ends with "(… of course)." The period after the closing parenthesis is
  terminal. The "[14]", "[17]", "[23]", "[24]" and "[26]" references are mid-sentence.
- **B048**: the parentheticals "(which gives (b))" and "(which gives (c))." are inside the
  sentence. The final period after the parenthesis ends sentence 2.
- **B030**: the semicolon in "…still normal; the expressions…" does not split, so this is 3
  sentences, not 4.
- **B009, B037, B058, B067 (2nd), B080, B057 (2nd)**: these sentences end without terminal
  punctuation ("are", "then", "given by", "with", and a colon). The sentence carries on in the
  next block or display, which is outside the block. Within the block each is one unterminated
  sentence. A cross-block gold standard would join them with the following block.
- **B002**: "Let \(X\) denote the volume of beer in liters" has no period (it's an exercise
  stem). One sentence.
- **B001, B019, B036**: headings or captions, not sentences. Each is one segment.
- **B003, B005, B012, B017, B024, B045, B052, B068, B069, B031**: list items that are only
  formula fragments, or end without a period. Each is one sentence that includes its marker
  (rule 4).
- **B061**: "So \( \Omega \) …" follows a period and starts a new sentence (rule 3's "So" case
  in running text).

Count of blocks I would call genuinely uncertain (a second reading is defensible): 3 (B060, B072,
B020). The rest above are rule applications recorded for traceability.
