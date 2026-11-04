# M1 source boundary representability and formula neighborhood preparation

Verified2026-11-04. Overall outcome **partial**: bounded source preparation/mapping is
settled, while faithful target grouping, actual capture and quality remain separate.
Standing: **Tested** representability inquiry. Its selected codepoint/context mechanisms
subsequently enter the opt-in contextual profile; the
[coordinator](../../../plans/first-production-milestone_2026-11-03.md) owns implementation and
the [separate native calls](../2026-11-04_m1-contextual-profile/README.md) establish only
bounded execution. This inquiry itself establishes no model efficacy or quality.

This inquiry compares the same148 stored source contexts and protected feature-fit
C23/24 targets under a native callable Unicode-codepoint splitter, preserving
original text and offsets. It also investigates source-only whole-block expansion
around native formula occurrences within2048 characters and64 pieces. Gold does
not select context membership. No model, forward call, inference, training,
database write, held-out access, PDF/OCR or product edit is authorized here.

Exact source/word/source mapping, native schema-conditioned subword budgets,
checkpoint4096 versus existing facade512-word/2048-subword bounds, and any native
span/candidate limits will remain distinct. The finalized alignment and numerical
feasibility folders are inputs and will not be changed.

## Result

The source-only alternatives materially raise the geometric mapping ceiling, but
the codepoint splitter is not usable within the unchanged facade admission bounds.
The same148 contexts reproduced their frozen context digests and text exactly.
Protected C23/24 remains the sole label source:270 records in source23, and explicit
zero-record source22. No other reference sets, author folders or predictions were
read. The frozen released packs, choices, states and cues were retained.

| Context policy and splitter | Source roles exact | Baseline-comparable complete mappings | With old512-word/2048-subword facade |
| --- | ---: | ---: | ---: |
| Original148, whitespace | 145/270 | 143/270 | 143/270 |
| Original148, codepoints | 190/270 | 184/270 | 127/270 |
| Expanded49 formula contexts, whitespace | 43/88 | 43/88 | 43/88 |
| Expanded49 formula contexts, codepoints | 73/88 | 73/88 | 3/88 |
| Additional4096/128 formula contexts, codepoints | 83/88 | 83/88 | 0/88 |

“Baseline-comparable” applies the previous alignment's complete literal/cue mapping
and classified-ABSENT representability criteria. It does **not** mean these new
alternatives have been emitted as training examples or passed native gold collation.
The six codepoint-mappable records with a nonpresent classified field remain a
separate native target-conditioning question owned by another worker.

The source-generated union of original plus expanded contexts represents177/270
baseline-comparable records with whitespace and236/270 with codepoints. The formula
expansion loses no original formula mappings. With the stronger requirement that a
gold formula record match the context's actual primary native formula, the combined
ceilings are169 and224 respectively. Formula-only ceilings under that requirement
are8 original whitespace,16 original codepoints,35 expanded whitespace and61
expanded codepoints. Mere co-presence of another formula and its wording does not
establish attachment. Even the primary-match counts establish source availability,
not learned meaning association.

The codepoint alternative removes all observed best-diagnostic word-boundary
mismatches:64 distinct original records had that cause (121 role occurrences across
their selected diagnostics), versus zero under codepoints. On unchanged contexts,
the remaining source-exact exclusions include77 records with a gold piece outside
the bounded context,2 with extra real text inside the scalar bounding span, and1
with gold/source piece order differing; causes can overlap. After formula expansion
and codepoints,15 formula records still lack a required gold piece in any bounded
candidate context. None of these exclusions becomes a negative.

See [attempt-001/summary.json](attempt-001/summary.json),
[attempt-001/analysis.json](attempt-001/analysis.json), and the full
[record mapping](attempt-001/record-mapping.jsonl). Every record retains its exact
source ID, role failures, complete candidate context indices and primary-formula
qualification. [Mapping attempts](attempt-001/mapping-attempts.jsonl) retain genuine
source pieces, synthetic whitespace gaps and source→token→source round trips.

## Native callable and budgets

`UnicodeCodepoints.__call__(text, lower=True)` in [probe.py](probe.py) yields one
token for each non-whitespace Python-string Unicode codepoint with `(i,i+1)` original
offsets. It is a native callable splitter, not the built-in `CharLevelSplitter`,
which retains welded Latin runs. The source string is never normalized or edited.
Lowercasing affects token values only, as with the native whitespace splitter;
combining marks remain individual original codepoints. Native character→word and
word→character conversion plus production `NativeSourceContext.read_span` enforce
exact genuine-piece identity. A scalar span cannot silently acquire extra real text.

| Source-generated requests | Max source word tokens | Max total subwords | Requests exceeding old word bound | Requests exceeding old subword bound |
| --- | ---: | ---: | ---: | ---: |
| Original whitespace,294 family requests | 401 | 1636 | 0 | 0 |
| Original codepoints,294 | 1610 | 2827 | 49 | 9 |
| Expanded formula whitespace,49 | 493 | 1171 | 0 | 0 |
| Expanded formula codepoints,49 | 1726 | 2350 | 48 | 26 |

