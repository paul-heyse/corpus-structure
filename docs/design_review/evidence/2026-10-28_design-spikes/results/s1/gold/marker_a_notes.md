# Marker A notes

Marker A annotated all 85 blocks (134 sentences) by reading only `worksheet.md`. No NLP tool or
sentence splitter was used. A small script took the hand-chosen sentence starts and checked that
every sentence is an exact substring and that only whitespace between sentences was dropped.

## Uncertain blocks

| Block | Choice | Why unsure |
|---|---|---|
| B020 | 3 sentences; the last is `But \[X = … W^\sigma\]` with no final period | The block ends inside a derivation, so the sentence is probably finished in the next block. Rule 3 still gives a sentence that ends at the display. |
| B032 | 2 sentences; the second ends with a display and no period | Same as B020: the trailing display may be followed by text in the source. |
| B060 | Split after the display (`… k \in (0, \infty) \]`) before `The function is well defined` | Rule 3 applies: a capitalized independent clause follows a display that has no period. One could argue the display and the next clause run on. |
| B072 | 2 sentences; the second is the bare formula `\(\P(Y - X \lt 0) = 0.0028\)` | This is an answer line that consists only of math, after a period. It could be read as part of a single "solution" unit, but it follows a sentence-final period and stands alone, so it is a separate fragment sentence. |
| B004, B065, B070, B082 | 1 sentence each; the text after the display continues lowercase (`so …`, `which …`, `and hence …`) | Rule 3: these continue the same sentence. B082 has no final period. |
| B081 | 1 sentence: `(a) From [3], \[ … = k\]` | A list item whose whole body is a display. It is one fragment sentence. |
| B073 | Sentence 1 ends at `of course).` | The period comes after the closing parenthesis, which closes a parenthetical inside the sentence. That makes it a sentence end, not an abbreviation. The second `Of course,` starts a new sentence. |
| B041 | Split before `Parts (b) and (c)` | `(b)` here is a cross-reference inside the sentence, not a list marker. |
| B048 | Split before `Note that`; `(which gives (b))` and `(which gives (c))` stay inside their sentence | Parenthetical cross-references to list items. They are not markers. |
| B057, B009, B037, B058, B067, B080 | Last sentence ends with a colon, `are`, `then` or `with`, with no period | These are lead-ins to a following list or display (rule 5: a colon does not end a sentence). Each is kept as one sentence that runs to the end of the block. |
