# Semantic contracts and comparison policies

**Status:** Planned; UM-01/UM-02 are not implemented by this document. **Created:** 2026-11-01.
**Target:** Proposed. Source review at `370f0643`: [R01](../../design_review/reviews/design_review_unified-domain-model_2026-11-01.md#R01)
and [R03](../../design_review/reviews/design_review_unified-domain-model_2026-11-01.md#R03), retaining
DA-001 and DA-027 as diagnostic identities. The [coordinator](../unified-domain-model_2026-11-01.md)
owns package state, source disposition and combined acceptance. Existing plans are unchanged.

**Planning snapshot:** committed source/review `370f0643` plus the specifically inspected dirty
PDF/model/native seams. The PDF series is still completing and may change those seams. This plan
does not continuously absorb that work or own its acceptance. A later update will reconcile the
then-current PDF snapshot as a discrete step before dependent execution.

## Foundation and selected meaning

The inspected semantic release already binds effective classes/properties, operation contracts,
state transitions, implementations and effect profiles. Its model is not merely descriptive.
Current comparison code filters qualification properties by `key_role`, then independently reads
`cs:qualifiers` and `cs:identity_qualifiers` to form comparison groups. Current invariant definitions
name a failure code and implementation, but the relation between that code and native diagnostic
behavior needs a complete contract. Neither observation proves current stored facts are corrupt.

Reconcile the execution baseline before implementation, particularly concurrent PDF contract and
native-validation changes. Preserve qualified occurrence identity, source evidence, canonical exact
values, native enforcement and independently authored validation expectations.

## UM-01 — Checked comparison projection

The effective release owns a named, versioned projection for each comparison policy. It identifies
qualification properties as comparison context, compared meaning or evidence-only information.
Those are roles of this operation; they do not redefine the full fact key. The compiled projection
contains resolved property identities and its source/policy revision, not annotation strings for
later consumers to interpret. Each selected property must belong to the effective qualification
class. Overlap, unknown references and prohibited cross-scope references fail preparation with a
located diagnostic before a candidate release can be admitted.

Preserve the existing statistics behavior while translating it into this contract: provenance stays
attached to source occurrences; the current qualifier-minus-identity-qualifier selection identifies
compared meaning; the remaining meaningful qualification defines comparison context. Explicitly
resolve every current list member and reject a contradictory declaration. A missing authored list
uses the current behavior only through an explicit compiler-versioned default recorded in the
product. This is a compatibility translation, not a new default interpretation by a consumer.

The scientific decision owner consumes the compiled projection to produce group keys and compared
values. Fact identity continues through its existing key-role/canonical-meaning owner. Evaluation,
impact explanation and serialized policy descriptions consume the same projection whenever they
need that operation's grouping semantics; they must not infer it from fact-key shape. Different
consumer policies may have different declared projections; there is no single universal equality.

### Library realization and remaining domain responsibility

| Mechanism | Role and condition |
|---|---|
| LinkML/runtime 1.12.1 `SchemaView.class_induced_slots`, `induced_slot` | Resolve contextual inherited definitions and property references once during release preparation. Keep closed import maps, duplicate/prefix refusal and conjunctive bounds; effective-definition materialization is not automatically equivalent to current preparation. |
| Existing normalized release products and typed domain functions | Store the checked projection and implement key/value projection. Specialized comparison algorithms remain functions; no generic rule language is introduced. |
| Valuesets 0.4.2 plus existing OAK/Term Validator snapshots | Preserve vocabulary meanings and memberships as pinned inputs. `RichEnum.from_meaning` is lookup, not scientific equivalence; generated enums are not a replacement for full metadata snapshots. |

See [semantic applicability](../../library_leverage/libraries/unified-model-semantics_2026-11-01.md),
`semantic/prepare.py:985–1006` and `semantic/domain_operations.py:2589–2603` at the review baseline.
Exact source research is Interface-checked; this projection's implementation remains Proposed.

### Delivery and acceptance

UM-01 consumes existing effective definitions and release/archive extension support. It delivers
compiled comparison products, migrated scientific grouping consumers, archive/reload behavior and
explicit rejection of incompatible products. A new product version changes interpretation identity;
do not reinterpret an old release or edit frozen products. Retire runtime annotation parsing only
after every maintained comparison consumer has adopted the product.

Use independently specified examples: two ownership facts with distinct validity or attribution
retain different fact IDs while a declared policy can place them in the same comparison group;
a policy requiring equal intervals keeps them apart. A duplicate assertion retains its occurrence
identity. A nonexistent qualifier and a reference belonging to another scope fail preparation.
Compare current statistics behavior before/after using independent expected groups, not expected
keys generated by the new projection itself. Archive reload must produce the same meaning.

## UM-02 — Observable invariant failure contract

Select `failure_code` as an observable **domain-boundary** contract for required invariants. Native
message prose remains diagnostic detail; it is not the API identifier. Bind each required invariant
to a trusted implementation/version, enforcement scope, relevant operation and a structured mapping
from its native failure identity to the domain code. Scope distinguishes construction, accepted
state, cross-record/context and concurrent transition. Native guards remain authoritative for
concurrent state and independent clients; preflight and Pydantic do not authorize later effects.

The mapping must use an unambiguous native diagnostic identity: SQLSTATE plus named constraint or
explicit structured guard detail where necessary. SQLSTATE alone is insufficient when several
invariants share it. When current native code lacks that identity, generate a forward implementation
change through the native-authoring owner before claiming this invariant supports the new contract.
Never infer a code by matching free-form English messages. Preserve unmapped database errors with
their cause and effect knowledge; do not fabricate a known invariant failure.

Preparation resolves invariant subjects/relationships and the enforcing binding. Admission verifies
that required implementation capabilities and native products are actually supported. A descriptive
invariant may remain descriptive only when no supported operation relies on it as enforcement;
that distinction is explicit in the normalized contract. The model must not advertise an enforced
requirement merely because its reference resolves.

### Concrete composition

LinkML effective definitions supply invariant and operation structure; the existing finite trusted
implementation catalog supplies qualified guard identities. Existing native SQLSTATE/structured
failure classification maps the actual execution to the domain outcome. Pydantic-generated error
boundaries validate the result envelope. RDFLib/pySHACL conformance supplies separate graph-scoped
results, never the authorization for an atomic database transition. Native semantic correctness
still needs independent tests: matching body digests and reconstructed metadata cannot prove it.

UM-02 consumes the existing implementation/effect admission foundation. Its early deliverable is the
stable invariant/error-binding contract used by typed API generation and actionable validation.
Its enforcing deliverable additionally depends on the actual new native products from
[native authoring](native-authoring-and-evolution.md). This is a contract/enforcement dependency,
not a cycle requiring all native work before any contract preparation.

### Acceptance and execution investigations

Exercise a bad object, a cross-record violation, a concurrent stale-owner failure and an unrelated
infrastructure failure through actual domain operations. Assert independent expected codes and
native cause retention. Required unsupported guard versions fail admission before effects; an
unmapped failure remains distinct. Structured errors must survive CLI/MCP presentation (O03).

**Investigation UM-I01:** identify the exact supported native diagnostic fields for the initial
required invariant families. Source inspection may settle a binding; otherwise use a focused native
failure case on an owned test database. The result supplies the mapping and forward changes required
for UM-02 enforcement closure. It does not reopen the choice of domain-level observable codes.

The [typed operations](typed-domain-operations.md) consumer needs the early stable error contract;
[operation explanations](operation-explanations-semantic-impact-and-validation.md) must distinguish declared,
implemented, unavailable and unresolved enforcement. Package/local qualification is not acceptance
of every invariant or of the assembled series. No tests or probes were run while authoring this plan.
