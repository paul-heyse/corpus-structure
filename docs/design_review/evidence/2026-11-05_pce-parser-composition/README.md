# Bounded parser composition execution

**Implemented and bounded Tested, 2026-11-05.** The PCE coordinator owns package
state. These results establish selected parser contracts, not PCE-07 completion,
corpus completeness or improved extraction quality.

## Source trace and implementation

The foundation's retained population has 25 definition attachments and no table
relations. Its supported cell literals do not establish row/header/unit/note
attachments. Current `native_table_groups` can consume explicit native paths;
neither absent returned fields nor nearby prose proves that such paths or semantic
relationships were established. Fresh source execution and independent same-case
assessment remain necessary before claiming those gaps closed.

The existing GLiNER worker already supports native entity, attribute and relation
schemas. `native-local-v1` admits those questions without record structures. Its
new adapter retains decoded occurrences, mention-conditioned attribute proposals
and directed native relations. Reconciliation uses exact endpoint extents, never
equal text or list order; unsupported/missing endpoint coordinates remain unresolved.
M1 candidate version7 consumes optional `local_schema` through that same worker and
retains raw local reports separately from whole-record reports.

Retained linguistic columns reconstruct a consumer-local Doc without tokenization
or language-model execution. Whitespace/offsets, absolute block-token heads,
annotation values and derived sentence extents must agree with retained ownership.
Prepared token/phrase/dependency matchers preserve overlaps and ordered nodes.
Optional M1 `annotation_token_rules` uses the existing resident linguistic vocabulary
(a bare spaCy Vocab does not provide the required LOWER lexeme attribute).

Optional M1 `formula_syntax` defaults to the strict `recognized_only` input policy;
unavailable recognition yields `not_run`. Explicit `formula_syntax_input_policy:
captured_native_text` permits a separate private syntax question over captured text
while retaining actual recognition health. Its operation version2 and dependencies
bind input policy, health and the assembled grammar profile. AST offsets index the
declared captured string, while source anchors remain at native-item precision.
Interpretation, original glyph mapping and scientific truth are not inferred.
Trimmed readings retain their original failure/tail. Failed parse attempts emit no
products; a separate diagnostic-retention operation preserves the failure without
erasing earlier useful contributions or claiming parse success.

## Actual selected provider contract

`uv run python docs/design_review/evidence/2026-11-05_pce-parser-composition/native_local.py`
**passed** with the existing pinned CPU FP32 GLiNER checkpoint. The script and raw
stdout/stderr/report are retained. The single controlled input produced two
distribution spans with role attributes. Its requested `alias_of` relation channel
completed empty. This is actual provider execution on one controlled text, not a
positive relationship result or corpus-quality assessment.

## Functional checks

`uv run pytest python/corpus-structure/tests/ingest/test_annotations.py python/corpus-structure/tests/methods/test_contribution_adapter.py python/corpus-structure/tests/methods/test_m1_producer.py python/corpus-structure/tests/methods/test_m1_record_frontends.py python/corpus-structure/tests/methods/test_gliner.py -q`
**passed** (107 selected tests), captured in `raw/parser-focused-005.log`.
Independent controls cover restored coordinates/heads, overlap, directed repeated
endpoints, missing endpoints, private native binding, whole/trimmed/failed syntax
and recognition/source mismatch. The integrated source-consumer control restores
real retained linguistic columns, emits a LOWER-based cue and controlled local
decoder products while complete record output is empty. Earlier failed runs001/003
and the successful002/004
remain; tokenizer token-boundary and decimal-punctuation fixture mistakes were
corrected without weakening the production contract.

The earlier 62-test check passed before new controls. This is not an additive
qualification count. Final source/context applicability and typing/lint are owned
by the coordinator's integrated receipts. Run005 covers the production vocabulary
fix; its controlled decoder establishes no additional provider result.

## Still open

Run the opt-in capabilities against selected retained corpus sources under the new
runtime/native head, then author or reuse applicable exact-question references
and compare source/output populations separately. Table attachments, prose symbol
roles, explicit cue-state capture and downstream benefit remain open until those
actual results exist. No JointIE, supplied-span, forest or training branch was
triggered by these bounded results.

## Explicit bounded producer selection

**Implemented and bounded Tested, 2026-11-05.** Optional
`M1Config.source_projection_digest` selects exactly one eligible view using retained
view metadata, refusing missing or ambiguous matches without hydrating other views.
Optional `region_pointers` is a strict nonempty per-view native selection. Unknown
pointers refuse before annotation restoration or native model work. Context preparation
builds only requested primary selections before widening, while preserving actual
bounded related context. Other region inventory rows remain `not_requested`; their
coverage is `unknown`/unanalysed, never inspected absence. Retained annotation rules
are restricted to selected primary ranges. Existing `None` defaults preserve broad
selection; this does not alter the separate upstream annotation producer's scope.

`uv run pytest python/corpus-structure/tests/methods/test_m1_producer.py python/corpus-structure/tests/methods/test_m1_source_preparation.py python/corpus-structure/tests/methods/test_m1_record_frontends.py -q`
**passed** (59 selected tests), retained in `raw/bounded-regions-002.log`.
Run001 retains a stale exact-registry expectation that omitted the newly registered
CPU contextual retriever. Its expected set was updated to include that authorized
method while preserving exact membership and no-agent/no-general-LLM assertions.
The region control uses real retained linguistic columns and a controlled GLiNER
decoder; it proves selection behavior, not extraction quality.

## Captured syntax and failure grain

`uv run pytest python/corpus-structure/tests/methods/test_contribution_adapter.py python/corpus-structure/tests/methods/test_m1_producer.py python/corpus-structure/tests/semantic/test_selected_source.py -q`
**passed** (54 selected tests), captured in `raw/captured-syntax-003.log`.
Unknown/failed/not-requested recognition can yield useful private captured-string
syntax without upgrading recognition, interpretation or PDF glyph fidelity.
The strict recognized frontend still refuses those same inputs. Actual production
`bind_contributions` and `bind_result` validate a failed zero-output parse plus its
separate retained diagnostic beside earlier useful products.

The coordinate control checks raw leading whitespace and a trimmed punctuation
suffix, independently requiring each token extent to reconstruct the original
captured input. Code inspection confirms `grammar.syntax` parses the raw string;
its only recovery removes a trailing suffix, leaving an unchanged input prefix.
The report records input digest, parsed prefix length, actual health and grammar
profile, while item-level evidence retains unestablished original-glyph mapping.
Run001 retains an unsupported Lark Token serialization failure. Rule names now
normalize to plain strings at the strict JSON scalar boundary. Run002 precedes
the strengthened failed-operation/diagnostic-grain controls and is not the final
scope receipt. Scoped Pyrefly and Ruff subsequently passed.
