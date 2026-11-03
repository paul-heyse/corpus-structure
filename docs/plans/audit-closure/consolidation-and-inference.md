# Consolidation decisions, attribution and inference

**Accepted planning direction, 2026-11-03; implementation and qualification Proposed.**
This companion develops AC03, AC04 and AC09 of the
[audit-closure coordinator](../audit-closure_2026-11-03.md). It owns detailed intended contracts;
the coordinator owns every package status and new-review-work disposition. Source DA disposition
remains with its existing owner, linked through the coordinator rather than copied here.
The whole series completes before the M1 plan update and subsequent M1 resumption.

The operator accepted RC01–RC12 on 2026-11-03; no reapproval is required. AC00 schedules the
appropriate ADR/architectural-owner changes before dependent meaning changes. This plan applies
none of those decisions to production and does not change native99 or frozen migration bodies.

## Basis and focused foundation assessment

Consume the [principal review](../../design_review/reviews/design_review_audit-closure-target_2026-11-03.md)
at `fd4ea601`, its [semantic contracts](../../design_review/reviews/audit-closure-target/semantic-contracts.md)
and [runtime boundaries](../../design_review/reviews/audit-closure-target/runtime-boundaries.md).
Plan source inspection is HEAD `fd4ea601` plus concurrent dirty M1 work, 2026-11-03. This focused
foundation assessment uses core/template 3.3, heuristics 1.0, code-intelligence 1.4 and test-assessment
1.2, without opening a new audit or asserting enclosing architectural conformance.
Architecture remains owned by [D1](../../design/D1-knowledge-representation.md),
[D2](../../design/D2-schema-and-guidelines.md) and
[D5](../../design/D5-consolidation-identity-confidence.md) and their decision lines.
Paths below omit `python/corpus-structure/src/corpus_structure/` unless stated otherwise.

**Implemented baseline, inspected 2026-11-03:** `semantic/domain_operations.py:824–1058` assigns
safe source-qualified identities, preserves local/known exclusion endpoints, refuses incompatible
declared keys, and avoids choosing between ambiguous known anchors. It returns mappings, extra
fields and parsed payloads without typed resolution decisions. Keep those safety properties.
`semantic/types.py:332,375` uses Python `str.casefold`; native identity/validation SQL uses
PostgreSQL `casefold(... COLLATE pg_catalog.pg_unicode_fast)`. No divergence was established.

`model/semantic/agent.yaml:8` gives attributes predicate/value alone. The source projector borrows
first eligible claim evidence via `setdefault` and emits asserted/positive entity fields
(`domain_operations.py:1507–1620`), including generated IDs. `semantic/consolidation.py:258` already
retains occurrences/support separately from exact facts. `serve/read.py` exposes occurrence values
but also makes display decisions; do not erase either scientific or original source distinctions.

Candidate rules rebuild premise and given-by-others collections per candidate at
`domain_operations.py:3253`. Scientific preparation already runs outside publication at
`:2058–2091`; that is a preserved foundation, not new work. Inference already uses a private
PostgreSQL workspace, conflict-aware conclusion deduplication and finite direct proofs after the
common fixed point (`semantic/inference.py:129–294`). `consolidate_cut` calls derive within source,
proof and result publication's atomic transaction (`domain_operations.py:2105–2150`).

Dirty M1 record/report-presence/native101 work is separate and does not remove these obligations.
Reconcile current shared publication/model bytes before implementation; preserve source-record
admission, terminal report absence, evaluator address ABI and independently owned quality repairs.

## AC03 — Explicit identity decisions and bounded Unicode compatibility

**Correspondence:** DA-007/009. AC00 supplies release/product and D1/D5 authority routes where
meaning changes; AC01 supplies effective identity/case bindings, not a second identity algorithm.

