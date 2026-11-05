# Native operation-grade protocol dispatch

**Tested, 2026-11-05:** bounded operational repair for the already declared source-operation
reference grade. This evidence does not establish model quality or complete PCE qualification.

The actual grading failure is retained in
[`pce03-fresh-source-grade-003-failure.json`](../2026-11-05_pce-foundations/raw/pce03-fresh-source-grade-003-failure.json).
The operation-owned recorder validated its existing source-operation report, but the shared
`eval.guard_scientific_decisions` insertion trigger recognized only source-record reference sets
before entering the scientific comparison-array validator. A valid source-operation report
therefore failed on the absent, inapplicable `$.units[*].comparisons` array.

The guard now dispatches from the immutable reference set's `operation_protocol`. A report's
protocol cannot choose a different validator. Existing operation validation was extracted without
changing its checks into the private native `validate_operation_reference_evaluation` function;
the table trigger invokes it for each operation-grade insert. The protected recorder inserts
through this one enforcement point. Source-record and scientific checks retain their existing
branches. Migration 133 carries four native-only transitions; committed migration 132 is unchanged.

`baseline.json` and `identity-after.json` compare the full prepared artifact-digest map,
manifest digest, release identity and execution-model identity before and after the repair.
`identity-after.log` records the passing assertion: release
`release:19379a91a0b9d5b573891f2b15562c5371a209321bbc2bc950708f3209705f18`,
model `execution:54efc3aead0a621b79f3f7307d97f6e4bdf238ef02448eb2cd6319d6ffabce89`,
manifest and every artifact digest remain identical. The runtime identity changes. No source,
reference, prediction, schema, catalog or report-definition regeneration was performed.

| Receipt | Outcome | Bounded scope |
|---|---|---|
| `attempt-001/receipt.json` | passed | Owned clone upgraded to 132; four-transition candidate installed and admitted, then rolled back |
| `native-attempt-001.log` | passed | Nine real native fixture cases: actual operation grade insertion and forged protocol/grain refusals, heldout author export, and scientific grading/decision/required-array regression controls |
| `record-regression-001.log` | passed | Three source-record grading controls preserving missing-output denominators, changed-alias refusal and failed-producer evidence |
| `identity-after.log` | passed | Release/model/manifest/artifact invariance and changed runtime identity |

Commands, from the repository root:

```sh
uv run python docs/design_review/evidence/2026-11-05_operation-grade-dispatch/author-candidate.py attempt-001
uv run pytest python/corpus-structure/tests/evaluate/test_operation_assessment_native.py python/corpus-structure/tests/semantic/test_reference_evaluation.py -q --strict-markers --strict-config
uv run pytest python/corpus-structure/tests/evaluate/test_record_references_native.py -k test_native_missing_producer_keeps_denominator_but_real_alias_change_refuses -q --strict-markers --strict-config
```

Scoped Ruff and Pyrefly checks of the changed Python, native candidate support and prospective
133 wrapper passed. The candidate author updates the prospective Python descriptor hash from
its exact declared native catalog; the native fixtures then bootstrap the prospective forward
migration and use real evaluator/writer connections. There is no mocked provider or validation
bypass. Persistent deployment and grading the retained production runs remain coordinator-owned.
