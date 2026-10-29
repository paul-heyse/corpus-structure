# Retirement dependencies (LOP-X001)

This page records comparative judgments for:
- CBO-006: the equivalence kernels;
- CBO-005: the released rule view;
- CBO-018: the DuckDB set kernels;
- the location of CBO-008's physical lowering.

Baseline, inputs and method are in the [README](README.md). Paths are relative to
`python/corpus-structure/src/corpus_structure/` unless they start with `docs/` or `domains/`.
Every recommendation is **Proposed**.

**Premise correction for this whole group.** SP-09 names no modules it removes. Its text says to
remove "replaced model projections, dispatch paths" after the consumer inventory, and that "useful
pure algorithms … stay". The coordinator plan's §3 says to *reuse* `schema/model.py`, `lookup.py`
and `relational.py`, and `duckdb_engine`'s scoped registrations. So "SP-09 retires `schema` and
`pool`" was the codebase account's reading, not the plan's.

The ordering below is therefore written as "before module X can be deleted", whenever SP-09 decides
to delete it.

<a id="cbo-006"></a>

## CBO-006 — One equivalence kernel: evidence in one place, policy per consumer

**Premise: the two kernels already decide differently, and one of them drives selection.**
(Coordinator-verified in source.)

**Domain path.** `evaluate/equivalence.py` `ValueComparator`, reached through
`_comparison_value`/`_comparison_condition` and the private `_constraints`.
- Agreement at 6 or more sample points *proves* equality (`NUMERIC_MIN_POINTS = 6` → `Tier.NUMERIC`
  equal).
- Sampling respects the claims' `member`/`cmp` conditions.
- The first tier is the ADR-0012 token form.
- Text is compared after NFC normalization and casefold.

**Evaluation path.** `evaluate/semantic_alignment.equivalent`.
- Numeric probes can only *disprove*. Coincident probes without a symbolic proof remain `undecided`.
- It does not sample when conditions are present, and its sampling ignores the domain.
- The first tier is exact `canonical_bytes`.
- Text is compared exactly unless the release declares a `case_policy`.

**Why it matters.**
- A G4 scratch check found that `"Normal  dist"` versus `"normal dist"` is canonical-equal in the
  domain kernel but unequal in the evaluation kernel.
- `PolicyDecision` drops every accepted fact in a numeric-tier `equivalent_components` group except
  one. So one kernel's numeric agreement removes facts from selection, while the other would grade
  the same pair as undecided.
- D7 §5.3 (Proposed) describes the domain behaviour. The SP-08 plan said to *migrate*
  `equivalence.py`, not to write a second kernel.

**Options.**
- **A. Keep two kernels.** The drift remains, and `core.values`, `core.keys`,
  `evaluate/equivalence.py` and `align.py` cannot be deleted.
- **B. Use the evaluation kernel everywhere.** Consolidation silently loses constrained sampling and
  token-form equality.
- **C. Keep `ValueComparator` with `core.values` as the kernel's private model.** Evaluation gives up
  its walk over release definitions.
- **D. Split by responsibility.**
  - The release-driven structure walk (from `semantic_alignment`/`semantic_values`) becomes the
    single operand route.
  - A pure math module in `methods/math/`, next to `grammar`, carries over the legacy tier logic:
    token-form tier, symbolic tier, relation and set handling, seeded *constrained* sampling, and a
    public reading of restrictions that reports whether it is complete.
  - The kernel *reports evidence*: canonical, symbolic, numeric agreement, numeric counterexample
    or undecided. Each consumer maps that evidence to decisions.

**Revealing case.** A single numeric policy for everyone either stops consolidation from merging
numerically coincident facts or makes evaluation laxer than its stated stance. Separating evidence
from policy avoids forcing either. Domain assessments already record `comparison_tier`.

**Recommendation.** Recommended target D. The numeric policy per consumer is **unsettled**.
- **The competing policies:** "numeric agreement establishes equivalence" (D7 §5.3 and the current
  domain path) versus "numeric agreement only disproves" (the current evaluation path).
