# Evaluation split-decision provenance

**Accepted target; source integrated; complete qualification open · 2026-11-03.** This companion defines AC12 of the
[audit-closure coordinator](../audit-closure_2026-11-03.md), which alone owns new-series package
state, review-obligation conclusions and completion. Existing plans retain scheduled DA
dispositions; this companion neither transfers nor duplicates them. It consumes DA-037 in the
[principal review](../../design_review/reviews/design_review_audit-closure-target_2026-11-03.md)
at `fd4ea601` and its [consumer/evaluation contracts](../../design_review/reviews/audit-closure-target/consumer-contracts.md),
read together with the semantic/runtime contributions. The original source baseline was
`fd4ea601` plus identified concurrent M1 work; the current implementation baseline is `75db93e1`.
Core3.3, heuristics1.0, code-intelligence1.4 and test-assessment1.2 guide this bounded assessment.
ADR-0054 realizes accepted RC10 at the owners; qualification remains separately scoped below.

## Purpose and baseline

**Implemented source, inspected 2026-11-03 at `75db93e1`; assembled qualification open.**
D3/D7/D8 and ADR-0054 own protected split effects and their consumers.
`evaluate/split_decisions.py`, `evaluate/semantic.py` and native evaluator operations now preserve
frozen policy, actual seed and origin, ordered population, prior assignments, assignment basis,
results and reasons. Exact replay differs from conflicting intent; historical rows retain explicit
legacy-unavailable provenance without invented seeds or reasons. Native102 carries the protected
forward transition, with evaluator-only decision access and immutable predecessor data.

The pure `evaluate/split.py:assign` rule retains source-URI grouping, forced/reserved reasons and
additive assignment: later registered pages do not reshuffle assigned URIs. Invocation population
and prior assignments are necessary to reproduce that behavior. Chapter inputs admit exact string,
null or absence; other JSON chapter types refuse at new-decision preparation, including assignment
requested through reference creation. This does not narrow general document metadata.

M1 origin partitions, reference independence and statistical sampling remain separate meanings.
The target below is implemented at source with bounded native controls; AC14 still accounts for
complete assembled applicability. Paths below are relative to
`python/corpus-structure/src/corpus_structure/`.

## Target decision contract

**Adopted refinement I01:** reference creation uses the exact execution-bound operational subset,
including nondefault supplied schemas, rather than reconstructing it from the domain namespace.
Keep split-decision provenance distinct from M1 origin partitions and final sampling. Remaining
native/CLI consumers must preserve legacy-unavailable meaning and actual seed-override origin.


Use one versioned evaluator-owned operation with frozen inputs. These conceptual shapes state
required meaning; existing released/Pydantic/native products should carry it without a new service
or generic provenance registry.

```text
SplitDecisionIntent = {
  protocol/algorithm version, project, producing release,
  frozen effective split policy (including forced/reserved reasons),
  actual seed and its override/default origin,
  source population snapshot: document/source identities + grouping inputs,
  prior assignments relevant to the decision,
  expected immutable assignment basis/revision or equivalent concurrency fence,
  intended source assignments: split + actual reason + decision input references
}

SplitDecisionReceipt = {
  immutable decision identity + canonical intent digest,
  protected operation/version and frozen input references,
  source assignment references + split/reason,
  effect outcome: committed | exact_replay
}

AssignmentProvenance =
  recorded {decision reference, per-source reason/input references}
  | legacy_unavailable {original source/split, explicit limitation}
```

Freeze the effective policy after binding its producing release, including explicit config and
seed overrides. The operation consumes that value/snapshot, not a hidden lookup of a mutable
project default during replay. Record the actual invocation seed even for a forced/reserved
assignment whose own algorithm branch does not use hashing; its per-assignment reason says that
distinction. Population evidence includes the chapter values and URI/document membership actually
used, plus the previous assignments/unassigned subset that affect additive assignment. Store
shared immutable metadata once and reference it per assignment; hashes alone without retrievable
inputs are insufficient for replay explanation. Existing protected immutable input storage can
be reused where its semantics/lifetime fit; no per-document policy object is required.

