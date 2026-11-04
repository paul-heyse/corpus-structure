# M1 native record frontend implementation controls

**Implemented; Tested within the targeted scope below, 2026-11-04.** Baseline main
`daaabab0`. This assignment changes the six method owners, the named contextual configuration
and one focused methods test file. The coordinator owns admission, actual native calls, source
reconstruction, learning, qualification and plan disposition. No model, database, PDF conversion,
held-out data, training, native bootstrap, commit or root maintenance was performed here.

## Implemented contract

Source policy `m1-canonical-related-context-candidates-6` selects native pack ABI
`native-combined-v2`; producer version is6 and named configuration version is
`m1-candidate-4`. Default/whitespace and stored policy4/5 configuration remain supported.
V1 retains its explicit natural-anchor guard. V2 permits natural or latent formation and
refuses anchorless. Assertions use latent candidates from the shared field pool, with no
surrogate semantic anchor or capacity change. The existing SPO/reading-occurrence policy remains.

Definition `defining_text` uses native list/zero_or_more fragments. Exact typed intervals are
sorted by model coordinates, mapped by the existing source owner and checked for one
source-monotone coordinate space. Overlap, duplicate, changed literal, foreign report/pack,
synthetic crossing and reversed source order refuse. Multiple original pieces use the existing
TextSequence/original_pieces shape; one original piece retains Text/original. Independent source
states, cues, inspected scopes and the retained value branch survive. An empty list is no value
proposal; it does not establish absence. Existing occurrence-v2 refusal for incomplete definitions
is retained.

List confidence observations preserve actual returned fragment positions in `fragment_index`,
raw span dictionaries, group/field attribution and shared model/context dependencies. Scalar row
shape is unchanged. No whole-field probability is manufactured. The production feature owner
`semantic/record_policy.py::derive_record_features` continues to declare
`provider.raw_confidence` unavailable; this assignment does not change that feature ABI.

Policy6 additionally routes existing whole-block formula neighborhoods to prose families.
Equivalent consumed slices and retrieval/selected-source dependencies share a prose request;
all original formula requests, local failures and region-selection links remain. Different
retrieval/dependency semantics remain separate. Reports are produced for their actual context,
without replay, cache, retagging, cropping or source normalization.

## Checks and retained attempts

`uv run pytest python/corpus-structure/tests/methods/test_m1_record_frontends.py`
first returned **failed**,12failed/13passed. The fixture initially assumed that incomplete
definition fields still produce selected occurrence-v2 records and that only balanced
whole-block windows exist. Production correctly refused the former and preserved one-sided
windows. The controlled role tests now explicitly select the retained legacy term-occurrence
adapter when isolating unresolved-field behavior, and the routing test independently finds the
single full window among all alternatives. The failure remains in the tool transcript.

`targeted-002.jsonl` retains the next **passed** result:25cases. `targeted-003.jsonl`
retains **passed**,28cases after adding reversal, foreign-report and score-dedup controls.
The actual5/13fragment controls use the independently frozen challenger spans, original source
pieces and source rereads; they establish the ordering bridge, not a fresh source reconstruction.
The synthetic multi-item assembly control independently checks exact source pointers, offsets,
original pieces and evidence order while excluding genuine intervening text.

Final command, **passed**,147cases (`final-targeted-004.jsonl`):

```sh
uv run pytest \
  python/corpus-structure/tests/methods/test_m1_record_frontends.py \
  python/corpus-structure/tests/methods/test_gliner.py \
  python/corpus-structure/tests/methods/test_record_assembly.py \
  python/corpus-structure/tests/methods/test_record_readings.py \
  python/corpus-structure/tests/methods/test_m1_source_preparation.py \
  python/corpus-structure/tests/methods/test_m1_source_profile.py \
  python/corpus-structure/tests/methods/test_m1_producer.py \
  python/corpus-structure/tests/methods/test_m1_readings.py \
  --report-log=docs/design_review/evidence/2026-11-04_m1-record-frontends/final-targeted-004.jsonl
```

The earlier119case compatibility-only run is retained in `compatibility-001.jsonl`.
Existing Pandas/LinkML deprecation warnings remain. These tests exercise controlled providers,
pure assembly and native schema helpers; they do not establish actual model execution or quality.

Scoped endpoint commands, both **passed** (`ruff-002.log`, `pyrefly-002.log`):

```sh
uv run ruff check python/corpus-structure/src/corpus_structure/methods/{gliner,record_packs,record_assembly,m1_source,source_preparation,record_readings}.py python/corpus-structure/tests/methods/test_m1_record_frontends.py
uv run pyrefly check python/corpus-structure/src/corpus_structure/methods/{gliner,record_packs,record_assembly,m1_source,source_preparation,record_readings}.py python/corpus-structure/tests/methods/test_m1_record_frontends.py
```

Initial endpoint Ruff/type runs **failed** on local formatting and controlled-test typing;
the transcript retains these diagnostics. Repairs introduce no ignores or production typing
escapes. `git diff --check` **passed** after the implementation.

`baseline-pack-identities.log` retains a read-only comparison with `git show daaabab0`'s
original `record_packs.py` and configuration. Under the same prepared release, all21packs
across default/described/readings and the old policy5 contextual profile retain exactly equal
objects, declarations, versions and fingerprints. This establishes pack identity preservation,
not reuse of old producer results under the new version6 implementation.

Full native execution, new source/target reconstruction, training, benefit, five quality gates,
held-out assessment, publication and whole-M1 qualification are **not_run** here and remain
with the coordinator. No quality or denominator claim follows from these controls.

## Records

<!-- evidence-index:start -->
Generated by `just evidence index` from `records/`; do not edit by hand. 1 current, 0 superseded.


**M1**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Checked native list/latent record frontends and legacy compatibility](records/m1.record-frontends.json) | M1-07 | passed | M1-INT-F23 | 2026-11-04 |
<!-- evidence-index:end -->