- **Consequence:** what consolidation selects, and what scores mean.
- **Settling evidence:** an owner decision by the D7 §5.3 and domain-operations owners. Comparing
  both mappings over existing fixture pairs, with no database, would show the impact.
- **Retained in the domain path:** binding distinctness, macro-context refusals, and identity
  `ref_eq`.
- **What disappears:**
  - `_comparison_value` and `_comparison_condition`;
  - the private `_constraints` call;
  - `core.values` as an operand model;
  - the canonical-value functions in `core.keys`;
  - `evaluate/align.py`, which is now test-only;
  - the unvalidated `model_copy(update=…)`.
- **Ownership:** domain decisions stop importing `evaluate`.
- **Prerequisite order:** this must land before `core.values`, the `core.keys` canonical and
  token-form functions, `evaluate/equivalence.py` and `evaluate/align.py` can be deleted.

**Rule impacts.**
- D7 §5.3 and the domain-operations owner: the numeric-evidence policy for each consumer.
- ADR-0012: the token form must survive in the math module.

<a id="cbo-005"></a>

## CBO-005 — A declared semantic rule view that keeps the authored vocabulary

**Premise, with corrections.**
- **The policy view is already partly logical.** It is a `SimpleNamespace` populated from semantic
  candidates. What remains legacy is the *type contract* (`schema/rules.py` dicts) plus small pieces
  from `validate/views.py`, `pool/steps.py`, `consolidate/finalize.py` and `core.keys.LabelRules`.
- **`schema/rulelang.py` is not legacy.** It is the shared compile discipline, also used by
  `orchestrate/policy.py`. ADR-0018 says one expression engine serves validation and routing.
