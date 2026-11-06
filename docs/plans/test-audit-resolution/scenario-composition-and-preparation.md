# Scenario composition and preparation

**Status:** Proposed. [Coordinator](../test-audit-resolution_2026-11-05.md) owns TR-01/02
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
macros and obtains its process-local NLP resources. No new serialization protocol is proposed.
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
