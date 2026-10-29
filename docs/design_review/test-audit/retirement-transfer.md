# Retirement transfer

What the tests slated for migration or retirement carry that the surviving paths will still need.
SP-09 says to "remove replaced model projections, dispatch paths, unsafe raw writes and obsolete
tests together with their replacements"
([regeneration-and-acceptance](../../plans/semantic-model-pivot/regeneration-and-acceptance.md#SP-09)).
This page records where independent assurance currently lives, so that retirement does not quietly
thin it. These are tier-3 observations made through the operator-approved transfer lens; they are
not per-test findings on code slated for deletion. Baseline, scope and method are in the
[README](README.md). Paths are relative to `python/corpus-structure/` unless they start at the
repository root.

<a id="dta-004"></a>

## DTA-004 — Independent oracles for surviving behaviour live only in tests slated for retirement

**Principles:** FP-04, DP-23, CI-12 by analogy; companion §1, §7.
**Subject:** implemented (tier-3 tests and fixtures cited below; surviving production in
`src/corpus_structure/semantic/domain_operations.py`).

**Diagnosis.** Several independently written oracles are consumed only by tests organized around
legacy modules. Their claims are not tied to the legacy store; they concern behaviour that the
semantic path keeps or must reproduce.

**1. The toy ownership oracle.** `fixtures/toy` states its expected outcomes independently of
consolidation and serving (`fixtures/toy/README.md`):
- nine materialized claims, seven accepted;
- at 2020-07-01 the 2020 interval applies and the 2022 one does not;
- undated claims stay unknown;
- `ORG-101`, `ORG-202` and `org-101` stay three organizations;
- F1 and F2 fuse;
- the 0.5 and 0.8 shares stay ambiguous;
- the notice paragraph is not routed.

Its JSON is read only by `tests/acceptance/test_toy.py`. The `toy/` paths in
`tests/semantic/test_operations.py` and `test_source_routing.py` are inline temporary corpora, and
`domains/toy` has no `semantic.yaml`.

**2. The statistics trace targets.** `fixtures/trace` targets were written from the `trace.md`
tables "independently of `fixtures/s0`", including `must_not` and `questions`. They are consumed
by `tests/acceptance/test_trace.py`. A search of `tests/semantic` for `fixtures/trace`,
`target.json`, `must_not` and `gold` found nothing.

**3. Label normalization.** Surviving `semantic/domain_operations.py:732-803` uses
`core.keys.LabelRules` and `normalize_label` for entity mapping and alias policy. The only
independent expectations for normalization output (articles, head words, rewrites) are in
`tests/core/test_keys.py` (the label normalization section), which is a tier-3 module. The
semantic tests check alias uniqueness and inheritance at preparation, not normalization output.

**4. F02's named controls.** The test-scope part of
[F02](../../plans/phase-0_2026-10-28.md#11-findings-disposition) is now met in wording.
`tests/core/test_shapes.py:4-7` calls schema validation "derivation conformance, not an
independent oracle" and names the independent controls: `test_keys.py`, `test_dispatch.py`,
`fixtures/s0` and `test_tex.py`. Two of those controls are tier-3 modules.

**Consequence.**
- When SP-09 retires the legacy paths, the only expected outcomes written independently of a
  production-defined domain go with them, unless they are carried over deliberately.
- Every remaining semantic expectation is then either hand-written for one micro-schema (good, but
  synthetic) or about the statistics pack, whose own content is the authority.
- A surviving production path (label normalization) would lose its only independent check.
- The plan's "small ownership/inspection transfer fixture" and the statistics trace run
  (regeneration-and-acceptance, SP-09) do not say that the toy README's outcomes, or the trace
  targets' `must_not` and `questions`, carry over.

**Footprint.**
- *Known:* the four items above.
- *Inferred:* further independent expectations in tier-3 modules that were not surveyed under the
  transfer lens. Candidates are the D3 DDL port check in `tests/db/test_port_check.py` and the
  golden tests.

**Counterevidence.** This is a transfer obligation, not a present defect: the oracles exist and
run today. `domains/statistics/semantic.yaml` tests exercise real domain content, and many semantic
component tests carry hand-written expectations ([evidence page](evidence-and-discrimination.md)).

**Related.**
- [F02](../../plans/phase-0_2026-10-28.md#11-findings-disposition) keeps its home in the phase-0
  findings table under the operator's exception for the alignment review; only its test-scope state
  was reexamined here.
- [DA-002](../audit/semantic-model-and-authority.md#da-002) and
  [DA-009](../audit/semantic-model-and-authority.md#da-009) own the legacy mirror and key-pinning
  observations.

**Bears on:** SP-09 retirement; SP-10 clean regeneration with a transfer fixture; the phase-0
rescoping of evaluation and goldens.

## Further transfer observations (tier 3)

These are recorded for SP-09 planning. They are not separate findings.

- **The product harness modules drive only the legacy path.**
  - `src/corpus_structure/orchestrate/testing.py` defaults acceptance runs to
    `phase0.stub_evaluate` (`:35`), `consolidate.run_pass`, `phase0.registry` and the `PHASE0`
    graph. `src/corpus_structure/intervene/testing.py` submits `core.batch.AuthoredBatch` fixtures.
  - Both docstrings say they are shared with evaluation, but their only consumers are tests: the
    acceptance, agent and `orchestrate/test_complete` modules (search of `src` and `tests`).
  - The semantic journeys have no equivalent driver. They patch the documented CLI hooks
    `cli.ENGINE`/`cli.PHASE0` with an untyped dict (`tests/semantic/test_source_routing.py`).
  - The SP-10 rule "a mocked provider is never a pass" applies to whatever replaces the stub
    default.
- **Protocol stubs embed their own decision rules.** The tier-3 `Stub` methods
  (`tests/orchestrate/conftest.py`, `tests/evaluate/golden/conftest.py`) each define their own
  `input_digest` and packet-id rule, and the two rules differ. That is acceptable for protocol
  doubles, but they should not become evidence on the new path.
- **Legacy harness precedents.**
  - The migrated template with an advisory-lock lease and sweep (`tests/conftest.py:238-318`) is
    the obvious precedent for [DTA-002](execution-and-qualification.md#dta-002). Its key premises
    are owned by [DA-018](../audit/boundaries-and-composition.md#da-018) and its races by
    [DA-019](../audit/boundaries-and-composition.md#da-019).
  - Its rolled-back-transaction `db` fixture gave cheap isolation that native semantic claims
    cannot use.
  - The module-scoped, mutable agent `world` (`tests/agent/conftest.py`) shares lease state across
    tests. Its semantic replacements use a database per test, so that cause does not recur.
- **The same support-structure cause recurs in tier 3.**
  - `world` is defined in 12 places, and `env` in three, with different scopes and meanings
    ([DTA-009](support-structure.md#dta-009)).
  - `schema/model.load()` is uncached and rebuilds two `SchemaView`s per fixture use
    (`tests/db/conftest.py`, `tests/pool/conftest.py`). This is minor repetition on a model being
    retired.
- **Dependencies to sort before deletion.** Surviving semantic code and tests also depend on:
  - `schema.relational.compile_metadata` (`src/corpus_structure/semantic/metadata.py:18`);
  - `pool.steps` (`tests/semantic/test_analytics.py`);
  - `core.db.store.open_store` (`tests/semantic/test_interop.py:11`).

  The pivot plans keep these foundations. `core.keys` and `core.values`, also imported by
  `semantic/domain_operations.py`, have no settled fate in the plans.
- **Owned legacy test-infrastructure findings remain where they are.**
  - [DA-018](../audit/boundaries-and-composition.md#da-018) and
    [DA-019](../audit/boundaries-and-composition.md#da-019) (broad audit).
  - [Q4-01](../../plans/phase-0_2026-10-28.md#11-findings-disposition): the legacy harness still
    uses `DROP … WITH (FORCE)` in `tests/conftest.py`.
  - [I2A-01](../../plans/phase-0_2026-10-28.md#11-findings-disposition): the forked
    `cpu_count` pool in `tests/math/conftest.py`.
  - [DA-014](../audit/structure-and-invariants.md#da-014), plus F01 and F03 in phase-0 §11.
  - This audit reexamined only their applicability to the transfer question; it did not refresh
    them.