- **The private AST read can be narrowed.** `ExpressionBase.result_type` carries a docstring ("The
  data type of the result of successful evaluation", coordinator-verified). Unwrapped from its
  nullable form, it matched private `_object_type` across five access forms in a G4 scratch probe on
  5.1.0. The attribute lives in the `ast` module, which upstream still marks private.
  `Rule.statement` is undocumented. This narrows the library assessment's negative result; it does
  not overturn it.
- **Defects the refresh missed:**
  - The `views` kernel hard-codes the legacy `core:ExternalReference` class (`pool/steps.REFERENCE_CLASS`),
    which is a dead filter in the semantic path.
  - Keyed collections are declared `map[Value]` while the accessor delivers raw dicts. This is
    latent; today's rules read only the keys.
  - `slot_kind` now derives from the value's own kind.

**Options.**
- **A. Retain.** It cannot survive deletion of the legacy modules.
- **B. A declared semantic rule view.** A module owned by domain operations, for example
  `semantic/rule_view.py`, holding:
  - the frozen `semantic-domain-2` type contract, copied rather than imported;
  - frozen slotted dataclasses for Claim, Entity, Value, Statement, Binding, Node and Qualifiers,
    with `accessor=getattr`;
  - the token helpers on `core.tex`, the `GRAMMAR_KINDS` mapping, and `views:` parsing.

  `rulelang` and its string notation stay. `_ref` reads `expr.object.result_type`.
- **C. Build `DataType` objects directly from LinkML definitions.** This would rename authored
  attributes.
- **D. Migrate the authored vocabulary** under `semantic-domain-3` (about 177 rule lines).

**Revealing case.**
- A view that copies the types could hide accessor values that disagree with them (`map[Value]`) or
  attribute sources that have shifted (`slot_kind`). The view module must state each attribute's
  semantic source.
- Correcting `map[Value]` changes which archived text compiles, so it needs a `VERSION` bump. Do it
  before SP-09 regeneration archives the new release, or record it as a known limit of
  `semantic-domain-2`.

**Recommendation: recommended target B.**
- **Retained domain rules:**
  - vocabulary admission and the literal walk;
  - refusing `$now`, `$today`, `$random` and regex over formulas;
  - undecided never counts as a pass.
- **Smaller changes:**
  - Replace `REFERENCE_CLASS` with an explicit parameter declared by the release, or drop it.
  - Move `LabelRules`/`normalize_label` to `semantic/identity_resolution.py`; evaluation also uses
    them.
  - Add a regression test over the pack rules for the `result_type` route.
- **ADR-0018's scope.** It binds the engine and the shared `rulelang` discipline. `Chain` applies to
  routing only (`orchestrate/policy.py`).
- **Prerequisite order:**
  - before `schema/rules.py`, `validate/views.py` and `consolidate/finalize.py` can be deleted;
  - with [CBO-018](#cbo-018) before `pool/steps.py` can be deleted, because they share `ViewSpec`;
  - before `core.keys` can be deleted, through the `LabelRules` move.
  - Moving `rulelang` is needed only if the `schema` package itself goes.

**Rule impact.** An optional `VERSION` → `semantic-domain-3` if the view's types are corrected.

<a id="cbo-018"></a>

## CBO-018 — Relocate the DuckDB set kernels; bind them natively

**Premise.** Still valuable, mainly as a question of *where the kernels live*. Name collisions from
the regex are unlikely today. The `pool` parity harness (Python versus DuckDB engines) is currently
the kernels' independent oracle, and it goes away when they move.

**Options.**
- **(i)** Relocate and keep the regex.
- **(ii)** Relocate, then bind single-input kernels with `DuckDBPyRelation.query(name, sql)` and the
  multi-input `views` kernel with a `TEMP MACRO … AS TABLE` that takes `query_table` names. Both
  were probe-verified on 2.0.0 ([duckdb](../libraries/duckdb/README.md#applicability-cbo-018)).
- **(iii)** Relocate, with explicit `{placeholder}` identifiers.
- **(iv)** A rewrite in the relational API.

**Revealing case.** Moving the kernels without independent expectations would let them grade
themselves, which conflicts with AGENTS.md's testing rules.

**Recommendation: recommended target (ii); (iii) is an acceptable equivalent.**
- `_DISAGREEMENTS`, `_VIEWS`, `_SPECS`, `_APPLIES`, `ViewSpec`, `SAME_SLOT`/`ALTERNATIVE_OF` and the
  `VIEW_*` schemas move to a semantic set-kernel module owned by `AnalysisScope`.
- The macros are created once per scope connection.
- Drop the `REFERENCE_CLASS` predicate.
- Carry a small set of independently expected results for `views` and `disagreements` into the
  semantic tests before the harness is deleted.
- **Prerequisite order:** before `pool/duckdb_engine.py` and `pool/steps.py` can be deleted, together
  with or before CBO-005.

<a id="cbo-008-location"></a>

## CBO-008 (location) — Move the physical lowering out of `schema/`

**Premise.**
- `_compile_physical` (`schema/relational.py`, about 85 lines) depends on `NAMING_CONVENTION`,
  `check_name`/`digest` and `ci_annotations`/`ModelError`.
- **Missed by the refresh:** `PHYSICAL_MODEL_ID` is a sha256 of `physical.yaml`'s raw bytes. It is
  bound in authored-SQL admission, in analytical capture and as `model_revision`. Any byte edit to
  `physical.yaml` is therefore a physical-identity event.

**Options.**
- **A.** Leave it in place.
- **B.** Move it into `semantic/` with a small typed `ph:*` reader, keeping `check_name` and
  `NAMING_CONVENTION` byte-identical.
- **C.** B plus structured `ph:*` annotations. linkml-runtime 1.12.1 loads nested values, while
  `ci_annotations` currently stringifies them.

**Revealing case.** Changing the CHECK digest scheme during the move would add to the 24
constraint-name mismatches the probe found.

**Recommendation.**
- **Do B now.** It is a pure move. Confirm it once by checking that `CreateTable` output is
  identical for every table.
- **Defer C,** folding it into the [CBO-008 reconciliation revision](native-integrity-and-execution.md#cbo-008)
  if one is scheduled before SP-09 regeneration. C changes `PHYSICAL_MODEL_ID`.
- **Prerequisite:** B must happen before `schema/relational.py` and `schema/model.py` can be deleted,
  but the plan currently retains them.
