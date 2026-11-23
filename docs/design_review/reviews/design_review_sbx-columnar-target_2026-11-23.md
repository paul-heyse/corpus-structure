# SBX columnar populations, admission and selected reads

**Design/target review · 2026-11-23.** Independently inspected production source at
`cc05ce725`, the reconciled plan at `e59b02b5e`, and the two source reviews. This is the
focused target review scheduled before the replacement changes physical storage, wire and
worker custody. The operator approved all five proposed rule changes on 2026-11-23.
Implementation and final-root qualification retain their separate obligations.
[Coordinator](../../plans/set-based-execution_2026-11-21.md#columnar-redesign-amendment) ·
[Columnar review](../../plan_improvement_reviews/set-based-execution-columnar-basis_2026-11-22.md) ·
[Redesign review](../../plan_improvement_reviews/set-based-execution-efficiency-and-analytical-redesign_2026-11-22.md)

## Scope and outcome

**Proposed architecture accepted for the reviewed scope.** The target has a credible route to
remove repeated tagged-value conversion and per-consumer indexing across the complete
annotation, canonical, construction and selected-read path. Arrow supplies the working
representation and process transport, DuckDB supplies local relational execution, and
PostgreSQL owns declared admission, publication and current support. Generic item rows serve
native rules and indexed references while partitions retain logical identity and reuse.

The retained-parent choice in F01 below is part of this accepted target. Carry it into the
physical model and admission owner before implementing the item table. The remaining
conditions are implementation and qualification obligations for that selected design. This
review supplies no production timing, capacity or installed-root claim.

| Review item | Scope and standing |
|---|---|
| Standard | Core 3.3, efficient-architecture heuristics 1.0, code-intelligence profile 1.4 and repository binding. Test-assessment guidance applies to the independent expectations described here. |
| Functional target | Attributed located observations and their evidence, declared rule conclusions, exact original/current references, authenticated selected answers and independent detached replay. DESIGN §1 and §B1/B4/B5 govern meaning. |
| Workload | Bulk token/sentence/HanLP populations, repeated rule projections and exact item citations, finite/rich archive reads, several provider processes and large or skewed partitions under the existing execution policy. |
| Excluded | Full PDF certification, scoped-relations kernel adoption, general cursor/freshness programs, stage deployment and whole-book qualification. Their affected interface obligations remain visible in their owning packages. |
| Method | Static source and target inspection, prior synthetic evidence and qualitative alternatives. Tests, database commands and new probes were `not_run`. |
| Diagnostic input | The [scoped refresh](../audit/README.md#refresh-2026-11-23-sbx-populations), published at `a4c3122a9`, inspects production baseline `cc05ce725`. [DA-087](../audit/execution-fit.md#da-087) owns the diagnosis of population transport and repeated reconstruction. Earlier findings outside that scope retain their dates. |

## Responsibilities and authoritative facts

| Owner | Decision it owns | Consumed representation |
|---|---|---|
| Effective release and collection compiler | Fields, value states, addresses, order, field groups, rule reads and wire correspondence | Derived Arrow schemas, native relations and typed call shapes |
| Identity owner | Existing canonical spelling and framing | Exact canonical item text and partition/group/root commitments |
| Producer and acquired carrier | Provider interpretation, attested checks and immutable input lifetime | Model-derived columns, selected projections and sealed IPC |
| Native admission and retention | Attempt, shape and canonical/projection correspondence, declared rules, durable completion | Session-private intake and logged retained populations |
| Native publication and selected access | Atomic visible product/proof/use, current support and authorized scope | Published associations, indexed item rows and typed bulk rows |
| Replay and verification | Captured evidence interpretation and independently checkable answer | Sealed Parquet relations under the original cut and release |

Producer facts remain attributed to the actual provider and runtime. A native declared-form
result remains a rule conclusion under its fingerprint and premise. An attestation remains an
assertion by the declared checker. A typed physical row does not change any of those meanings.
Typed references retain slot, role, occurrence and address. Two producers at position zero
remain independently identified. Unknown or unavailable coverage remains distinct from empty
membership. These distinctions satisfy the applicable CI-01–06 model obligations in the
proposed boundary.

## Contracts and retained ownership

The existing physical partition has a foreign key to `kb.data_product`, while the existing
completion intent exists before publication. The new retained population needs a parent that
exists at that earlier point. Its physical owner is the completion intent and output role and
position, with collection and partition beneath it. Keep the final logical product identity as
a distinct value. Publication adds the visible product/derivation association to the retained
population, and item reads require that association plus authorization. A repeated publication
may use an existing identical published population after checking exact correspondence. It
must not overwrite its content or disclose an unresolved retained population.
[Physical declarations](../../../python/corpus-structure/src/corpus_structure/model/semantic/data-operation-physical.yaml#L295) ·
[Completion intent](../../../python/corpus-structure/src/corpus_structure/model/semantic/data-operation-physical.yaml#L399)

This permits one protected insert into logged retained storage and promotion of the same rows.
It avoids making an unpublished `kb.data_product` visible as an intermediate recovery artifact.
Keep the item content immutable and separate lifecycle or association facts. Native guards
verify that a submitted context, projection or claimed product identity agrees with the
admitted canonical items before any rule or address relies on it.

Reuse the current authenticated temporary COPY intake. Verify actual namespace, owner,
shape and relation behavior, start a preparation empty, and bind it to the invocation's
release and attempt. Check the fence before preparation and again before the protected effect.
Existing upload privileges and a temporary namespace alone do not identify the current
attempt. The client validates typed result contracts before committing. An individual refusal
must roll back that item's effects, even when diagnostics are returned as rows.
[Scratch custody](../../../python/corpus-structure/src/corpus_structure/semantic/pdf_staging_native.py#L987) ·
[Owned COPY](../../../python/corpus-structure/src/corpus_structure/semantic/arrow_transfer.py#L134)

Preserve exact committed replay before requiring a current producing claim. The current
publication owner checks replay before and after taking the request lock, allowing lost-ack
recovery after claim expiry. A new effect still needs the live claim and current support.
Carry that distinction into the typed boundary. An unconditional fence at the beginning of
every replay request would reject valid recovery.
[Publication order](../../../python/corpus-structure/src/corpus_structure/semantic/data_derivation_native.py#L345) ·
[Intent adoption](../../../python/corpus-structure/src/corpus_structure/semantic/data_completion_settlement_native.py#L1224)

## Composition and physical execution

A producer acquires columns once and exposes the declared projection to its consumers. Prepare
each distinct premise projection once within the actual completion or partition lifetime.
Generate canonical item framing from those columns, then combine ordered item text under the
existing identity definition. Keep exact hard-scalar spelling and all allowed optional states.
Native admission validates canonical item form once and derives or verifies its rule/address
fields, then reuses the admitted relation for rules, closure and commitments. The generic
Python encoder remains an independent reference. Engine-expression spelling does not enter
semantic fingerprints.

Use DuckDB `from_arrow(pa.Table)` for a reused finite population, the existing typed expression
owner for windows, joins and grouped computation, and `to_arrow_reader(batch_size=...)` for
incremental egress. The source table owner must outlive the computation. A reader is single-use.
A sort, ordered aggregate or join has its own retained state. Partition-grain aggregation is
credible for the ordinary path, but a dominant partition requires a deliberate execution-fit
choice before it is claimed supported. Arrow and DuckDB limits, queues, model memory and
mapped storage have different owners and need complete cleanup at cancellation.
[Analytical contract](../../plans/set-based-execution/common-analytical-basis.md#columnar-population-target)

Seal worker IPC after writing and retain one invocation owner through accepted reply or
cancellation. Bind the file, schema, request and logical commitments. Use the acquired read
handle and mapping rather than authenticate a pathname and later open a possibly replaced
file. The validating constructor must establish immutable ownership of buffers supplied by
an external producer. A read-only view alone cannot prevent its external writable owner from
mutating the backing storage. Retain post-encoding and late-import verification at the current
worker boundaries. IPC transfer digests and logical content identities have separate roles.

Point references follow the authorized item index. Bulk selected reads project before tagged
envelope construction and preserve bags and role identities. The existing selected archive
uses transaction-private keys and same-session reads. Keep that route where the pin or archive
state is uncommitted. Companion export's imported-snapshot ADBC reader is suitable for eligible
committed projections, with the parent snapshot alive through drain or close. A second
connection cannot read the first session's temporary archive keys.
[Selected export](../../../python/corpus-structure/src/corpus_structure/serve/demand_export.py#L161) ·
[Archive cut and issuer](../../../python/corpus-structure/src/corpus_structure/semantic/selected_archive_native.py#L238) ·
[ADBC snapshot](../../../python/corpus-structure/src/corpus_structure/serve/companion_export.py#L131)

The replay projection states its finite relation universe, original cut, producing inputs,
reference direction, multiplicity and declared order. DuckDB anti-joins, `EXCEPT ALL`, counts
and exact commitment checks can replace the selected JSONL/SQLite reconstruction. Its manifest
must cover schemas, bytes, logical commitments, completeness and authorized empty relations.
Physical pruning is a layout question, and prior plan evidence alone establishes no bytes-read
claim. Current authority is reacquired for live access. Captured detached evidence preserves the
exported cut and its evidence scope.

## Change and failure scenarios

| Scenario | Change owner and expected propagation | Settling evidence |
|---|---|---|
| Add a table-cell population with optional geometry | Collection declaration derives schema, indexed address and rules. Existing generic intake, retention and read paths apply. New domain semantics belong in the declaration. | Independent canonical and address examples under the new collection. |
| Move, rename, repeat, split or merge source blocks | Content, observed placement, computation equivalence and current occurrence remain separate. Only the relevant projection changes its key. | Existing shared change scenarios with actual publication and selected readback on the replacement. |
| Substitute IPC chunking or dictionary layout | Physical encoding may change the transfer seal while equivalent content keeps logical commitments. | Independent logical vectors and deliberately different physical encodings. |
| Send valid canonical text with false rule columns | Admission refuses before evaluating a rule or publishing rows from the false projection. | Conflicting span, optional-state and address fixtures. |
| Expire an attempt during COPY; lose acknowledgement after commit | Stale new effects refuse. Exact committed replay can return the authenticated prior result after claim expiry. | Real attempt/lock/replay controls and interrupted COPY. |
| Return typed per-item refusal after a sibling success | Refused effects roll back at the promised scope. Sibling results and retry remain coherent. | Independent partial-refusal and replay expectations. |
| Warm a body cache, then revoke support | Cached content cannot authorize disclosure or mutation. Role and scope checks still run. | Existing revocation and original/current binding controls through the indexed reader. |
| Replace selected archive cut or swap its issuer | Same-session handle remains issuer- and cut-bound; a detached response carries the exact captured universe. | Native handle misuse, altered cut and finite/rich independent replay. |

## Gates, findings and architecture judgments

These verdicts concern the proposed target above. Qualification of its implementation remains
open. No gate is awarded on the basis of current product test counts.

| Gate | Proposed-target verdict and own grounds |
|---|---|
| G1 Authority | Pass. One model defines the schema and semantic reads; PostgreSQL authenticates submitted projections and effects. |
| G2 Fidelity | Pass. Optional states, exact scalar text, canonical reference and complete role identities remain explicit. Required production parity cases remain implementation acceptance. |
| G3 Validity | Pass. Validating carrier construction and native canonical/projection correspondence precede dependent work. |
| G4 Hidden behavior | Pass. Reads, effects, materialization and artifact publication retain explicit owners. |
| G5 Consistency and recovery | Pass. F01's intent-owned logged population and published association define visibility. Exact replay and partial refusal preserve existing failure contracts. |
| G6 Transformation and reuse | Pass. Logical commitment and transfer seal differ, observed placement is explicit and live authorization remains independent of cached contents. |
| G7 Capability claims | Pass at Proposed maturity. Synthetic controls are attributed to their stated cases and the target includes production acceptance. |
| G8 Library fit | Pass. Arrow, DuckDB, PostgreSQL and pgpq own their native capabilities. Canonical generation implements the remaining repository identity contract. |
| CI-G1 Fidelity | Pass. Provider assertions, rules, original/current bindings and unknown/empty states retain their types and scopes. |
| CI-G2 Evidence closure | Pass. Exact selected cut, producing inputs, archive universe and manifest are part of live and detached contracts. |
| CI-G3 Evaluation integrity | Pass within this boundary. Protected authority and independent expectations remain outside producer truth and engine result comparison. Wider evaluation policy is excluded. |

<a id="F01"></a>
### F01 — Give retained populations a parent before product visibility

**Interface-checked diagnosis; Proposed correction.** The old partition-to-product foreign key
cannot by itself support durable pre-publication item rows and promotion of those same rows.
The retained header must use completion intent and output identity as described above, with
publication supplying the visible association. This is a focused lifecycle refinement of the
existing I03 storage recommendation, owned by SBX-01/02 and retention/publication. It preserves
exact logical identity and introduces no additional rule impact. Verify lost acknowledgement,
repeated content, an expired producing claim, a malformed projection, and refusal of unpublished
item disclosure. [Disposition owner](../../plans/set-based-execution/populations-rules-and-proofs.md#typed-item-admission)

A1 is satisfied for the proposed scope. Shared contracts localize a new collection or provider
shape while storage and native authority reuse the common boundary. A2 is satisfied by the
model-derived shapes, explicit authority and retained/publication lifecycle above. A3 is
satisfied by composition through the existing analytical, COPY, worker and selected-read owners.
A4 is satisfied qualitatively for the stated bulk and sparse workloads: source columns serve
multiple consumers, native sets reuse one admitted relation, indexed points avoid decoding a
partition, and logged retention supports recovery without reinserting items at publication.
Skew and resource release remain explicit implementation obligations before claiming support.
FP-01–07 and the applicable DP-01–04, DP-07–11, DP-13–15, DP-19–24 are satisfied by those same
scoped mechanisms. These judgments leave full PDF, general query and other kernel acceptance
with their owners.

## Alternatives, evidence and rule impacts

The simplest immediate alternative is to retain the acquired immutable carrier and improve
repeated preparation. It is already useful and has scoped tests, but leaves packet construction
and restoration around bulk consumers. Fully typed per-collection tables would simplify some
queries while adding native DDL and registration per shape. Generic logged item rows plus
model-derived indexed projections provide the needed set and keyed access with one declaration
route. Direct COPY into durable tables would need an additional attempt-scoped privilege design.
The existing protected temporary intake followed by one admitted durable insert is a credible
smaller ownership boundary. PostgreSQL executes mutable authority work. Moving that work to
DuckDB would require new claim, support, recovery and writer coordination without a demonstrated
replacement advantage in this scope.

The [retained probes](../evidence/2026-11-22_sbx-columnar-basis/README.md) provide limited
identity and composition evidence. They cover integer, boolean, string, list and absence
fixtures. Full optional states, wide numbers, float/temporal spelling, sets, bags, nested
mappings and HanLP still need independent parity. The small Acero fixture establishes read-ahead
under its settings and cannot establish the general absence of backpressure. No timing claim
or root-cause attribution for the interrupted qualification follows from these controls.

The approved impacts are RC01–RC05 in the order ADR-0128 typed population wire, ADR-0144 item
storage, ADR-0145 typed custody, ADR-0021 SBX canonical production, and ADR-0148 brought-forward
analytical prerequisites. The operator accepted all five on 2026-11-23. Carry surviving renewal,
nonpopulation wire, other kernel and pool obligations into their existing authorities. The
[coordinator](../../plans/set-based-execution_2026-11-21.md#columnar-rule-confirmation) owns the
recorded decision and execution sequence. The replacement ADR and corresponding DESIGN/D3/D8
owners record the architectural change. This review accepts the direction for implementation.
The plan owns native, worker, provider and final-source qualification of the delivered result.