Prepare the pure decision once against the frozen selection, validate it through the operation's
released/native admission and publish the shared decision with its assignments atomically. The
native boundary must reject unsupported operation/release, cross-project sources, conflicting
source assignments and incomplete/mismatched decision membership. Preserve evaluator privileges,
immutability guards, native cross-row constraints and release admission. A client supplying a
reason string is not by itself authority that those inputs produced that split. Reuse the current
assignment semantics for protected validation/admission; independently authored cases assess the
algorithm rather than treating its own output as the expected answer.

The assignment basis needs a short transaction/concurrency route: preserve the read population and
prior-assignment basis through protected publication, or fence and refuse a changed basis before
effects. Concurrent exact intentions may replay; contradictory intentions cannot both commit.
The implementation chooses the smallest existing locking/fencing mechanism that establishes this
property and documents it in the owning operation. No long-lived transaction around reference
authoring or evaluation, and no durable assignment workflow scheduler, is needed.

The canonical intent covers the frozen inputs and intended outputs. The exact repeated intention
returns the original receipt without rewriting rows. A different intention cannot acquire the
old decision identity simply because its resulting split label happens to agree. Existing
assignments remain immutable; a different decision for an assigned source refuses or enters an
explicitly authorized migration that preserves original provenance. Ordinary additive assignment
uses a new decision for new sources with references to the old assignments; it never attributes
the new seed/population to those old assignments.

## AC12 implementation and migration scope

AC12 uses the existing evaluator's released operation/read contracts, adopting affected AC01–05
products or AC06 owned reads where their actual interfaces change; it does not wait for those
whole packages or for AC11 walk execution. AC00 routes accepted RC10 into
D7/D3/D8 and the governing decision before activation. AC13 integrates the released operation,
native descriptors and installed release coherently; it does not postpone AC12 consumer changes.

Extend the executable model/physical declarations and existing protected evaluator operation.
Add a forward Alembic/native migration with its frozen SQL/admission descriptors, preserving all
predecessor bodies, native catalog/role checks and immutable source/split rows. The migration can
add a shared decision relation with assignment references or an equivalent compact representation;
physical granularity follows actual reuse and constraint needs. The semantic boundary does not
demand a table for every input category. Preserve useful model-derived native enforcement; do not
substitute a Python-only write path or introduce blanket new triggers/certificates.

Update `evaluate/semantic.py:split_documents` and its pure wrapper to pass actual reason/seed,
frozen policy/population/basis and intended results to the protected operation. Return a receipt
that distinguishes replay from a new effect. Move `create_reference_set` and all actual API/CLI
consumers in the same package, including `cli/golden.py` split/create/status and the protected
M1 record-reference prerequisite path. Status reports provenance availability without exposing
reference answers. New deterministic/reproducible claims require recorded provenance; historical
availability remains visible to callers instead of being inferred from today's config.

Historical rows keep their original labels and grades. If original seeds/reasons/populations are
not recoverable from existing immutable evidence, mark them `legacy_unavailable`; do not infer a
seed from the current pack, fabricate a `hash` reason or retroactively attach a fresh decision.
Existing consumers may continue using their known immutable split under an explicit legacy
limitation. An operation requiring reproducible decision provenance refuses that claim for legacy
rows. Any later historical recovery requires independently retained source evidence and a separately
declared provenance correction, not silent backfill. No historical regrading is part of AC12.

**Implementation contract resolution (2026-11-03):** new protected decisions accept exact string,
null or absent chapter metadata, matching `SplitDocument.chapter`; null and empty strings retain
the existing common group. Python and native admission explicitly refuse other JSON chapter
types. This narrows the former permissive Python `str()` conversion: it does not silently adopt
PostgreSQL's different boolean/container spellings or pretend arbitrary JSON has a chapter meaning.
General document metadata stays unrestricted. Existing assignments and grades remain usable under
their recorded provenance; a new split invocation (including reference creation that requests one)
with unsupported historical chapter metadata refuses rather than rewriting or guessing its group.