For original codepoints these failures concern25 distinct contexts at the word
bound and4 at the subword bound; a prose context can produce three family requests.
No prepared input exceeds the checkpoint's4096 **source-word-token** `max_len`.
The observed combined envelope needs1726 source tokens and2827 total subwords,
including schema/choice prefix. Those figures are preparation observations, not
universal bounds or a qualified safe runtime profile. Native multi-record training
choice-prefix expansion can add further tokens and is not requalified here.

The installed processor documents `max_len` as source-word truncation before
prefix/schema encoding, so4096 is not a checkpoint subword cap. The encoder config
contains `max_position_embeddings=512` with `position_biased_input=False`; installed
DeBERTa creates no learned position embedding in that mode. Its tokenizer has an
unbounded sentinel limit. These source facts do not qualify arbitrarily long
encoder execution. [Native budgets](attempt-001/native-budgets.jsonl) retain each
actual schema-conditioned preparation, source/prefix token counts and old-facade
admission decisions. No truncation was used to obtain a mapping pass.

Boundary architecture has half-open start/end pairs and no dense fixed-width span
axis (`models/boundary/model.py`), unlike span-era `max_width` examples. The largest
successfully mapped role widths observed here were50 whitespace tokens and200
codepoint tokens on original contexts, and50/116 on expanded contexts. Exact legal
endpoints do not establish proposal discovery or useful span scores. The unchanged
checkpoint still has start/end top-k24, pool-boundary top-k32, shared pool192,
candidate/training budgets192 and max-gold-per-query64; record query count32 concerns
the native latent/anchorless mechanism, not a new natural-mode record allowance.
Finer segmentation increases positions competing for those budgets and changes
the checkpoint's learned input distribution. No head capacity or weight was changed,
and no candidate-recall, memory, time, finite-loss or efficacy claim follows here.
Multiple C formula records can also share one formula occurrence; natural-anchor
instance identity and scalar field assignment are not established by these geometric
mapping ceilings. Native target collation/grouping remains separately owned.

## Source-only formula neighborhood

The alternative is generated **before** reading gold for mapping. The49 actual
native formula selections identify the primary formula pointer. Persisted source
annotations supply complete native paragraph/list/caption blocks and their original
piece extents. The smallest complete block containing the actual formula starts
the context. The algorithm then alternates the nearest preceding and following
whole blocks; it stops a direction when its nearest remaining block cannot fit.
It never skips an oversized neighbor to reach semantically convenient wording.

Each complete block is an unchanged `SourceSlice`; deterministic newline gaps
between blocks are model-only synthetic whitespace. Production context construction
enforces2048 characters and64 actual intervals. All49 contexts prepared; the largest
had2048 characters,64 intervals and18 whole blocks. Ninety-four directional additions
were refused by character/interval bounds and remain explicit. The neighborhood is
within the same selected source view and native document order; it makes no claim
that a neighboring paragraph defines a symbol or supplies a missing assumption.
It is a wider candidate context, not semantic scope acceptance.

[Formula expansion receipts](attempt-001/formula-expansion.jsonl) identify primary
formula pointers, all included whole-block IDs/extents/digests and every stopped
direction. [Expanded contexts](attempt-001/expanded-contexts.jsonl) retain exact text
and piece maps. Wider context plus codepoints makes many more complete protected
readings available, but model interpretation and cross-record attachment remain
unresolved until separately assessed.

## Commands and evidence limits

- **passed**: `uv run python docs/design_review/evidence/2026-11-04_m1-source-boundary-fit/probe.py`
  — [attempt-probe-001.log](attempt-probe-001.log); exact148-context reconstruction,
  source-only49-context generation,686 native tokenizer/schema preparations and
  complete source/word/source mapping comparisons.
- **passed**: `uv run python docs/design_review/evidence/2026-11-04_m1-source-boundary-fit/analyze.py`
  — [attempt-analysis-001.log](attempt-analysis-001.log); distinct causes, budget
  filters and primary-formula/source-generated union ceilings.
- Model loading/forward, inference, training, new native gold collation, grading,
  held-out access, DB writes, product changes and adoption: **not_run**.

The source reader used run14/cut13 views22/23 and the unchanged frozen release
`release:bc69d3be658e27e079ae61d4c4fa2051eabf006326b80443f2d28a9e8662b5bd`.
Stored annotations were consumed; no annotation recomputation/PDF/OCR occurred.
Exact local checkpoint artifacts were verified and only its tokenizer loaded,
offline with CPU4/parent1/interop1. Context7 first confirmed callable splitter
offsets and runtime-only splitter selection; installed2.1.0 processor/configuration,
boundary and splitter sources control consequential details. Runtime selection must
explicitly restore any custom splitter after checkpoint reload.

