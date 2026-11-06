# Scenario composition and preparation

**Status:** Implemented; TR-02 focused Tested; full qualification stopped by operator2026-11-06. [Coordinator](../test-audit-resolution_2026-11-05.md) owns TR-01/02
and finding disposition. Package-relative paths below designate test support unless stated.

## TR-01 — Explicit pure/native/reference composition

Replace private module bindings with ordinary support functions and explicit fixtures organized
around preparation, source publication and reference authoring. Select two existing-responsibility
layers: pure preparation returns original SourceBundle/dependencies/profile and PreparedRelease;
native construction consumes that result plus explicit method/source options and returns the
owned scenario references. Reuse native_record_fixtures.publish_native_record_fixture for actual
stage/freeze/validate/seal. Reference authoring consumes scenario inputs and separately authored
readings, origin assignments and labels. It never calls producer candidate() for expected meaning.

The affected seed is `semantic/test_private_records.py:76–371`. Extract its pure preparation so
`test_private_placement_preserves_schemas_and_excludes_graph_applicability` can run without a
native engine, publication or run/task state. Keep full source/publication fixtures for consumers
whose claims require those effects. Return the original preparation inputs explicitly: compatible
successor controls in `evaluate/test_record_references_native.py` must no longer intercept
prepare_release merely to recover them.

Migrate the specializing consumers as one coherent slice:

- evaluate/test_record_references_native and test_record_policy_authority_native;
- semantic/test_record_reading_closure_native and test_local_semantic_admission_native;
- their private-source, contextual and reference helpers and any maintained consumer of those
  extracted contracts discovered by import/call search.

Represent the actual independent variation: observation/reference input composition, method name
and Config, registry targets, source options, expected reading/frame, origin assignment and
reference-set label. Functions/immutable ordinary values and pytest dependencies suffice. A method
name must not select a SimpleNamespace interception. Source-specific expected values stay with
the independent assurance owner, not a configurable expected-answer generator.

Follow methods/test_m1_readings, test_m1_record_frontends, test_m1_source_profile and PDF helper
consumers for their actual shared responsibilities. Move shared mechanics out of test hosts when
they activate unrelated setup or private specialization. Trivial constants/imports alone need no
rewrite. Existing six TA scenario owners remain; extend/reuse them where meaning matches rather
than introducing parallel support with a new name.

Collection has a concrete independent correction: semantic/test_publication.py:145 computes
R=fixture_model()[1].release_id during import and captures it in batch defaults. Replace it with
an explicit prepared/release argument at shared builders; resolve preparation at the fixture or
calling case. Migrate execution, Arrow publication, analysis-boundary, shared math and PostgreSQL
adoption consumers together. Merely moving the eager expression to a support module is not a fix.

**Acceptance:** focused reference/policy/direct-reading/local-admission cases retain their meaning;
unrelated descriptor/import changes do not alter scenario policy; preparation inputs are returned
without interception; collection of extracted support performs no compilation/native acquisition;
actual commits and independent source answers remain. Remove obsolete helper implementations,
private-global patches and replacement imports when callers migrate. Keep frozen reference data.

## TR-02 — Demand-shaped math with shared explicit stages

Choose staged preparation over independently rebuilding each capability tier. Separate narrow
fixtures are initially simpler but would parse the same spike pages repeatedly in the full run.
No lazy scopes property, process-global mutable cache or persistent preparation cache is selected.

Use four session-scoped fixture products with ordinary dependency edges:

| Product | Construction and ownership |
|---|---|
| Retained content | Load validated historical content/effective frozen macros without math parsing |
| Readings | Spawn read_spans using retained input; return PageReadings to the session owner |
| Extraction | Spawn formula_values/extract on cached readings; return only values/extraction |
| Scoped | Spawn resolve_scopes on content/macros/values/extraction; return scopes only |

Assemble consumer views in the parent using its existing content/readings rather than retaining
three complete deserialized copies. Never share mutable effect state among tests; a consumer that
mutates a support value receives its owned copy. Stage functions are module-level/picklable and
invoke existing production algorithms. The session's fixed source/configuration defines reuse;
changed source/configuration needs a distinct product, not reuse under an ambient latest input.

Generalize math_support._run_pages only enough for page-keyed payloads. Retain bounded outstanding
submission, distinct page identities, spawn, submission-to-result deadlines, PageWorkError naming
its page, completed/incomplete/not-submitted diagnostics and pool.kill_workers on BaseException.
Main-thread worker execution preserves parser SIGALRM behavior. Each submitted stage has its own
active-job deadline; there is no wall-clock deadline spanning distant fixture requests. Retain
direct analyse_all whole-page-job semantics for its current direct callers, composing the same
stage functions internally. The explicit distinction prevents an accidental timeout-contract change.

Feasibility is **Interface-checked by source inspection,2026-11-05**: production SpanReading
__getstate__ (spans.py:70–78) transports span/result and drops process-owned preparation;
MathResult.__getstate__ (grammar.py:422–431) handles immutable macro mappings. formula_values
and extract use finished results/trees/occurrences; resolve_scopes uses content/values/extraction/
macros and obtains its process-local NLP resources. Execution correction2026-11-05: installed Lark Token.__reduce__ drops end_pos/end_line/end_column.
Real staged Normal results lost terminal relations and T2 reopening while values/mentions remained
equal. Existing SpanReading/MathResult transport is therefore necessary but insufficient.
Use multiprocessing's reducer registration for Token to carry all eight native constructor fields,
in the parent before submission and each spawned worker initializer. Keep ordinary pickle unchanged,
register at execution rather than import, and preserve existing worker bounds/lifecycle. Independent
nested-token and original frozen scope checks establish full positional fidelity. No new wire object
or parser reconstruction is selected; the enclosing review assesses this bounded target amendment.
Actual worker behavior must still be tested during implementation; source inspection is not a pass.

