---
id: ADR-0122
title: Semantic support uses set-wise live validity and acquisition evidence
status: accepted
date: 2026-11-17
supersedes: [ADR-0093]
superseded-by: null
design: [§B1, §B4, §B5]
evidence: Proposed
revisit: A supported binding or live trust premise cannot be preserved by the recorded closure and scoped epoch protocol.
---

## Context

PE-RC02 deliberately changes how current support and ordered trust epochs are evaluated.
The operator accepted this target and its detailed execution design. ADR-0093's clauses
"Cross-release inputs require ... current support" and "Trust publication/revocation shares
ordered scoped epoch authority" retain their meaning with the realization below. This record
restates all its decisions; acceptance does not establish implementation or qualification.

## Options

1. Recursive per-candidate validity and reconstructed closure on every read. This retains
   current behavior but repeats shared immutable and graph work across candidates and calls.
2. A maintained transitive invalidation cache. This duplicates substitution semantics and puts
   reverse traversal under revocation locks; boundary-relative facts still need evaluation.
3. Statement-local set validity and immutable acquisition evidence with live premise checks.
   Selected: one meaning owner and distinct lifetimes for immutable correspondence, mutable
   premises and caller authority, without a second invalidation service.

## Decision

A semantic product is kind contract plus immutable subject/context plus canonical body.
Original source occurrences, role/order/multiplicity and local member qualification remain
exact. Derivations retain actual execution, runtime and consumed support. Equal bytes do not
establish source equivalence, trust or independent votes.

Native admission validates semantic request and full selected admission manifests separately.
Cross-release inputs require compatible contracts, source/custody/coverage/outcome/purpose
and current support. Value substitution is explicitly admitted and does not rewrite history
or fabricate inference. Directly revoked producing execution cannot be rehabilitated by
replacing only upstream support. Native permissions and exact requested/observed numerical
evidence are preserved.

Evaluate support validity once per statement over the distinct protected candidate closure,
with AND dependencies and explicitly grouped value-substitution alternatives. Reduce candidates
by declared role/kind/context before validity, retaining the existing access refusal surface.
Preserve complete protected traversal under ADR-0110 and live family premises, including
PostgreSQL linguistic/catalog observations. Immutable completion correspondence may be carried
only under its actual validator-kernel identity; mutable premises and caller authority remain
live. Retained completion intents remain the recovery point and retain/publish are separate
transactions. Missing or different seals run the complete validation battery.

At pinned-read acquisition record immutable scopes, zero-inclusive epochs, actual nested access
universes and kernel identity. Forbid later support/frontier graph writes in that acquiring
transaction; acquisition bookkeeping is allowed and later graph writes use a fresh transaction.
Each use locks the recorded scopes, compares current epochs/kernel and reauthorizes the caller.
No cached authority decision or forgeable session marker replaces these checks. Old reads require
reacquisition. New population visibility and directly revoked producers retain their semantics.

Trust publication, renewal, cancellation and reads acquire scopes in canonical order in shared
mode before request/task locks; revocation acquires them exclusively and bumps epochs. Shared
call-wide locks precede per-item savepoints. Large preparation stays outside locks. This changes
settlement exclusivity, preserving publication/revocation ordering and exact attempt fences.

## Consequences

The native and Python consumers migrate together through the ordinary frozen forward successor.
Re-lowering admitted release facts does not certify historical products under a new validator.
Old intents are preserved and receive full validation; their seals are not fabricated. Implementation,
concurrency controls and qualification remain owned by the DDO coordinator's PE-S16–S22 scope.
No historical reader, data deletion, migration, activation or provider call is authorized by this
record alone; execution authorization remains the operator's implementation instruction.

ADR-0093's decision-acceptance versus completion distinction and scoped legacy-reference retirement
remain: prior records still governing consumers retire only with those consumer migrations.
