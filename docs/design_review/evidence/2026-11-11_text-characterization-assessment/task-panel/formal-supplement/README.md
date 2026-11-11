# Source-only formal nomination supplement

Prepared and frozen on 2026-11-11: **reference set 43**, units **105** (SourceView 477, original question 23 occurrence) and **106** (SourceView 481, original question 24 occurrence). This uses the same authentic source capture 496/cut 614, project `nce-grinstead-snell-full-book`, archived release `c9939039081ddcfbc382e9dc323e12e31f9b3683fb479c773ea3fd72ac6a6189`, guideline `characterization-reference-2` and rubric `chapter-facet-task-semantics-1`.

Earlier sets 40/41 retain their original questions, source opportunities and prior passes. Their Q23/Q24 family contracts are mismatched and remain unassessed; this supplement does not silently override a case's required family. The public `formal_evidence.nominate_fields` contract nominates an ordinary labeled `Identifier:` field for `formal.identifier`, and labeled `Range` or literal numeric bracket intervals for `formal.interval`. A formula-labeled item is examined by `formal.math`; a written inequality is not an inferred interval object.

The new source-only questions preserve **exactly the original ordered real extents**, formula labels and source text:

| Unit | SourceView | Original occurrence | Revised question |
|---|---|---|---|
| 105 | 477 | `#/texts/21747`, projection offsets 114–122 | Independently determine symbol/variable normalized identity under public `symbol-occurrence-v1` / `tex.token_form`; scalar `formal.normalized` may express the independently authored expectation. |
| 106 | 481 | `#/texts/14243`, projection offsets 3461–3471 | Independently determine written comparison operators and directed ordered operands under task `formal`, role scheme `formal-children-v1`. |

Both require `formal.math`. Neither question supplies a normalized string, operator value or expected AST. The comparison question does not request algebraic solving, an equivalent rewrite, scientific meaning or an interval. The source states freeze as `uninspected`; fresh authors independently choose honest witness/complete-slot scope and preserve unresolved or inapplicable source. Actual semantic assertions, identity values and graph decomposition are not authored by selection.

Original source/hierarchy context is delivered in `source-view-477.json` and `source-view-481.json`, with exact original coordinate bindings from the immutable source-first selection. The protected native create guard reauthenticates those bindings. No producer product, candidate parse, reference pass or another author's answer was read. No normalization, parsing or NLP operation was run. According to the coordinator's execution boundary, chapter SourceViews were still unproduced when these corrected source frames were frozen.

Reproduction:

```sh
uv run python docs/design_review/evidence/2026-11-11_text-characterization-assessment/task-panel/formal-supplement/prepare_supplement.py prepare
uv run ci golden operation-create --from-run 496 --source-cut 614 \
  --label tc10-source-formal-supplement-1 --split dev \
  --guideline characterization-reference-2 \
  --guideline-text domains/statistics/characterization-task-reference-guideline.md \
  --partition development \
  --sample docs/design_review/evidence/2026-11-11_text-characterization-assessment/task-panel/formal-supplement/sample.json \
  --project nce-grinstead-snell-full-book --json
uv run python docs/design_review/evidence/2026-11-11_text-characterization-assessment/task-panel/formal-supplement/prepare_supplement.py packets
```

Protected creation **passed, 2026-11-11**. Its exact receipt is [frozen-reference-set.json](frozen-reference-set.json). Source health remains inherited: display partial, inline/cell unknown. The two purposive source questions establish no book-wide semantic accuracy or complete formula recognition claim.

Protected source-only packet delivery **passed, 2026-11-11**: [author-unit-105.json](author-unit-105.json) and [author-unit-106.json](author-unit-106.json), indexed in [author-packets.json](author-packets.json), 155,618 bytes total. The source-only attestation **passed**: original Q23/Q24 extents are byte-equivalent, actual native-receipt frames equal submitted frames, receipt manifest SHA-256 matches, both opportunities remain uninspected, source-only output bindings are null/empty and packets expose no selected outputs. `uv run python -m py_compile .../prepare_supplement.py` **passed**.
