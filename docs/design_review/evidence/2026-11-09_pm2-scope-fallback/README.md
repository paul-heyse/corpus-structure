# Native parser scope fallback on the admitted PM2 release

This bounded operating diagnostic exercises the existing `ci run parsers` fallback for
Maverick (PM2-04) and Dipo (PM2-05). It uses one authenticated Standard/Nemotron source
projection from run 407/cut 517, source view 383, without recognition, Chandra, release
activation, or run selection. All outputs are private. The project remains unselected.

The runs use admitted release
`release:ca0d3cbe0eb56ce659afada0f4b1692624558622ebf61bfdd9a93b44aa11354f` and the
development target `corpus_structure_dev` (OID 25921445; system identifier
`7701811359771751232`; port 5434). The maintenance revision at run time was
`semantic_pm2_definition_chain`. A private active realization was created for the release;
the parser commands then created ordinary private runs. Neither action selected a result or
activated a release.

## Older release refusal retained

Before the new admitted release was available, the same authenticated source view was opened
read-only under `release:0fea02616c97367ad658fefee131b01855c8c20a4e9bd40b3e97c1b0c4e0aca3`.
Structural source authentication succeeded, but analytical source-layout preparation refused
with `PreparationError: unsupported_analysis_implementation` and the message that the admitted
semantic determinant bytes must be bound to the runtime before analysis. The refusal is preserved
in `raw/prior-release-refusal.json`; archive validation was not relaxed. The newly admitted
`ca0d3c…1354f` release prepared the exact source successfully.

## Source and boundary preparation

`prepare.py` reopens the existing parser request pin for view 383, validates it through
`ops.validate_structural_source`, loads the retained source under the admitted release, and
uses the production PM2 `_sentences` and `_partition` functions to construct the expected
sentence-coherent extents. The initial parents and children were:

| Provider | Parent extent | Parent sentences | Coherent child extents |
| --- | --- | ---: | --- |
| Maverick | `[811,4564)` | 28 | `[811,2742)`, `[2742,4564)` |
| Dipo initial | `[811,15015)` | 130 | `[811,7866)`, `[7866,15015)` |
| Dipo reduced | `[811,10578)` | 90 | `[811,5688)`, `[5688,10578)` |

The ranges are half-open projection offsets. Each child retains its parent input digest. The
PM2 source-context owner labels child contexts as coherent splits and marks relationships
crossing those boundaries unexamined. The recorded rows therefore show examined local work;
they do not imply coverage of cross-child links.

## Native outcomes

**Maverick · run 446/cut 549.** The 28-sentence parent, task 2154, returned `limited` with
reason `post_tokenizer_tokens`, and inspected/emitted counts of 0/0. Both children completed:
task 2155 emitted 54 mentions and task 2156 emitted 38. The isolated DeBERTa tokenizer preflight
estimated 897 parent tokens and 443/456 child tokens; the native task outcome is authoritative.

**Dipo initial scope · run 447/cut 550.** The 130-sentence parent, task 2157, returned
`limited` at `post_tokenizer_tokens`. Its first two children (tasks 2158 and 2159) also returned
`limited`, both at `edus`. The existing fallback recursively created four successful sentence
coherent descendants: task 2160 `[811,4367)` emitted 177 products; 2161 `[4367,7866)` emitted
201; 2162 `[7866,11444)` emitted 189; and 2163 `[11444,15015)` emitted 191. The parent and
limited intermediate children remain in the retained run.

**Dipo reduced scope · run 448/cut 551.** The 90-sentence parent, task 2164, returned `limited`
at `post_tokenizer_tokens`. The first child, task 2165 `[811,5688)`, succeeded and emitted 237
products. The second child, task 2166 `[5688,10578)`, reached the separate `edus` limit; its
two successful descendants were task 2167 `[5688,8125)` with 147 products and task 2168
`[8125,10578)` with 135. Tokenizer preflight estimated 2454 parent tokens and 1242/1215 for
the two original children. The fallback correctly retained the EDU limitation and recursively
covered the oversized child.

All three runs settled as `finished`, `readiness: completed`, `supervisor: terminal`, and zero
unresolved agent tasks. A limited scope is an expected, typed result here; it is retained beside
the successful smaller work. The Dipo results demonstrate distinct tokenizer and EDU bounds.
The first Dipo pair did not fit in one split, so a smaller parent was tried; its denser second
child still required one additional split. Both attempts are preserved.

These runs establish execution and coverage behavior only. They do not grade mentions, EDU
boundaries, rhetorical structures, referent selection, or downstream consumer improvement.
Maverick supplied-mention comparison and Dipo layout-forced comparison are `not_run`; no
consumer-quality inference follows from fallback completion.

## Reproduction

```sh
uv run python docs/design_review/evidence/2026-11-09_pm2-scope-fallback/prepare.py \
  > docs/design_review/evidence/2026-11-09_pm2-scope-fallback/raw/prepare-report.json
uv run ci run parsers --request docs/design_review/evidence/2026-11-09_pm2-scope-fallback/raw/maverick-request.json --json \
  > docs/design_review/evidence/2026-11-09_pm2-scope-fallback/raw/maverick-run.json
uv run ci run parsers --request docs/design_review/evidence/2026-11-09_pm2-scope-fallback/raw/dipo-request.json --json \
  > docs/design_review/evidence/2026-11-09_pm2-scope-fallback/raw/dipo-run.json
uv run ci run parsers --request docs/design_review/evidence/2026-11-09_pm2-scope-fallback/raw/dipo-reduced-request.json --json \
  > docs/design_review/evidence/2026-11-09_pm2-scope-fallback/raw/dipo-reduced-run.json
```

The original read-only refusal is reproducible with
`uv run python docs/design_review/evidence/2026-11-09_pm2-scope-fallback/probe_prior_release_refusal.py`.

## Records

<!-- evidence-index:start -->
Generated by `just evidence index` from `records/`; do not edit by hand. 1 current, 0 superseded.


**pm2-adoption**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Maverick and Dipo coherent-scope fallback on retained source](records/pm2.native-parser-scope-fallback.json) | PM2-04/05 | partial | PM2-04, PM2-05 | 2026-11-09 |
<!-- evidence-index:end -->
