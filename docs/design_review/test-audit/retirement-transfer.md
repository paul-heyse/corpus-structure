# Retirement and transfer

What happened to assurance when the semantic pivot retired its predecessors, and what the suite now
protects. SP-09 said to "remove replaced model projections, dispatch paths, unsafe raw writes and
obsolete tests together with their replacements"
([regeneration-and-acceptance](../../plans/semantic-model-pivot/regeneration-and-acceptance.md#SP-09)).
The previous version of this page predicted a risk; this one reports the outcome. Baseline, scope and
method are in the [README](README.md). Paths are relative to `python/corpus-structure/` unless they
start at the repository root.

<a id="dta-004"></a>

## DTA-004 — Independently stated outcomes for surviving behaviour lost their actual on the live path

**Lineage.** Formerly "Independent oracles for surviving behaviour live only in tests slated for
retirement". The risk it recorded was realized in part.

**Principles:** FP-04, FP-05, DP-23, CI-12 by analogy; companion §1, §4, §7.
**Subject:** implemented (`fixtures/toy`, `fixtures/trace`, `tests/fixtures/`; the deleted tests at
`c50a747`; surviving production under `src/corpus_structure/semantic/`).

**Diagnosis.** 23 test files were deleted between `c50a747` and this baseline. The tests that exercised
the independently written toy and trace oracles went with the legacy path (`92a1d39`), and the oracle
data stayed behind. Expectations written against legacy batch shapes and predicates were not re-expressed
for the semantic pack, and the plan's transfer clause names exercised capabilities, not outcomes.

| Oracle | Carried to | Production present? | Verdict |
|---|---|---|---|
| Toy: 9 claims, 7 accepted | Nothing. `fixtures/toy/ownership.json` and `registers.json` have no reader (search of `python`, `scripts`, `domains`, `justfile`) | Yes | **Lost** |
| Toy: 2020 applies, 2022 does not | `tests/semantic/test_serving.py:510-565`, one interval, hand-written | Yes | **Partial** |
| Toy: undated stays `unknown` | The `None` branch of `domains/toy/queries.py` `applicability` has no assertion | Yes | **Lost** |
| Toy: `ORG-101`, `ORG-202`, `org-101` stay three | `tests/semantic/test_prepare.py:240-251` asserts preserved `ABC` and `abc` give different `entity_keys` and casefolded ones equal keys, the branch production uses (`semantic/types.py:327`). `domains/toy/semantic.yaml:51-52` declares `cs:case: preserve` on `registry_id` | Yes | **Carried by mechanism** at `entity_keys`; not on the toy pack or through consolidation |
| Toy: F1 and F2 fuse | `test_publication.py:760`, `test_alternative_groups.py` duplicate collapse | Yes | Carried by mechanism (*Inferred*; located, not traced to the toy claim) |
| Toy: 0.5 and 0.8 stay ambiguous | `test_domain_operations.py:1064` onward | Yes | **Carried by mechanism** |
| Toy: Alpha and Beta stay separate | `toy:reported` declares `attribution_identifying`, which `semantic/` never reads; semantic tests treat attribution as a provenance key role | Unknown | **Possibly superseded in meaning, unrecorded** (*Suspected*) |
| Toy: notice not routed | Policy engine in `tests/orchestrate/test_policy.py`; nothing toy-specific. `test_regeneration.py` uses only `transfer` | Yes | **Partial** |
| Trace: `must_not` (16 patterns) | Structural only: `tests/fixtures/test_fixtures.py:183` checks named references exist. The matcher was deleted with `test_trace.py`. Condition-reference retention is covered by mechanism (`test_domain_operations.py:996-1010`, `test_reference_evaluation.py:524-620`, `test_statistics_cut.py:262`) | Yes | **Lost for the trace data.** Conditions carried by mechanism; modality preservation ("C1 with modality asserted") not located |
| Trace: `questions` (7) | Same query names in `test_serving.py:474-505` on a small hand-written pack | Yes | **Partial by mechanism;** trace-specific lost |
| Trace targets and s0 key alike | `tests/consolidate/test_assemble.py` | Stranded ([DTA-014](#dta-014)) | Carried, no longer live evidence |
| Trace: reverse-order equality | Entity partition arrival order: `test_identity_resolution.py:139-157` reverses observations through the live `_entity_mappings`. Fact and publication order: a search of `tests/semantic` and `tests/acceptance` for `reversed\|[::-1]\|arrival\|shuffle\|permut` finds none | Yes | **Partial:** partition order carried; fact and publication order not found |
| Lifecycle stateful model (`test_lifecycle`) | No model-based test remains (`RuleBasedStateMachine\|stateful`). Examples exist in `test_operations.py:1295` and `test_execution_native.py` | Replaced by native kernels, state space survives | **Model not carried;** suspected thinning |
| Label normalization | `tests/core/test_keys.py:75-99` survives with independent expectations | Yes | **Risk did not fire,** but see [DTA-015](evidence-and-discrimination.md#dta-015) |
| F02 named controls | `test_keys.py`, `test_dispatch.py`, `test_tex.py` exist. `fixtures/s0` has no reader under `tests/semantic`, so it no longer controls the live proposal shape | Mixed | **Stands in wording; one control changed meaning** |
| Golden store, `by_unit`, liveness and orphans, `ProfileRefused` | Removed or refused with production (`39a3e33`, `f40a9c4`, `7fadeff`) | Removed | Removed with production; no transfer owed |

A second consequence has the same cause: **the live scorer has only synthetic evidence.**
`evaluate/semantic.py` routes grading and pass agreement through `align_semantic`. Its direct tests
(`tests/evaluate/test_semantic_alignment.py`, 25 nodes) use an `Alice` batch and a compiled toy scientific
schema, and they are discriminating within that scope. All real-domain assessment of scoring (`test_parity.py`
on spike passes A and B, `test_align.py` on real `fixtures/s0` forms, `test_equivalence.py`) exercises
`evaluate/align.py`, `equivalence.py` and `agreement.py`, which `cli.app` does not reach. Real S0 passes exist
only in the legacy batch shape, so no route carries them to the current scorer. Even on the old scorer the
parity run prints 47 canonical and 2 numeric comparisons, with no symbolic decision and none of the 13 recorded
decisions firing.

Transfer obligations that remain open while the stack survives:
- `schema.rulelang` is live, but refusal codes are asserted only in `tests/schema/test_rules.py`, which reaches
  `Language` through the dormant `compile_paths` (`:58-60`, `:150`, `:205`), and `test_scientific_rule_views.py:97-99`
  has a bare `pytest.raises(RuleError)`. These 30 nodes are excluded from [DTA-014](#dta-014)'s count for that reason.
- `tests/orchestrate/test_policy.py:27-35` uses `compile_paths` only to list statement kinds for live policy code.

**Consequence.**
- On the live path, outcome expectations written independently of a production-defined domain are limited to the
  five positive assertions of `semantic-trace-reference`, the inspection reference (operational only), synthetic
  micro-schemas, and hand-written exact expectations on the real statistics schema over a test-assembled release
  (`test_statistics_cut.py:255-264`).
- A regression that drops a condition, flips a modality or merges case-distinct registry identifiers in the
  real statistics or toy pack is caught only if a micro-schema shares the mechanism, or by a provider run with
  graded positives.
- No deterministic no-provider journey for the real statistics pack runs from authored input to served answers.
  The nearest is `test_statistics_cut.py`, one test, on a test-assembled release
  ([DTA-005](support-structure.md#dta-005)).

**Footprint.**
- *Known:* the table's readers and deleting commits. A search for `DTA-004` across `docs/plans`, `docs/adr` and
  `STATUS.md` finds nothing, so no disposition is recorded anywhere.
- *Inferred:* the "lost" and "not found" verdicts, which are bounded by the searches stated. The independent challenge
  overturned two earlier "lost" verdicts this way, so a further carrier may exist.
- *Inferred:* mechanism transfers marked as such.

**Counterevidence.**
- Semantic micro-schema tests are many and often hand-written, and mechanism transfer is real for ambiguity,
  fusion and temporal applicability.
- `tests/semantic/test_trace_reference_fixture.py` keeps references written from source without reading extracted
  answers, each quote exactly one rendered sentence, and it was graded in a real run.
- `must_not` patterns need re-expression because the shape changed, so some loss is natural.
- An operator could accept this thinning. No record shows that choice.

**Uncertainty.** Whether Alpha and Beta should stay separate or fuse as provenance is a semantic owner question.
Whether S0 parity is a current obligation or a finished port check is an operator question.

**Leads (optional).** Treat the toy README bullets and trace `must_not` as requirements to re-express or retire
explicitly.

**Bears on:** original SP-09/SP-10; the phase-0 rescoping of evaluation; any claim about real-pack behaviour.

<a id="dta-014"></a>

## DTA-014 — About a quarter of collected nodes challenge code with no execution route, and nothing separates them from live evidence

**Principles:** DP-16 ("keep no shim or parallel path as evidence"), FP-01, FP-03, FP-04, FP-07/A4, DP-22, DP-23;
H27; companion §1, §2, §8.
**Subject:** implemented (`src/corpus_structure/orchestrate/phase0.py`; `tests/{core,schema,validate,consolidate,pool,db,evaluate}`;
`tests/legacy_*.py`, `tests/db/legacy_pool.py`, `tests/orchestrate/legacy_registry.py`).

**Diagnosis.** SP-09 rerouted execution to the semantic path and removed legacy writers, but retirement stopped at
execution routing. Two kinds of target remain.
- *Production with no call route.* `orchestrate/phase0.py:18`, `:41` instantiates config descriptors whose `run`
  methods refuse (`consolidate/pass_.py:75`, "use semantic.domain_operations.consolidate_cut"; `validate/runner.py:256-262`,
  "no orchestrator worker runs it"). Registration keeps these modules importable so `methods.yaml` sections resolve.
  Reachability from `cli.app`, the only console entry point, found no runtime import at all for `consolidate.assemble`,
  `finalize`, `write`, `core.frame`, `evaluate.align`, `equivalence`, `agreement`, `goldens`, `sets`, `methods.llm.parse`,
  `schema.compile`, `rules`, `reference`, `batches`, `change` and `registry`. `validate.*`, `pool.*`, `schema.tables`,
  `schema.lookup`, and `core.keys` beyond label and symbol normalization are reached by import only, with no caller on a
  live path found. `core.db`'s `_tables`, `overlay`, `migrations` and `alembic/` are imported only by themselves.
- *Code that now lives only in the test tree.* `legacy_db_repo.py` (552 lines) calls itself a "Historical database oracle".
  With `legacy_schema_registry.py` (363), `db/legacy_pool.py` (152) and `orchestrate/legacy_registry.py` (93), it has no
  consumer in `tests/semantic`. An oracle needs an actual, and nothing current is compared with these. Their main tests
  test themselves.

| Area | Nodes | What they challenge |
|---|---:|---|
| `tests/validate` | 150 | `check_stored`, `run_rules`, `check_batch`, `candidates_from_batch`: no live caller |
| `tests/schema/test_{interchange,packs,change}` | 122 of 123 | Compile and interchange stack (one packs CLI node is live; `schema.model` uses only `interchange` constants) |
| `tests/core/test_{keys,identity,conformance,carry_over,dispatch,references,frame,payload_schemas}` | 133 of 142 | Key scheme 1 and its contracts (9 label and symbol nodes in `test_keys` are live) |
| `tests/db` legacy modules plus one `orchestrate/test_registry` node | 89 | The retired schema and test-owned code |
| `tests/evaluate/test_{align,equivalence,parity}` | 34 | The old scorer ([DTA-004](#dta-004)) |
| `tests/consolidate`, `tests/pool` | 44 | `consolidate.*`, `pool.*`; `pool.steps` is reached only through `validate.views` |
| `tests/llm/test_parse.py`, `tests/agent/test_tools.py` | 13 | `methods.llm.parse`, `intervene.testing` |
| **Total** | **585 of 2,429** | Of the denominator, 127 are process-script tests. `tests/schema/test_rules.py` (30) is excluded: most assert the live `schema.rulelang` through a dormant fixture, and a handful target the compile stack |

A narrower manifestation has a stronger bound. `publish_batch`, `publish_on_connection` and `stage_batch` have no
`src` caller beyond definitions and a registry entry (`semantic/contracts.py:94`), while tests call `publish_batch(`
82 times in 19 files. Production writes through Arrow. Kernel refusals transfer, because both share stage relations
and the server recomputes content (`semantic_0040_kernels.sql:937`, `:954`). Lowering-specific behaviour does not, and
hostile vectors live only on the row path.

**Claim at risk.**
- *Contracts present as binding.* `tests/core/test_conformance.py:10-12` requires "a new scheme, a carry-over map and a
  new vector", while the pivot rules out old key scheme support.
- *Aggregates read as product assurance.* `STATUS.md:31` reports that the classifier covers all 2,429 required Python
  nodes. "Required" there is the selected union, since `classify` takes it from a supplied manifest
  (`scripts/test_receipts.py:537-551`). So about a quarter of that union cannot detect a current product regression through
  a live route.
- *"Independent historical oracle"* (`docs/design/D3-database.md:48-49`) reads as assurance about something.

**Consequence.**
- **DP-16.** Test work buys assurance about behaviour no route performs. Among other costs, `compile_paths` runs in three
  fixtures and subprocesses (`tests/schema/test_packs.py:74-89`, `tests/validate/test_views.py:335-368`).
- **Execution (FP-07).** Under [the receipt's conditions](execution-and-qualification.md#measurements), the modules in the table
  cost about 200 s, about 20% of recorded phase time: schema 101.5 s (including one 89.41 s draw test), legacy `db` 67.0 s,
  `consolidate` and `pool` 18.9 s, and the rest under 5 s each. This is execution with no current-route assurance, and it is
  larger than the clone route's whole setup and teardown.
- **Lifecycle (H27).** The persistent `cs_tpl_<hash>` template, its stamp and retention, the legacy sweep branch, and `db`,
  `db_engine` and `committing_db` exist largely for this set. Of 83 `db_server` nodes, 66 protect the superseded store, and the
  live ones are `db/test_store.py` (3) and `core/test_method.py` (5), plus 9 harness controls. `world` reseeds per test, so the
  outer rollback saves nothing there, and `test_invariants.py` spends 29.2 s in setup for no recorded call time. A complete
  `ensure_template` cold build took 0.18 s, so the persistent cache saves on the order of that per session.
- **Change scenarios.** A system-model change regenerates `_tables.py` (`schema/generate.py:554`) and, through
  `test_the_catalog_after_upgrade_equals_create_all`, forces a new revision on a history no live database upgrades to (SC1).
  `core.keys` retirement cannot be local (SC4). `test_port_check.py` compares two frozen sides of a retired schema: D3 itself
  now says its legacy shapes "do not constrain new releases" (`docs/design/D3-database.md:5-7`), and `port_residue.json`
  mostly records that D3 moved.
- **Misdirection.** A reader asking what enforces batch validity finds 150 strong tests of a validator production does not
  call. Stale self-descriptions make this worse: `fixtures/trace/README.md` still says acceptance checks "are not written
  yet" when they were written and deleted, `tests/orchestrate/conftest.py` has no consumer for `orch` and `Stub`,
  `intervene/testing.py` names callers `submit_batches` no longer has, and `cli/orchestrate.py:141` offers a `by_unit` that
  `orchestrate/semantic.py:77` refuses, with no test of the refusal.

**Footprint.**
- *Known:* the reachability result, confirmed by an independent rerun of the import graph, and the sites cited.
- *Inferred:* the per-module split behind the node figures, which uses per-file collection and judgment about each module's
  target. `tests/core/test_shapes.py` (80, unpartitioned) and parts of `tests/agent` may share the cause.
- *Suspected:* other routes outside `cli.app`. `justfile`, `import_module` and `__import__` were searched by name only.

**Counterevidence.**
- These are often the strongest tests in the tree: `test_conformance.py` has hand-written bytes hashed with `hashlib` and
  seeded changes, `test_invariants.py` has SQLSTATE per case with positive controls, and `test_batch.py` and `test_runner.py`
  have mutation cases tied to recorded outcomes. The weakness is the target, not the quality, and they are the asset any
  transfer would use.
- Plans deliberately retain "set kernels where valid" (`docs/plans/semantic-model-pivot_2026-10-29.md:78`), so part of this may
  be a reservoir. No document says so for `validate`, `schema.compile` or `key_claims`.
- Registration has a real consumer (`semantic/regeneration.py:121`), and ADR-0034's move of the oracles out of product paths
  is sound. Maintenance has been small: eight commits, 74 insertions and 28 deletions across the core, schema and validate tests
  since `c50a747`.
- Removal could thin `schema.compile`, `schema.registry` and `interchange` assurance. No per-invariant analogue of
  `test_invariants.py` with positive controls exists for the semantic schema, and many live guards have no reason-level test
  ([DTA-001](evidence-and-discrimination.md#dta-001)), so that file's technique is worth keeping even if its subject retires.

**Uncertainty.** Operator intent decides whether this is retire-with-transfer or a labelling problem. Static reachability
cannot exclude dynamic routes beyond those searched.

**Leads (optional).** Decide per module between retirement with transfer and a declared reservoir, and name what each oracle
judges. The transfer list is [DTA-004](#dta-004).

**Bears on:** SC4; `core.keys`; the phase-0 rescoping; how "required" counts are read.

## Links retained from the previous page

- The broad findings [DA-002](../audit/semantic-model-and-authority.md#da-002) and
  [DA-009](../audit/semantic-model-and-authority.md#da-009) still own the legacy mirror and key-pinning observations.
- [F02](../../plans/phase-0_2026-10-28.md#11-findings-disposition) keeps its home under the operator's exception. Only its
  test-scope state was reexamined here.
- `orchestrate/testing.py`, the former product harness with a stub default, was deleted by `ec48bfa`. `world` now has two
  definitions rather than twelve, so that manifestation of [DTA-009](support-structure.md#dta-009) is largely closed.
- `schema/model.load()` repetition (`tests/db/conftest.py:38-39`, `tests/pool/conftest.py:77`) is still minor and belongs to
  code under DTA-014.