[Input receipts](attempt-001/input-receipts.json) freeze the protected response,
original contexts/configuration, checkpoint config and executed probe hash. Executed
probe/analysis bytes are retained as `.py.txt` snapshots, so later root formatting
does not rewrite the executed source. Root owns final maintenance, integration and
any change to profile bounds or candidate policy.

## Additional immutable4096/128 scenario

At the coordinator's request, the same source-only whole-block expansion was run
once more under4096 characters/128 intervals, with codepoint segmentation only for
the expanded contexts. The original2048/64 artifacts remain unchanged. All49 larger
contexts prepared. Formula co-presence mappings rise73→83/88, while the stronger
actual-primary count rises61→75/88, gaining14 primary-bound records and losing zero.
The corresponding all-family source-generated union is246 co-present or238 requiring
the actual primary formula. **75/88 actual-primary availability remains incomplete**;
the83/88 co-presence figure cannot replace it or waive any quality requirement.

The largest prepared context has4084 characters,128 intervals and27 whole blocks.
Observed expanded maxima are3427 source tokens,57 choice-prefix tokens,3484 model
word tokens and4049 total schema-conditioned subwords. No source input exceeds the
checkpoint's4096 source-word cap. Every larger expanded context exceeds the old512
word bound;45/49 also exceed2048 subwords. The unchanged facade admits zero complete
formula records from this scenario. The larger profile is therefore an explicit
alternative needing real forward/resource qualification, not a drop-in splitter
change or evidence that4096 subwords is generally safe.

This is a material geometric gain for a larger input envelope; its runtime burden
and model benefit are unmeasured. No8192 variant or further model/native probe was
run. Per-request source/prefix/model-word/subword counts and primary qualifications
remain in [attempt-002/analysis.json](attempt-002/analysis.json) and
[attempt-002/native-budgets.jsonl](attempt-002/native-budgets.jsonl).

The remaining five co-presence failures were classified using existing artifacts
only. **All five are context co-location failures; zero are solely the current
scalar-contiguous-span restriction.** Every required quote is confirmed in the
frozen source23 projection and is available in at least one generated context, but
no single generated4096/128 context contains the complete required combination.
They are not source-document absence claims. In contexts containing the formula
and symbol, the missing role is `meaning`:

- Two records require `#/texts/356`: “the number of trials up to and including the
  first success”, in a different generated window from the formula occurrence.
- One requires the located meaning pieces at `#/texts/313`–314 (`=1-`, `p`), which
  do not co-occur with its complete formula/symbol targets in one generated window.
- Two require `#/texts/275`: “first term p” or “common\nratio q”, outside their
  formula/symbol-containing windows.

The actual-primary remainder is13 records: nine lack the required meaning within
any complete primary-matching candidate; four gold formula pointers have no actual
native primary-formula selection among the49 source-generated formula selections.
Eight of these13 records are complete only in another formula's context. The first
diagnostic's limited co-presence count is superseded by the comprehensive
[source-gap classification](attempt-002/source-gap-classification/summary.json),
[five-record receipts](attempt-002/source-gap-classification/remaining-five.jsonl)
and [primary remainder](attempt-002/source-gap-classification/remaining-thirteen-primary.jsonl).

Context7 was queried before inspecting the installed `RecordFieldTarget` and
cardinality implementation. Native `values` distinguishes distinct gold values
from alternative occurrences of one scalar value: `ZERO_OR_MORE`/`ONE_OR_MORE`
construct one distinct span value per mention, while scalar values group spans as
occurrence alternatives. A future explicit piece-list pack and ordered TextSequence
assembly policy could preserve disjoint genuine quotes without invented joins or
normalization. It does not make missing co-located inputs available, so it alone
cannot close these five failures. No new list policy was adopted or collated here.

Additional commands, all **passed**:

```sh
uv run python docs/design_review/evidence/2026-11-04_m1-source-boundary-fit/probe.py --output attempt-002 --expanded-chars 4096 --expanded-pieces 128 --expanded-codepoints-only
uv run python docs/design_review/evidence/2026-11-04_m1-source-boundary-fit/analyze.py --output attempt-002
uv run python docs/design_review/evidence/2026-11-04_m1-source-boundary-fit/remaining_primary.py
uv run python docs/design_review/evidence/2026-11-04_m1-source-boundary-fit/classify_source_gaps.py
```

The latter two commands read retained artifacts only. Their executed bytes remain
beside their results; no new context, model, target-policy or inference run occurred.

## Records

<!-- evidence-index:start -->
Generated by `just evidence index` from `records/`; do not edit by hand. 1 current, 0 superseded.


**M1**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Source-available exact boundaries and coherent formula neighborhood alternatives](records/m1.source-boundary-fit.json) | M1-05 | partial | — | 2026-11-04 |
<!-- evidence-index:end -->
