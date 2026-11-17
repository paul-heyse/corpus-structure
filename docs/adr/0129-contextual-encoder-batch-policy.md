---
id: ADR-0129
title: Contextual encoders batch authentic observations while preserving independent vectors
status: accepted
date: 2026-11-17
supersedes: [ADR-0114]
superseded-by: null
design: [§B4, §B5]
evidence: Proposed
revisit: A supported encoder requires cohort-determined logical results, native scoring cannot be faithfully recomputed over its frozen inputs, or a consumer requires independent verification of the hidden whole CPU cohort.
---

## Context

D4 M04/M14 and D6 promise that an inventory change invalidates retrieval while unchanged target
descriptors can reuse compatible vectors. Encoding the entire inventory in one request cannot
realize that promise. DDO request identity also retains the selected parent product/member, even
for value substitution, so merely splitting an inventory into vector requests would still couple
vectors to inventory changes. Curated project targets and source-backed definition components
have different actual origins; a query document cannot provide invented target provenance.

ADR-0112 binds a native admission to the actual CPU reply and frozen inputs. Prepared batches
need the original whole reply and authentic receipt, exact logical members and original producer
fences. Copying that reply into each selected completion's disclosed support would expose other
members' bodies, including source-qualified text outside the selected closure. A protected
structural authority leaf has different meaning and cannot silently represent CPU execution.
The DDO coordinator owns implementation, native capture and qualification.

The accepted PE-S29 target now supplies the explicit encoder policy left open by ADR-0114. Actual CPU panels for both selected profiles passed mixed, reversed and regrouped book inputs (managed result08737ea42bf94750b1d018211e4a45ea). This establishes only that authored provider panel, not native DDO integration or ranking invariance.

## Options

1. Keep whole-inventory encoding. This is the smallest implementation but drops accepted
unchanged-target reuse; rejected. An optional prior-vector selection adds inventory-dependent
selection rules and ambiguous missing/empty cases; canonical target products are simpler.
2. Widen native discovery to mixed-source children or add a parallel target cache/scheduler.
Rejected. Existing project/source roots, frozen source sets and demand products provide sufficient
custody without another origin interpretation or lifecycle.
3. Let a thread return search scores with a labelled receipt, or independently implement RRF in
PostgreSQL. Rejected. The first lacks native execution correspondence; the second duplicates
Python reduction semantics. Reuse the existing Core search query behind one native score product.
4. Disclose every batch member or trim/re-hash a whole reply and call it the original evidence.
Rejected. The former broadens disclosure beyond selection; the latter misrepresents the receipt.
A distinct native-authenticated bounded evidence projection preserves both private replay and
selected scope without a new persistent attestation registry.

## Decision

**Accepted target; implementation and qualification Proposed.** Materialize an exact standalone
canonical target before encoding. Project-curated targets retain project scope and no original
source; source-backed targets consume actual selected definition-component products and their
source context. Exact descriptor/body and source/profile support remain meaningful. Target vectors
are separate declared products; query encoding is independent of target inventory. Model
preparation stays with the existing owned CPU encoder and exact captured profile/resources.

Acquire project/source-rooted target demands first, then freeze an explicit cross-context target
vector source set with the query/inventory inputs for final assembly. Complete population,
membership, missing versus empty, source and profile checks remain required. This composes the
existing demand engine rather than weakening same-original discovery or adding a cache authority.

One declared native score product executes the existing authoritative SQLAlchemy Core alias,
full-text and pgvector scoring query over authenticated frozen inputs. Native completion recomputes
that same bounded native function and checks the exact typed product. The actual CPU reduction
consumes this score product and preserves its native producer/receipt; Python owns RRF and
relationship selection. Store exact observed vectors/scores through the existing numerical codec;
no approximate fresh-run equality or duplicated SQL reduction is implied.

The shared CPU input-basis contract includes exact typed semantic parameters and explicit replicate,
in addition to selected inputs/support. Original completion input/support facts remain distinct
from later substitution/currentness. Current scalar and batch reply forms are explicit; no older
basis/reply fallback qualifies. A batch retains the actual original whole reply and execution
receipt, ordered unique member tokens, per-member basis/output and native-derived original
producer fence. First retention uses the already validated execution runtime, not an assumption
that the request-creation runtime executed. Retained-intent replay uses its immutable original
runtime/fence; adopting or publishing a result never rewrites that execution identity. Lost
unpublished siblings retain their original cohort attribution without requiring live sibling claims.

Selected ordinary reads and detached exports expose a distinct bounded execution-evidence leaf
rather than a modified completion-intent row. It identifies the actual original intent, publication,
request/generation/fence/runtime/recipe, receipt, whole-reply digest and selected member commitment.
Sibling bodies remain explicitly undisclosed. The selected operation's genuine input/support
closure remains visible; the leaf does not cut that closure or confer scientific standing.
Detached verification describes native/custodian assertion with hidden physical cohort, not
independent verification of a whole reply it did not receive. Full private bytes remain available
through existing authorized admission/replay custody. Reuse the existing selected export and
archived validation mechanisms with this distinct relation; do not add an attestation table/service.

The three declared encoder operations (query, selected context and target vector) select an
explicit released batch form under a new numerical policy and profile identity. Each logical
occurrence or target keeps one request, product and vector; physical cohort/order does not enter
semantic vector identity. The policy binds model/artifacts, rendering, tokenizer and pooling,
padding side, dtype and normalization, prompts and native chunk size. Authentic native float32
observations may vary with physical cohort/order. All affected vector identities change and prior
vectors can be regenerated; no historical compatibility reader is introduced.

Batch provenance retains the actual ordered member mapping and whole physical reply. Mixed,
reversed, regrouped and cross-request scatter controls must establish member attribution and the
same logical population before enabling the form. Norm tolerance is an admission condition only.
No universal epsilon, fresh-run byte equality, invariant ranking or provider accuracy is promised.
ADR-0085's cue/classification qualification is independent. Other CPU families remain governed by
their own forms. This replaces only ADR-0114's scalar-until-policy clause; all target-reuse,
authenticated native scoring, original cohort custody and bounded disclosure clauses above remain
in force.

## Consequences

Unchanged targets can reuse genuinely independent retained vectors; adding a target changes the
exact candidate population and retrieval without re-encoding unrelated targets. Canonical target
materialization adds a cheap declared product while removing inventory coupling, and preserves
current source/trust support through the ordinary engine. No performance amount is claimed.

Batch execution and disclosure acquire explicit separate contracts. Native guards still enforce
membership, original execution, policy, trust and publication; possession of a digest grants no
permission. Exact-integer prepared-batch controls do not qualify model batching. The provider panels supply bounded numerical and attribution evidence; native/provider integration remains open. Shared protocol integration, native bypass/adoption/refusal controls, detached projection,
actual encoder qualification and retirement of superseded consumers remain with the
[DDO coordinator](../plans/declared-data-operations_2026-11-12.md). This decision neither marks
those obligations complete nor deploys a persistent database change.