Return assigned identities together with compact typed per-entity decisions. A decision records
source/local identity, assigned identity, basis (declared_key/global_label/source_local), outcome
(resolved/ambiguous_anchor/incomplete_key/ungrounded_cycle), relevant candidate identities,
key/label policy, dependency references and reason. Source-local is a legitimate policy where
declared, not automatically a failed resolution. A usable provisional fallback must not claim
global resolution. Retain refusal for bridging incompatible declared identities and cannot-link
violations; typed decisions do not authorize speculative merge.

Persist the compact decisions as part of the cut's coherent projection with its release, input
scope and operation identity. Reuse the publication/report relationship rather than creating an
event stream or copying source evidence bodies. Stable-local-reference consumers use assigned
IDs; global grouping/explanation consumers inspect outcome and basis. Keep known endpoint and
packet-local endpoint meaning explicit at the boundary, even when both serialize as strings.

Migrate `_resolve_entities`, `_project_cut`, entity/reference rewriting, compiled-position
traversal, publication products and query/explanation/evaluator consumers that need resolution
standing. Preserve collision checks and revalidation after actual mutation. Follow the existing
reference-position owner instead of adding a recursive visitor. AC10 presents identity standing;
AC11 exposes the compact decision's evidence/source links within the same pin. Neither package
may infer global resolution from successful dictionary lookup.

**I01 — bounded runtime-pair compatibility qualification is required.** Declare Unicode default
case folding, with no implicit normalization step, for identity properties selecting that policy.
Bind the effective Python/runtime Unicode and PostgreSQL/collation compatibility determinants
to producing/admitting artifacts. Qualify the exact supported pair before claiming its compatibility;
refuse unqualified pairs and requalify when determinants change. Do not substitute lowercase or
claim universal parity from a handful of examples.

Qualification combines the relevant folding mappings for the declared Unicode/runtime pair with
independently specified identity cases, including non-ASCII expansions, preserved-case properties,
composed/decomposed strings and explicit no-normalization behavior. State the qualified domain and
limits; any unexamined broader pair remains unsupported. If mapping-level comparison leaves a
material gap, narrow the supported compatibility claim or investigate that gap before admission.
Examples challenge integration; they do not prove the entire mapping relation. Retain independent
native recomputation at its trust boundary. No bespoke Unicode engine, per-fact parity check or
universal proof system is selected.

