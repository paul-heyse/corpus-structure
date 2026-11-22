# SBX-06 computation identity and native delivery

**Design tier · target purpose · 2026-11-21.** Independent review of the SBX-06 identity,
authority and execution-fit target at committed source `d918a09ea`. Standard is core 3.3,
efficiency heuristics 1.0, code-intelligence 1.4 and the repository binding. Source findings
are **Inspected** and target judgments are **Proposed**. The review consumes the production
audit's [scoped refresh at `d918a09ea`](../audit/README.md) over `568d70596`. Coordination of
the audit update and this review is concurrent. No changed production files informed the
review. Provider, database, performance and integrated execution checks are **not_run**.

## Decision

Revise the SBX-06 target before changing native keys. Proceed with a distinct project-scoped
computation lookup, exact contextual claims, and durable PostgreSQL delivery through the
existing executor once the proposal fixes the four contracts below. The architecture needs
distinct facts for what ran, which result is reusable, which inputs a current use is entitled
to rely on, and which committed changes an acquired scope has settled. An identity or an
empty dispatch result cannot stand in for any of the other facts. Independent SBX-03–05
work can proceed. Revision A owns native coverage, Revision B owns public freshness, and
SBX-20 owns registered cutover. [SBX-06](../../plans/set-based-execution/references-and-projection-keys.md#sbx-06) ·
[Revision A and B](../../plans/set-based-execution/cutover-and-qualification.md#native-revisions)

The target serves an evidence-backed corpus whose users can follow both current selections
and historical evidence. The relevant workload is a maintained book with many obligations
under one original, partitioned producers, sparse and broad source edits, new model activations,
and concurrent native publication, restart and reading on one PostgreSQL deployment. The
early annotation-to-canonical chain is the first implementation discriminator. Diamonds,
parallel roles, first and removed members, protected evidence and supersession exercise the
same ownership boundary. Cross-project sharing, automatic refresh effects, per-partition
memo admission and public freshness serving belong outside this review's decision. [Functional target](../../design/DESIGN.md#section-1-1) ·
[Propagation scenarios](../../plans/set-based-execution/cutover-and-qualification.md#propagation-scenarios)

## Scope, ownership and fidelity

| Fact | Owner, identity and revision | Fidelity and coverage | Consumer |
| --- | --- | --- | --- |
| Exact request and claim | Native binding reconstructs exact custody. Request/generation has a separate active task/attempt fence. | Authenticated demand, operation, source and analyzed context, exact runtime and binding, under their respective lifecycle rules. | Executor, durable recovery, publication. |
| Reusable computation | Effective declaration owns projection and result determinants. Native admission authenticates commitments, with identical typed meaning in Python. | Exact for the admitted projection and execution policy. Unproven reads widen scope. An equal digest supplies a lookup candidate. | Native attachment before hydration, then admitted execution envelope. |
| Producing episode and current use | Publication owns immutable outputs and historical inputs. Attachment/disclosure own the exact current use and support. | Attributed producer and consumer assertions. A current reference needs authoritative correspondence to a current occurrence. | Binding, support validity, online reads, replay. |
| Change and readiness origin | The authoritative native transition owns its revision and native fact. Durable delivery references that fact. | Exact origin, with conservative matching permitted for a scoped readiness recheck. | Immediate native recipient selection and existing executor. |
| Scoped freshness | The governed selection owner records exact demand, generation, relevant unresolved changes and settled cut. | Complete only over the declared scope and covered changes. Missing coverage is unknown. | SBX-11 live disclosure and SBX-12 pinned or detached evidence. |

DA-078 remains an execution diagnosis. Current readiness recursively expands operation
ancestors, compares coarse source-local fulfilled uses and hashes visible facts and the
whole boundary trust snapshot. The current hash has no explicit installed-kernel component.
DA-071's historical three-authority diagnosis has narrowed: native support paths use declared
edges, and change impact consumes native revocation witnesses. Change impact still walks
conservative operation-level old and new dependency projections. It has neither instantiated
role identity nor the semantics of an eligible current binding. The prior review's F03 and
F04 govern the premise and producing/current distinction carried here. [Readiness diagnosis](../audit/execution-fit.md#da-078) ·
[Dependency and support diagnosis](../audit/semantic-model-and-authority.md#da-071) ·
[Current comparison](../../../python/corpus-structure/src/corpus_structure/semantic/change_impact.py#L157) ·
[Prior F03/F04](design_review_sbx-revision-a-identity-and-authority_2026-11-21.md#F03)

## Findings and corrections

<a id="F01"></a>

**F01 · Exact custody and computation need distinct identities and an enforced premise.**
The current unique request key selects a mutable binding and generation, and native attachment
locks that row. Replacing its digest with geometry equivalence would let two analyzed scopes,
releases or exact selections address the same claim owner. Keep a unique exact request
identity, with the following separation of responsibility. The context and actual coordinates
needed to bind work, coalesce exact requests and fence recovery stay with the native request
and generation. Ephemeral read coordinates stay in admitted support when they do not distinguish
the work. The computation lookup is project-scoped and nonunique over published candidates.
Include effective recipe, projection specification, every observed typed digest and result-affecting
parameter, policy, inference or replicate determinant. Authenticate those from selection and
declared metadata before hydration, on the native path and in canonical Python meaning.
Keep role and collection meaning in the premise, including multiplicity, ordered positions,
observed absence and omitted fields versus explicit null.
Provider, Python and native kernels receive only the declared premise. A whole-role default
preserves undeclared older operations; opaque access prevents narrowing until its premise is
established. Keep effectful or exact-provenance work under its admitted restrictions.

Canonical currently forwards source, selectors, block coverage, selected coverage, block
placement and order alongside geometry and role-relative references. The key must include
the retained header and address commitments corresponding to everything this execution can
read. SBX-01 supplies partition commitments, and shared SBX-02 premise acquisition supplies
useful composition. The current proof routine has an ungrouped body-reading path. A
computational cutoff that uses that fallback or hands a full body to a narrowed kernel
fails the target. An unread field changing a wider input kind identity must still preserve
eligible computation identity, even if its exact custody changes. Validate both equality and
change via independently authored projection expectations and provider-attempt observations.
FP-02/04/05/07, A1/A2/A4, G2/G6, CI-G1. [Exact request storage](../../../python/corpus-structure/src/corpus_structure/model/semantic/data-operation-physical.yaml#L204) ·
[Exact attachment](../../../python/corpus-structure/src/corpus_structure/semantic/request_attachment_native.py#L1535) ·
[Canonical reads](../../../python/corpus-structure/src/corpus_structure/semantic/canonical_sentences.py#L88) ·
[Proof reads](../../../python/corpus-structure/src/corpus_structure/semantic/data_operation_rule_native.py#L127)

<a id="F02"></a>

**F02 · Substitution needs an exact use-facing support mode and admitted current occurrence.**
Current publication installs the output under its producing request context. Existing selected
reference admission can require that the original and selected product/member addresses agree.
A reused episode's original inputs must remain interpretable for authorized historical evidence.
An exact current use must separately record its selected support and occurrence correspondence.
For a compatible output contract, admit a current occurrence association to the retained result
through the existing native output and attachment authority. Where an output needs a new
contextual identity, admit the contextual projection or publish it with explicit borrowed
computation provenance. A current use cannot publish an old contextual product as current by
pointing at the episode alone. Ambiguous repeated text or a split without an address relation
requires fresh exact acquisition and may exclude output attachment. Reject any route that
adopts a producing attempt or asserts a fresh proof establishment merely because a digest
agrees. An exact retained intent and a settled reusable result have different recovery rights.

Current use validity structurally admits either the full producing episode or selected support
for a value use. The existing rebound-revocation test first withdraws the historical upstream
support, so it cannot show refusal when that historical support still stands. A use explicitly
bound on current substituted support must require that basis independently of old support.
Current proof establishments, direct producer revocation, current selected support and
disclosure remain separate checks. Exercise both sides of each revocation and explicitly
check historical-healthy/current-revoked, two uses of one producer, direct producer revoked,
missing establishment and protected access. Observe selected address readback and locked
disclosure independently of the computation key. FP-01/04/05/06, A2/A3, G1/G2/G3/G6,
CI-G1/CI-G2. [Contextual output admission](../../../python/corpus-structure/src/corpus_structure/semantic/data_derivation_native.py#L555) ·
[Current reference admission](../../../python/corpus-structure/src/corpus_structure/semantic/producer_correspondence_native.py#L100) ·
[Current support alternatives](../../../python/corpus-structure/src/corpus_structure/semantic/support_edges.py#L185) ·
[Validity selection](../../../python/corpus-structure/src/corpus_structure/semantic/data_validity_native.py#L439) ·
[Existing revocation setup](../../../python/corpus-structure/tests/semantic/test_data_operation_storage.py#L2699)

<a id="F03"></a>

**F03 · Durable delivery needs both origin and recipient enrollment atomicity.** Publication
already has an immutable receipt with exact output and fulfilled-use facts. Key replay from
those records and a transactionally durable delivery reference wherever the facts do not track
dispatch and acknowledgement. Activation needs an immutable transition keyed by its project
and fenced generation because its current pointer drops the old transition. Establish a native
named head over explicitly admitted exact demand selections and authorized successor transitions.
Keep release activation, inventory registration and evidence selection distinct. Registration
only wakes an interested open/inventory selector. Active release changes can affect explicit
release-following interest or inform an explicitly admitted successor. A frozen demand keeps
its exact release and sources. A timed-out reply must recover the same committed origin or
refuse a different transition at the observed fence.

Compile actual reverse selectors from admitted relationship occurrences in PostgreSQL.
Supplement selected addresses with prospective membership and waiting selectors so a first
member, an empty closure, or a new usable episode for an equal-digest exact pin is visible.
An origin and a waiter enrollment that overlap must share a scoped fence or reconcile their
overlap before declaring coverage. Otherwise each can commit after reading the other's old
state and the waiter stays asleep. Preserve every relevant typed reason when coalescing work.
Settlement must cover the exact reasons it checked and leave a reason that arrived during
execution available for a subsequent decision.
Proof, source admission, fulfilled use, discovery and trust transitions must reach the native
binding owner even when computation is unchanged. A conservative body-dependent wake can
request one scoped check. It cannot supply binding or authorization. FP-02/03/04/05/07,
A1/A2/A3/A4, G1/G4/G5, CI-03/05. [Activation CAS](../../../python/corpus-structure/src/corpus_structure/semantic/closure_native.py#L560) ·
[Publication receipt](../../../python/corpus-structure/src/corpus_structure/semantic/data_derivation_native.py#L653) ·
[Fulfilled-use attachment](../../../python/corpus-structure/src/corpus_structure/semantic/request_attachment_native.py#L1778) ·
[Waiting discovery](../../../python/corpus-structure/tests/semantic/test_data_operation_pinned_reuse_native.py#L538)

<a id="F04"></a>

**F04 · Settled coverage needs a scope, current arms and an unbroken pending chain.** Mark
the affected maintained scope pending in the same transaction as a relevant origin. Keep
unresolved work visible through dispatch, claim and waiting for an authorized demand. A short
settlement transaction records affected immediate successors or a settled decision before it
closes the predecessor. At a join, confirm that no unresolved upstream work can still reach a
relevant input role and that each arm has a current or valid carry-forward decision for the
same selection. Use the admitted scoped relationship projection against unresolved work.
An unchanged arm can supply carry-forward evidence without a provider attempt or a synthetic
descendant sweep. A scoped native cut is fresh only when those premises cover committed
changes. A resolved unavailable result, pending work and unknown coverage have different
meaning. Late legitimate publication can remain historical. It cannot advance a superseding
selection. Active demand, executor claim and governed selection fences continue to protect
their respective operations.

Reject freshness derived from an empty claim batch, one queue position, timestamps, or a
last allocated sequence without a matching commit-order contract. Pause native delivery
between two edges while the target's queue is empty, and exercise a diamond with one changed
arm, one unchanged arm and a genuine independent scope. Include lost acknowledgement, a
superseding selection, protected pending state and a last settled cut subject to current
disclosure. Migrate the planner's waiting decision, wire waits, executor rediscovery and
watermark read on the same coverage boundary. Retain actual finite record-grade census and
pin-based replay, including their authority and completeness consumers. FP-01/02/04/05/07,
A1/A2/A4, G2/G4/G5/G7, CI-G1/CI-G2. [Wait comparison](../../../python/corpus-structure/src/corpus_structure/semantic/data_operation_demands.py#L739) ·
[Recursive watermark](../../../python/corpus-structure/src/corpus_structure/semantic/data_operation_projections.py#L2004) ·
[Executor discovery](../../../python/corpus-structure/src/corpus_structure/orchestrate/data_operations.py#L2333) ·
[Finite record-grade census](../../../python/corpus-structure/src/corpus_structure/semantic/record_grade_native.py#L434)

## Composition and alternatives

The runtime dispatch projection starts at an admitted origin. Its universe is current scoped
selected or prospective dependencies from the effective native model and exact demand. Preserve
direction and role/output/population occurrence identity, including parallel relationships and
ordered/multiple bindings. Indexed SQL matching yields exact candidates where the premise is
stored and a conservative wake where the owner still owes a binding predicate. A bounded
dispatch page limits work acquired by that invocation. Pending facts and the governing scope
retain coverage of deferred work. The change-impact old/new operation projection is useful for
explaining conservative candidates under that model. It cannot justify a native wake, an
absence claim, or a settled arm by itself. Provenance and validity keep their separate typed
graphs. Neither analytical reachability nor a new broker acquires native effect rights.

| Approach | Judgment for the workload |
| --- | --- |
| Repeated digest-on-demand and discovery sweeps | A keyed first read can remain useful for a new or rare request. Repeated whole-demand ancestry and population reconstruction grow with the book's same-source obligations even when observed fields are unchanged. They cannot establish a pending guarantee between two edges without another source of custody. |
| Scan retained receipts for every wake | Direct keyed replay fits exact receipt recovery. A broad receipt scan cannot recover overwritten activation state and does not handle a waiter that enrolls after an origin was processed. |
| Native keyed origin and coalesced immediate work | Reuse existing native facts, exact claims and generated schema. PostgreSQL uniqueness and `INSERT … ON CONFLICT` give a durable same-origin arbiter. Scoped locks and fresh reads under explicit isolation protect enrollment and fence checks. Use bounded `FOR UPDATE SKIP LOCKED` only to acquire dispatch work if concurrent consumers justify it. A query that skips locked rows cannot establish coverage. Keep potentially expensive matching and computation outside long-held locks, with a final owned fence. |
| Eager descendant invalidation or external event platform | A broad wake after every change buries both computational cutoffs and scopes in avoidable work. Another platform adds delivery and recovery boundaries while PostgreSQL must still own authorization and atomic state. Revisit fan-out preparation if an actual large maintained scope cannot obtain a bounded, keyed immediate route. |

[PostgreSQL 18 insertion and conflict handling](https://www.postgresql.org/docs/18/sql-insert.html) ·
[PostgreSQL 18 transaction isolation](https://www.postgresql.org/docs/18/transaction-iso.html) ·
[PostgreSQL 18 row locking](https://www.postgresql.org/docs/18/sql-select.html#SQL-FOR-UPDATE-SHARE)

## Gates, authority and qualification

| Gate | Target judgment |
| --- | --- |
| G1 Authority | Revise. One owner per origin, binding, use and selection. Fix use support and establish selection/delivery ownership in F02–F04. |
| G2 Fidelity | Revise. Distinguish exact identity, projection equality, role identity, coverage and unknown in F01–F04. |
| G3 Validity | Revise. F02 must keep required establishment, current selected support and direct revocation independent. |
| G4 Hidden behaviour | Pass within the proposed restriction to explicitly authorized demand and transitions. Activation, registration and reads cannot implicitly compute or retarget. |
| G5 Consistency and recovery | Revise. F03/F04 need atomically recoverable origin, enrollment and pending coverage across handoffs. |
| G6 Transformation and reuse | Revise. F01/F02 need a complete enforced premise and contextual output association. |
| G7 Capability claims | Pass at Proposed maturity. This source review provides no runtime, provider or throughput claim. |
| G8 Library leverage | Pass in the proposed realization. Existing PostgreSQL tables, native program declarations and executor supply the composition. |
| CI-G1 Fidelity | Revise. F02 and F04 guard producer attribution, exact current use, and unknown versus unavailable. |
| CI-G2 Evidence closure | Revise. Pin cut, current selection and native disclosure consistently under F02/F04 before serving freshness. |
| CI-G3 Evaluation integrity | Outside the selected boundary. No change to gold/reference inputs is proposed. Protected-kind refusal and disclosure remain G1/G3 obligations. |

<a id="RC01"></a>

**RC01.** Supersede ADR-0100 only for the reusable computation identity distinction, amend
the contextual identity owners in DESIGN, D1 and D3, and align the exact-value substitution
and output meanings with ADR-0093, ADR-0122, ADR-0146 and ADR-0147. Retaining the existing
contextual computation key would preserve the over-invalidation and exclude cross-occurrence
reuse. F01 and F02 require the successor before keys change. [ADR-0100](../../adr/0100-ddo-contextual-identities.md) ·
[Contextual owner](../../design/DESIGN.md#section-2)

<a id="RC02"></a>

**RC02.** Record the bounded selection and delivery authority, and replace the readiness
watermark contract in the owning sections when the wake paths and consumers migrate. Keeping
the old discovery/read contract as an active second authority would retain its repeated work
and leave settlement ambiguous. F03/F04 require the new readiness and coverage interface.
Existing durable recovery, frozen reads and exact-stop authority continue through their
owners. [Durable recovery](../../adr/0140-durable-recovery-and-exact-stop.md) ·
[Readiness retirement](../../plans/set-based-execution/references-and-projection-keys.md#readiness-delivery)

**Architecture.** A1 is credible after F01/F03 constrain where changes propagate, and remains
unresolved for the current proposal until those boundaries are explicit. A2 requires revision
for exact current use, output and settlement meaning. A3 has a credible composition based on
the existing admission, proof and executor owners, with the use-facing support mode still to
integrate. A4 is unresolved until the target states the bounded native matching and join path.
Fetching only an output page does not validate the work examined to discover it. The shape
can avoid repeated readiness sweeps for sparse change and tolerate unavoidable broad
collection changes. No performance magnitude is claimed. FP-01/03 support reuse of the
existing owner boundaries. FP-02/04/05/06/07 retain the scenario obligations above.

**Disposition.** Revise the scoped design through F01–F04. The enclosing Revision A can
continue independent producer and proof work. The ADR and an early native candidate settle the
contract before broad propagation adoption. Use the existing equal-output, exact-pin,
authority and partition tests as controls alongside independent denied-substitution, concurrent
enrollment, join, pending and recovery cases. The [SBX-06 package](../../plans/set-based-execution/references-and-projection-keys.md#sbx-06)
owns disposition and closure. The [native revision plan](../../plans/set-based-execution/cutover-and-qualification.md#native-revisions)
owns installed qualification separately.
