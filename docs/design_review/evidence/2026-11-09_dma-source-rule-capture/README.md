# Exact source-rule candidate capture for DMA-13

**Tested · 2026-11-09.** The [bounded read-only replay](replay.py) used the retained Standard and
Nemotron source product in run 407/cut 517 and run 437/cut 537. No recognition, reference read,
resolver, fitting, evaluation write, or run selection occurred. The registered `/10` configuration
and ordinary M1 route were preserved. The diagnostic uses the same native CPU GLiNER baseline
inside an explicit region selection and augments only its private candidates.

The [two authored constructions](capture-rules.yaml) use the existing spaCy dependency matcher
on retained annotation columns and the existing released record field and classification contracts.
One construction requires a finite clause with a direct nominal content expression and its exact
`about` complement. It preserves that complement's restrictive clause. The other requires an
explicit `up to` count with the number and counted unit under the same governing activity as the
`for` referent. Partial, negated, cross-sentence, synthetic, or non-primary evidence cannot supply
one of these constructions. The record assembler leaves unsupported roles unresolved. The
separate capture request digest binds the selected regions, source and rule parameters.

| Authenticated source | Bounded outcome |
| --- | --- |
| Preface view 381 | Captured both candidate cores missed by the original decoder: `Probability theory` / `makes predictions about` / `experiments whose outcomes depend upon chance`, and `experiments` / `trials` / `1000`, with `up to` and the explicitly cued `bound` classification. Unobserved qualifications remain unresolved. |
| Heading view 382 | No new source-rule candidate. The incumbent decoder's unsupported private heading definition remains observable; the new arm does not convert it to an eligible reading or hide it. |
| Subsection view 409 | No added rule candidate or assembled record. The original annotation merges the naming prose and the following condition, attaching the condition to `think` rather than the subsequent `get`. Both native displays remain retained and the candidate arm does not invent a symbol or its meaning. |

An alternate-vocabulary business assertion passed the same capture and assembly path. Negative
controls include a negated counterpart, different-sentence content, and heading-like text.
An initial replay invocation refused because the script resolved the pack root one directory too
shallow; the corrected invocation and its observed result are kept separately.

These results isolate a recoverable source capture gap. They do not qualify full Preface records,
repair the subsection's definition and formula readings, or make either historical predecessor
eligible. Do not fit on these exposed development controls.

## Subsection condition and formula limits

**Tested · 2026-11-09.** The [locked HanLP CPU replay](replay_hanlp.py) compared the exact
retained sentence block at view 409 `[193,399)` with a separate diagnostic split at existing
punctuation. It authenticated the same completed source cut and pinned two distinct effective
inputs. Both native outputs locate the whole `if we differentiate g(t) n times and then set
t = 0` condition at `[336,387)` and the sole candidate host `get` at `[392,395)` in
`#/texts/21407`. The direct arguments belong to the consequent: `we` at `[389,391)` and `μn`
at `[396,398)`. The unchanged layout already suffices for this scoped HanLP result.

The [assembly readback](raw/hanlp-assembly.json) authenticates each retained input and reuses
the typed condition cue, predicate frame and record assembler to produce a private assertion.
It refuses competing host choices and substituted source maps. Polarity, modality and other
unproved roles remain unresolved. A production successor needs an exact retained provider
dependency in the native task graph and a fresh independent grade. This read-only candidate
does not supply a public condition assertion or a fitted record policy.

The [exact formula boundary check](raw/formula-boundary.json) confirms that both original
displays have unknown recognition health. The ordinary recognized-only syntax route was
`not_run`; forcing the original captured strings into the diagnostic syntax path failed at
native unexpected characters and retained `math.syntax_failure`. No SymPy assessment or
symbol binding ran. Preserve the displayed text and its anchors and carry the named
declaration and formula-binding gap forward without reconstructing flattened notation.

## Reproduction

```sh
uv run python docs/design_review/evidence/2026-11-09_dma-source-rule-capture/replay.py
uv run python docs/design_review/evidence/2026-11-09_dma-source-rule-capture/replay_hanlp.py
uv run python docs/design_review/evidence/2026-11-09_dma-source-rule-capture/replay_hanlp.py --assemble-retained
uv run python docs/design_review/evidence/2026-11-09_dma-source-rule-capture/formula_probe.py
uv run ci test --json -- python/corpus-structure/tests/methods/test_m1_source_capture.py python/corpus-structure/tests/methods/test_m1_producer.py python/corpus-structure/tests/methods/test_m1_assertion_qualification.py
```

## Records

<!-- evidence-index:start -->
Generated by `just evidence index` from `records/`; do not edit by hand. 2 current, 0 superseded.


**dma-predecessor**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Bounded source-rule candidate capture on the retained predecessor](records/dma.exact-source-rule-capture.json) | DMA-13 | partial | DMA-13 | 2026-11-09 |
| [Exact HanLP subsection condition capture and native formula limits](records/dma.subsection-condition-and-formula.json) | DMA-13 | partial | DMA-13 | 2026-11-09 |
<!-- evidence-index:end -->