Migrate the current consumer set:

| Consumer | Minimum product |
|---|---|
| math/test_property corpus-layer spike control | Readings |
| math/test_spans M09 spike control | Extraction |
| math/test_scope core-standing, suppose-again, annotated, typed-extent controls | Scoped spike pages |
| math/test_scope held-out standing control | Scoped S0R2 pages |
| math/test_scope M13 block-split reconstruction | Retained content; it deliberately exercises sentence splitting only |

Search current consumers at implementation baseline to include any additions, not to freeze this
list against later work. Keep coverage_rows' narrow path, independent printer/scientific answers,
frozen macro ownership and source provenance. Do not change production caches or cold compiler
tests to accommodate fixture reuse.

**Acceptance:** content-only requests invoke no parser; readings invoke no extraction/scopes;
extraction invokes no scope/NLP work; scoped cases execute real resolution. Selecting all tiers
shares parsing instead of rebuilding it. Check real transported outputs with independent existing
expectations and bounded work observations; retain timeout, failure and interruption controls
that settle children and identify incomplete pages. No timing target or benchmark is required.

## Foundation and library rationale

Pytest dependencies/session lifetimes express capability reuse without a fixture engine.
Existing ProcessPoolExecutor(spawn), futures.wait(FIRST_COMPLETED), kill_workers and module-level
functions already own execution; do not add another worker manager. Reference expectations are
not part of the preparation cache. A newly added record family varies explicit inputs and
independent meanings; it should not need monkeypatching an unrelated test module.

Sources: current math_support.py; production methods/math/{spans,grammar,scope}.py;
[pytest fixture contract](https://docs.pytest.org/en/stable/how-to/fixtures.html);
[Hypothesis orientation](../../libraries/analytical_infrastructure/hypothesis.md).
Hypothesis state machines are unnecessary for these deterministic preparation/lifecycle changes.
TR-01 supplies pure preparation to TR-02's prepared-only semantic case; math staging can proceed
independently. Changed callers migrate with their producer. TR-09/10 owns preservation/integration.

## Execution amendment — lossless parsed-token transport

**Implemented / focused Tested,2026-11-05.** TR10-F01 identified
that Lark1.3.1 Token reduction drops terminal end coordinates. Token equality is string-oriented
and cannot establish positional fidelity. Use a lightweight worker initializer/adapter, independent
of heavy math/NLP imports, and explicit eight-field nested-token comparisons in both directions.
Retain independent terminal-relation bounds and frozen corpus scope answers. A process initializer
that imports all math support consumed the existing lifecycle probe's short deadline; narrowing
imports preserves that deadline instead of increasing it.

The [Lark overview](../../libraries/parsing/lark.md) §6.2/6.3 describes token/tree source metadata;
§10.3's save/load is for compiled parsers and does not solve parsed-token transport. The
[concurrency overview](../../libraries/analytical_infrastructure/Python_Concurrency_Multithreading_Multiprocessing_and_Worker_Management.md)
§4.4 covers worker initialization/termination and §11 compares alternative executors. Apply its
version-sensitive guidance to installed Python3.14.10, not later-version-only capabilities.

Independent review compared installed Joblib1.6.0's Loky implementation: per-executor
job_reducers/result_reducers and shutdown(wait=True,kill_workers=True) can implement the full target
with narrower reducer policy scope. That is a valid alternative, not an absent capability.
Select the existing stdlib executor with multiprocessing.reduction.register because this policy
is one deterministic lossless reduction for all multiprocessing transfers of the same Token value,
with no scenario/source/expected-answer state or competing reducer found in current repository
scope. Ordinary pickle is unchanged. Loky would add an executor/serialization provider, direct
pin/ownership, cloudpickle selection and a changed shutdown route without a currently required
separate transport policy. Revisit if competing Token policies or executor-local isolation become
requirements. Do not mutate Token methods, use global copyreg, or restore private dispatch tables.

**passed:** final28-case native worker/tier selection in
build/test-receipts/tr02-math-lightweight-adapter-final; original scope/printer answers unchanged.
[Finalized record](../../design_review/evidence/2026-11-05_test-audit-token-transport/records/tr02.math-token-transport.json)
retains exact commands/source, all-eight-field bidirectional tests, relation bounds and earlier
failed/interrupted attempts. Root evidence finalization and `just evidence` passed (0 errors;
40 existing repository warnings). This component result does not establish full-series qualification.

## Execution handoff — 2026-11-06

Scenario migration and the assembled review are complete. The initial serial full run passed its
math/corpus/worker section, including the unchanged78page coverage and frozen scope controls;
full-series qualification was interrupted later at operator request. Existing successful results
are retained, not scheduled for replay. The new16worker configuration puts shared math preparation
consumers in one loadgroup; their own bounded child pool and deadline semantics are unchanged.
New parallel configuration evidence is separate from the earlier28case math transport record.
The qualification companion owns remaining1390 original nodes and the explicit stop.
