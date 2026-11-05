# Invocation-scoped local semantic publication preparation

**Implemented / focused Tested, 2026-11-05.** F27 repairs the two local semantic
publication functions in `semantic/sql/record_publication.sql`. Qualification at
the new frozen native head remains the coordinator's integration obligation.

Candidate discovery materializes each distinct protected evaluation binding and
selected origin once, expands authored and assessed cases independently, and
matches their full unit/pass/frame/case identity and assessed contribution ID
before exact applicability checks. Distinct valid grade/case witnesses survive;
only exact duplicate assertion rows collapse.

Final validation retains the exact current final-cut/run/selected-origin and
immutable dependency checks for every staged row. Its subsequent invocation-local
query materializes grades by project/release/evaluation/digest, each selected
origin's contribution array, source product membership, and keyed unit/case/
operation matches. Left joins retain malformed staged rows; explicit cardinality
checks reject missing and ambiguous witnesses. The existing protected grade
helper remains the sole grade/current-C authority. No persistent cache, table,
model change, or raw-adjudication grant is introduced.

`check_rollback.py` installs only these two function bodies in a rollback-only
transaction on the configured working database. `rollback-001.log` records the
initial 16-witness smoke pass. `rollback-002.log` also records ten independent
mixed-batch refusals, each retaining the other valid witnesses and recomputing
the forged row's assertion identity: unit, pass, frame, cut, origin, selected task,
evaluation ID, evaluation digest, case, and statement. These are native boundary
controls on retained controlled witnesses, not a new producer or quality claim.

Commands:

```sh
uv run python docs/design_review/evidence/2026-11-05_pce-local-capabilities/f27-batch-validation/check_rollback.py
uv run ci schema native-candidate --out docs/design_review/evidence/2026-11-05_pce-local-capabilities/native144-candidate-001 --json
```

Both passed. The candidate has predecessor `semantic_pce_ports_20261105`, three
native transitions and zero ordinary table operations. `candidate-001.log`
retains the authoring warnings and successful result. Frozen earlier migrations
were not changed. Source SHA256 at authoring:
`27db87ddeb7d72c5bd6267ec1dbc7b4f322f28640870c3cbdb8f22a2b24cf262`.

The change removes repeated whole-grade and source-array reconstruction
structurally. No latency, throughput or capacity improvement was measured.

Focused native144 qualification, 2026-11-05:

- `uv run pytest python/corpus-structure/tests/semantic/test_local_semantic_admission_native.py -q -x`: **passed**, all 21 cases; exit 0, `pytest-native144-003.log`.
- The affected 11-case selection also passed in `pytest-native144-002.log`.
- `pytest-native144-001.log` retains the interrupted initial run and its fixture-teardown `KeyError`; `pytest-native144-diagnostic-001.log` retains the failing single-case diagnostic. The new test initially expected four applicable witnesses from two grades and two authored cases. The evaluator correctly captures one source prediction for one case, so the independent expectation was corrected to the two exact grade/case-0 witnesses, with case-1 remaining ineligible. No SQL or frozen payload changed during this correction.

This is the complete local semantic admission native file, not assembled PCE
qualification or a new actual-source publication receipt. The coordinator owns
those broader conclusions and final-source accounting.