The existing mechanisms are Python **3.14.10** `str.casefold` and PostgreSQL **18**
`casefold(text COLLATE pg_catalog.pg_unicode_fast)`. Sources carried from the review:
[Python 3.14 case folding](https://docs.python.org/3.14/library/stdtypes.html#str.casefold) and
[PostgreSQL 18 string functions](https://www.postgresql.org/docs/18/functions-string.html).
These document the mechanisms, not established parity for this deployment. AC13 binds the
admitted runtime/deployment route; AC03 owns I01's compatibility cases and evidence.

**Acceptance:** independently specify ambiguous multiple anchors, incomplete declared keys,
ungrounded cycles, legitimate source-local policy, local/known endpoints and cannot-link cases.
Assert assigned IDs and decision meaning independently, with reordered input. Include native
unqualified-pair refusal and the bounded I01 compatibility result. No algorithm change to Unicode
folding is justified solely by DA-009; reopen on demonstrated mismatch or changed determinants.

## AC04 — Attribute-specific support and three representative policies

**Correspondence:** DA-044. RC01 and RC03 are accepted, 2026-11-03. AC00 schedules D1/D2/D5
and applicable §B1/§B5 authority changes before activating the new shape and view meaning.

Replace implicit attribution with a released SourceAttributeAssertion carrying predicate, value,
qualification, source-admissible establishment and located evidence. An explicit assertion reference
is acceptable only when its contract establishes this attribute, not merely another claim about
the same entity. Retain multiple supports and qualifications. AgentEntity.label remains display
metadata unless separately supported; generated IDs are structural assignments with operation/input
lineage and must not become document-stated occurrences by borrowing evidence.

Change the authored attribute shape, stored/located adapters, producer schemas and guidelines,
packet/completion/native validation, projection and support/evidence publication together.
AC01 supplies source-admissible establishment and released role/display products. Reuse the
existing typed evidence-placement/source-custody boundary; do not invent offsets or copy support
from the first eligible claim. Unsupported older attributes remain metadata or explicitly
ungrounded. They cannot be promoted silently to satisfy graph constraints. Attributed entity
declarations may exist without accepted scientific claim evidence.

The representative decisions have separate owned contracts:

| Decision | Selected policy and output |
|---|---|
| One stored representation of an exact fact | Declared total order on representation IDs; no source-quality or scientific preference claim |
| Display label/value | AC01's ordered class-bound display policy, selected property/value/source identity and retained alternatives |
| Scientific equivalent-fact view | Released deterministic policy over eligible accepted component members, stable fact-ID tie break, retained component membership and comparison evidence |

Select minimum stable fact ID as the initial scientific-view representative where no scientific
quality preference is required; declare that meaning explicitly in the released policy. It provides
permutation stability, not better science. Keep each exact fact identity, original occurrence and
qualified support. A nonrepresentative equivalent accepted fact is not rejected. Proposition-set
consumers use the explicit representative view to avoid duplicate counting; source-report consumers
retain original values and occurrence support.

Implement representative selection with existing exact-fact/equivalence/selection products and
released policy binding, not a new generic quality ranker. Migrate scientific policy selection,
display/query/export and evaluation paths that consume propositions alongside their outputs.
Coordinate AC10 standing so accepted, assessed, representative and returned are never synonyms.
If scientific quality preference becomes an actual requirement, change its declared policy and
evidence inputs explicitly; do not infer it from source order or storage minima.

AC13 supplies changed generated/native shapes and new release products through forward-only
installation; preserve archived original bytes, native99 and frozen predecessors. An intermediate
state can support the new attribute contract before all representative readers move, but no reader
may consume new fields under old defaults. Refuse incompatible consumers until their versioned
contract is available; universal historical translation is not required.

**Acceptance:** reorder source claims/attributes while independently asserting each attribute's
own qualifications and support. Include two supports, contradictory qualifiers, unsupported
metadata, a display-only label and a generated ID. Verify native refusal of fabricated support.
Separately assert exact-storage minimum, class display policy and scientific representative over
accepted equivalence components; alternate members remain accepted and source occurrences survive.

## AC09 — Shared candidate indexes and delta inference inside atomic publication

**Correspondence:** DA-043. AC09 changes physical work, preserving released rule meaning,
qualification context, direct witness multiplicity and publication/replay guarantees.
Prerequisites are the usable AC01 behavior-membership slice and AC02's rule-view contract where
consumed; AC05 reason variants integrate affected failures. AC03/04 changes affecting candidate
meaning must be incorporated before AC09's final applicability evidence, without requiring their
whole documents as start barriers.

Prepare statement, role, occurrence and symbol indexes once for the pinned candidate cut.
Same-statement premises and global assumptions remain eligible; the current occurrence excludes
itself. Symbol ownership is occurrence-sensitive: a symbol shared by two occurrences remains
available from the other occurrence after self-exclusion. Use indexed memberships/counts rather
than subtracting a global set in a way that loses duplicate ownership. Candidate views consume
the prepared indexes; retire per-candidate whole-candidate scans once all actual rule consumers move.

Where a rule asks membership, expose an owned membership operation using those indexes. Where
the released rule genuinely consumes a full materialized premise/symbol universe, preserve that
universe and its ordering/cardinality meaning. Do not narrow it for speed or silently substitute
a predicate for an authored collection. Any incompatible rule-contract change uses AC00/AC02's
version route rather than hiding behind an optimization label.

Select frontier/delta inference in the existing PostgreSQL/SQLAlchemy workspace. Maintain accumulated
qualified conclusions and the newly inserted frontier. Apply unary subproperty/inverse/symmetric
rules to frontier facts. For transitivity combine new/accumulated and accumulated/new premises,
deduplicate overlap and insert only newly admitted conclusions. All admitted rule groups participate
in one common fixed point; terminate on an empty frontier. Preserve canonical context and stable
qualification-representation selection regardless of insertion order.

After the fixed point, materialize every required distinct finite direct witness, with rule ID/version,
ordered premises and context. Do not enumerate recursive proof paths, collapse distinct direct
proofs merely because the conclusion matches, or replace qualified rules with reachability.
Necessary pair comparisons remain work required by the declared semantics.

Selected pins and APIs are SQLAlchemy **2.1.6** Core `select`, aliases/joins,
`insert(...).from_select(...)`, PostgreSQL dialect `insert(...).on_conflict_do_nothing().returning(...)`,
and the existing temporary workspace begin/end native calls. Returned insertions identify the next
frontier without rereading the full accumulated relation for every rule. Keep current transaction
error cleanup: an aborted PostgreSQL transaction rolls back its workspace; do not mask the original
failure by issuing cleanup SQL into that aborted transaction. Sources are the inspected current
`semantic/inference.py:129–294` and
[SQLAlchemy 2.1.6 PostgreSQL implementation](https://github.com/sqlalchemy/sqlalchemy/blob/rel_2_1_6/lib/sqlalchemy/dialects/postgresql/dml.py).
No dependency move or new inference backend is selected.

Inference initially stays **inside existing atomic publication**. Preserve source receipt, proof
publication and run-result visibility in one transaction, native revision/attempt fences, rollback,
exact replay and workspace lifetime. Scientific candidate preparation remains outside as already
implemented. Moving inference outside would require an immutable prospective-input contract plus
source/output revision fencing; that extra handoff is not necessary for the demonstrated correction.

DuckDB **2.0.0** `USING KEY` is an unselected alternative, not an execution prerequisite:
[recursive keyed state](https://duckdb.org/docs/current/sql/query_syntax/with.html).
Replacing keyed payloads does not establish preservation of qualified facts or witness multiplicity.
NetworkX/plain graph closure likewise does not supply the complete qualified/proof contract.
Keeping full accumulated rescans is simpler locally but retains repeated work as candidates/closure
grow; PostgreSQL delta state reuses the adopted workspace and transaction route with less new
runtime/operator machinery. Performance benefits remain Proposed and unmeasured.

**Acceptance:** independently specified cycles, self-loops, reconvergence, mutually enabling rule
groups, duplicate conclusions/distinct direct witnesses, different qualification contexts and
permutation-stable output. Candidate cases cover same-statement/global premises, self-exclusion and
shared symbol ownership. Native integration retains atomic rollback on inference failure and
coherent exact replay after uncertain publication. A bounded correct closure establishes semantic
behavior; quantitative speed/capacity claims require separate measurements before being made.

## Preservation, boundaries and verification ownership

DA-004 retains typed validation followed by governed mutable/serializable mappings, centralized
compiled reference positions and revalidation after actual mutation. Reopen only for a concrete
consumer loss or demonstrated unchanged-premise repeated work. DA-027 retains declarations,
compiler diagnostics and native guards; inspect/test changed invariants without a universal
correspondence registry or SHACL pass. DA-046/048 retain reusable mathematical types and explicit
single canonical-domain production selection; AC01 moves actual pack-specific behavior. Reopen
simultaneous multi-pack production only when a real consumer requires its complete contract.

AC10 consumes resolution/representative standing; AC11 consumes pinned decision/evidence links
and bounded walks, without turning them into a second consolidation authority. AC13 owns combined
release/native adoption and current D2 guidance; AC14 owns complete-series qualification and final
source/context union. Each package includes its producers, native/generated forms and real consumers
before local completion; agreement on a shape alone is not integrated behavior.

During implementation run targeted functional checks appropriate to changed contracts. Pure
identity/projection/index tests need no unrelated database; native trust/publication cases require
real PostgreSQL. Expected meanings must be independent of the projection/algorithm under test.
Retain failed/interrupted receipts; no integrated campaign after a slice and no native99/M1
qualification promotion. Plan-authoring product tests, providers, database operations and runtime
qualification are **not_run**; this document authorizes no product edits.
