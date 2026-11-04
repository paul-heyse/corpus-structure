# Audit-closure assembled review: independent F01 delta

**Implemented / scoped assessment, 2026-11-03.** Separately attributed to the independent
assembled design reviewer. This continues the original holistic engagement under core/template3.3,
heuristics1.0, code-intelligence1.4 and the repository binding; it is not another broad review.

**Decision: Accept the F01 correction at source level.** The correction supplies the shared
producer/coverage composition missing from the original review. Its revised judgments apply to
that boundary. Native102, final-source applicability and complete AC14 qualification remain open.

## Baseline and preservation

The original [assembled review](design_review_audit-closure-assembled_2026-11-03.md) was published
verbatim at `de61cc38`; its diagnosis and Revise decision remain an accurate assessment of its
`31ea1dad` plus identified working-change baseline. This delta inspects correction `c82d8910`,
integrated on main at `f6d43b9df3738cbfe57cfa87c267d96797aa497d`, plus the coordinator's inspected
working change adding `methods/llm/producer.py` to `QUERY_SOURCES`.

Inspection was read-only. No test, database operation, provider call or probe was run by this
reviewer. No repository file was changed. The coordinator owns publication, the finding's current
disposition and final evidence applicability.

## What settles the original finding

**Implemented, source-inspected, 2026-11-03:**

- `semantic/coverage_contract.py:6` publishes recipe4. Its supported producer names and proposal
  protocol come from `methods/llm/producer.py`, while its protocol version comes from the existing
  proposal owner. The read side no longer authors a competing current Opus-only selector.
- `semantic/query.py:891` accepts only the recognized complete current or historical recipe.
  Recipe4 validates the run's immutable named producer configurations through `producer_binding`
  (`:935` onward). Unsupported/missing declarations produce an explicit not-established coverage
  requirement; they cannot justify absence.
- The required population is selected from compatible effective-origin tasks (`:970` onward),
  including the source units of both admitted producer identities. It does not require a report
  to exist before including a required unit. Reused tasks retain their effective-origin identity.
- Persisted method version, method/task unit, configuration name, complete parameters and the
  queue's configuration hash are checked against the recorded declaration (`:1020` onward).
  The hash expression agrees with `orchestrate/semantic.py:queue_agent`; it is not a new identity
  definition. A mismatched alias does not become compatible merely because its display name is
  recognized.
- Required-unit and configuration transfer have finite admission limits. The correction uses
  existing relational selection and the existing coverage summary rather than add a cache,
  parallel coverage store or scheduler.

This directly addresses the original counterexample: a complete Opus-owned scope cannot hide
a missing or incomplete general-owned required scope, while a genuinely complete general-only
population can establish coverage. The latter matters: conservatively returning unknown for
every general-only request would preserve fidelity but leave the supported composition unfinished.

## Historical meaning and continuation behavior

`coverage_contract.py:18` retains the exact recipe3 interpretation, including its historical
Opus-only universe and `semantic-7` protocol. `required_coverage` dispatches that archive through
the historical branch rather than applying recipe4 defaults. An unrecognized or altered recipe
refuses. Maintaining this deliberate reader branch is historical compatibility, not a second
current producer authority.

No cursor codec or walk meaning changes in this delta. Named-query implementation custody
already includes `semantic/query.py` and `semantic/coverage_contract.py`; the inspected root
addition of `methods/llm/producer.py` also binds the newly consumed shared producer declaration.
Existing named-query compatibility checks and token validation therefore prevent a previously
issued token from silently crossing to a changed implementation binding. Coverage-detail tokens
continue to bind release, realization/revision, run/cut, query/answer selection and the selected
scope digest. A recipe is immutable within its producing release; recipe4 is not substituted
inside a retained recipe3 release. Final regeneration and actual transport applicability remain
the coordinator's obligations.

## Independent expectations and evidence limits

`tests/semantic/test_configured_coverage.py` contains independent expectations for general-only
membership and complete coverage, mixed missing/partial/failed/unanalysed general coverage,
parameters/version/hash/configuration-name/unit drift, unsupported or missing producer declarations,
and historical recipe3/unknown-recipe handling. The first two cases exercise the actual empty
named-answer consumer's absent/unknown classification; coverage-detail transport is explicitly
controlled and is not qualified by those cases. The configuration-hash fixture uses an independently
encoded queue tuple. These are discriminating expectations rather than copies of the production
required-population calculation.

The coordinator and implementing worker report **passed: 20 focused cases**, comprising the 14
new Core-SQL cases and six existing reader-contract cases. This reviewer inspected their source
but did not rerun them. They use SQLite Core SQL and controlled setup, so they establish no native
PostgreSQL installation/admission, actual provider or complete transport result. They do not
replace the final AC14 union.

## Revised judgments for the corrected boundary

| Judgment/gate | Revised verdict | Basis |
|---|---|---|
| A1 Localize change | satisfied | Current producer compatibility has one owner; coverage derives and validates its recorded binding |
| A2 Explicit domain meaning | satisfied | Required coverage is governed by the configured producer/unit contract; unknown and absent remain distinct |
| A3 Composition | satisfied | Both existing compatible producer bindings reach the same required-unit and answer semantics |
| G1 Authority | pass | The independent current producer selector is removed; historical recipe3 retains its original scope |
| G2 Semantic fidelity | pass | General-owned required units are retained and incompatible bindings cannot establish coverage |
| G6 Transformation/reuse | pass | Effective-origin and archived-recipe interpretations are explicit; incompatible reuse remains refused |
| CI-G1 Fidelity | pass | Missing/incomplete general coverage cannot become absence through the original producer-omission path |

The F01-related FP-01/02/03/04 and DP-01/08/24 violations are corrected for the reviewed scenario.
Other judgments and evidence limits from the original review are unchanged. No new rule impact
or directly related defect was established by this delta.

The coordinator can record F01's source-level correction with this separately attributed
assessment and the bounded test receipt. The original diagnosis remains recoverable and accurate.
This removes the original assembled review's named architectural revision reason; it does not
declare all AC packages complete, freeze native102, qualify the enclosing system or resume M1.