Keep `dev/test/reserved` separate from M1 origin/training/qualification partitions, source-origin
groups and fixed reference-sampling metadata. Carry existing sample procedure/version/seed/frame
metadata forward unchanged; the split receipt references its own population. Source/reference
isolation and blind automated A/B/C grading remain intact. A split provenance defect is not by
itself proof of leakage, credible origin independence or representative sampling.

## Execution fit and retained mechanisms

Reuse the pure hash/group assignment, shared frozen invocation metadata and one atomic protected
effect instead of issuing independent policy snapshots per document. Registered document growth
requires reading the selected project population and relevant prior assignments because those
are semantic inputs; do not reduce that universe to the output's newly assigned rows. Set-shaped
selection and batch publication avoid per-source policy/release reloads, while assignment rows
remain independently addressable by immutable source identity. The ordinary one-operator workload
does not justify a new scheduler, general replay service or another evaluation database.

Carry forward SQLAlchemy **2.1.6** Core `select`/`where`/joins and transaction ownership,
PostgreSQL **18** constraints/protected routines and Alembic **1.20.1** forward migrations.
The review's library research remains **Interface-checked**; current source composition is
**Implemented** at the coordinator's bounded scope, with complete qualification open.
Precise sources: [SQLAlchemy 2.1.6 connection/transaction source](https://github.com/sqlalchemy/sqlalchemy/blob/rel_2_1_6/doc/build/core/connections.rst),
[PostgreSQL 18 transaction modes](https://www.postgresql.org/docs/18/sql-set-transaction.html),
[Alembic autogenerate limitations](https://alembic.sqlalchemy.org/en/latest/autogenerate.html), and
the [runtime review's native/frozen migration constraints](../../design_review/reviews/audit-closure-target/runtime-boundaries.md).
Retain model-derived/frozen descriptors rather than assuming generic autogeneration discovers all
CHECK semantics. No pin changes or fresh library research are needed to author this target.

Replacing the split algorithm, merging M1 origins with dev/test, keeping only current CLI seed
output or backfilling guessed provenance do not solve the actual boundary defect. Reopen the
algorithm only for a separate requirement such as a changed leakage grouping policy; that would
need a versioned decision and explicit immutable-data migration, not an AC12 implementation detail.
Quantitative performance/capacity improvements remain unmeasured.

## Completion evidence

AC12 owns focused tests of assignment/effect/consumer behavior; AC14 owns assembled final-source
qualification and complete evidence union. Start with independent small chapter/URI expectations
and known hash-order cases in `tests/evaluate/golden/test_split.py`; include a seed override,
forced/reserved precedence/conflict, same URI/new bytes, shuffled input and incremental registration.
Independently inspect the stored actual seed/reason/policy/population, not just the CLI return value
or an expected receipt produced by the same serialization under test.

Native cases must establish atomic decision-plus-assignment publication, exact replay, changed
intent with an unchanged output label, conflicting existing assignment, changed population/basis,
concurrent intents and rollback without orphan decision/assignment rows. Test real evaluator roles
and protected native routines; a mocked connection does not establish permissions or concurrency.
Exercise forward installation on historical rows and verify legacy-unavailable status, unchanged
split/grade identities and preserved immutable guards/frozen predecessor compatibility.

Exercise actual golden split/create/status and direct APIs, ordinary reference creation,
`native_references.sql` and M1 `record_references.sql` prerequisites against populated data.
Verify distinct origin/sample metadata and reference-isolation controls remain intact. Future
test locations include existing `tests/semantic/test_evaluation_boundaries.py`,
`test_reference_evaluation_native.py` and `tests/evaluate/test_record_references_native.py` plus
focused CLI fixtures. Their current presence is a source lead, not a passing result for the new
contract. Preserve failed/interrupted receipts and qualify actual external journeys at the
integrated endpoint. No test, database migration or probe was run for this documentation-only
contribution.
