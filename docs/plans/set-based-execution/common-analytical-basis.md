# Common analytical basis

**Proposed · 2026-11-22.** Companion of the [SBX
coordinator](../set-based-execution_2026-11-21.md#common-analytics-review-amendment). It owns the
SBX-03/08 pilot, the shared projection contract and the PostgreSQL placement comparison. Package
disposition stays in the coordinator. The full scoped-relations trial and the frozen replay reader
have their own owners. [Source review
I01–I04](../../plan_improvement_reviews/set-based-execution-common-analytics_2026-11-22.md)

**Inspected at `d884fa8a2`.** Canonical execution materializes a selected annotation projection,
thaws it for a CPU call and parses and acquires the reply. Primary construction takes the same
annotation population directly, with formal evidence, and prepares its own navigation and membership
structures. The current immutable partition carrier can already share a decoded body across
placements. Compare against that implementation and follow both branches through their consumers.
The detached reader's earlier removal of a second completion representation illustrates the work a
stable hand-off can remove. Failures at installed descriptor correspondence exercise a different
guarantee. [Inspected paths and scoped
observations](../../plan_improvement_reviews/set-based-execution-common-analytics_2026-11-22.md#where-the-burden-comes-from)

<a id="projection-contract"></a>
## Projection contract

Derive a typed projection from the effective model's declared roles, collections, field groups and
rule premises. Define each relation at its consumer's grain. Include stable partition and item keys,
order, occurrence, placement and presence where observed. Body-relative rows and current placement
have separate commitments. An absent field and an explicit null remain distinguishable where the
model distinguishes them. Preserve exact values, canonical bytes and identity at publication. One
projection can have physical backings suited to its consumers, including Arrow batches, native
relation rows and the typed archive in [SBX-12](owner-resolved-reads.md#sbx-12).

Establish type and structural shape at external acquisition and at conversions that can change
meaning. An admitted projection carries its established facts while their premises hold. Use grouped
checks, windows, anti-joins or construction invariants for ordinals, counts, containment,
membership, inventory closure and coverage over the governing population.
[SBX-04](populations-rules-and-proofs.md#sbx-04) owns establishment. Batch compatible work while
retaining separate conclusions when the required scope or eligible provenance differs. A point read
acquires only the keyed facts and body it needs. [SBX-05](references-and-projection-keys.md#sbx-05)
still resolves through the original producing role and acquires authority for the exact current use.
An anti-join establishes absence within the admitted projection. The authorized scope determines
what that absence means. The native owner commits product, proofs and use outcome atomically.

**Tested · 2026-11-22.** Arrow 26.0.0 accepted the structural shape of a fixture with duplicate
ordinals and an out-of-range span. DuckDB 2.0.0 found both over Arrow and Parquet. The tested UTC
nanosecond sample survived both scans and Arrow egress. The DuckDB CLI showed projection and filter
pushdown for the fixture. Use [`DESCRIBE` and
`EXPLAIN`](../../libraries/analytical_infrastructure/duckdb_2_cli.md#36-query-and-schema-discovery)
when a disputed type or scan boundary matters. These observations cover the pinned fixture.
Integrated behavior and any performance claim require their own evidence. [Runnable
probe](../../design_review/evidence/2026-11-22_sbx-common-analytics/README.md)

<a id="typed-population-pilot"></a>
## Typed population pilot

Start with runnable SBX-01 partitions, the SBX-02 proof-binding slice, SBX-05 exact reference
resolution for the slice and SBX-08 acquired carriers. Use newly admitted fixtures on the existing
early integration route. Follow annotation → canonical → HanLP and declaration for affected address
coverage, and annotation plus formal evidence → primary construction. Include a real selected
publication and exact readback. Native settlement and SBX-09 implementation custody can continue in
parallel. Use SBX-06/07 controls as their relevant slices become runnable. [Early
integration](cutover-and-qualification.md#early-revision-a-integration)

Compare three routes through the complete fork.

1. Use the current immutable carrier and its validated payload reuse as the baseline.
2. Acquire a model-derived Arrow projection. Use [Arrow
   compute](../../libraries/analytical_infrastructure/pyarrow.md#3-native-computational-capabilities)
   for direct column transforms and
   [DuckDB](../../libraries/analytical_infrastructure/duckdb_2.md#33-the-relational-api-as-a-native-query-construction-layer)
   for set steps. Compare in-process batches with an owned [IPC or
   stream](../../libraries/analytical_infrastructure/pyarrow.md#71-arrow-ipc-native-columnar-interchange)
   where a real worker boundary otherwise serializes the same rows as JSON. Check sealed bytes at
   ingress, charge buffers and descriptors to their existing owners, and exercise stop, eviction and
   cleanup. Reuse canonical encoding at the publication boundary.
3. Use typed PostgreSQL projections over admitted populations and native set checks. Include the
   cost of extracting partition rows, and any typed-row staging or return to Python. Compare
   [transfer placement](#postgresql-placement-and-transfer) where finite inputs are needed outside
   PostgreSQL.

Trace actual decode, conversion, validation and index construction through producer, hand-off,
publication and readback. Use bounded observations where source inspection leaves a consequential
uncertainty. Exercise independent expected rows and bytes through equal blocks moved or renamed,
ambiguous splits and merges, duplicate ordinals, invalid containment, missing members and protected
parents, explicit null and absence, and closed-empty and pending populations. Verify the same
content under different support and deliberate revocation. The local projection key stays stable
when observed inputs stay equal, and publication resolves the current selected placement. Use the
real provider and native routes where the representation change reaches them.

**Decision.** Accept a candidate for the affected families only if it preserves meaning, identity
and use custody and removes at least one complete repeated decode, rebuild or validation path
without equivalent work or a second persistent authority. Among conforming candidates prefer the
simpler complete route, including admission, transfer, recovery and consumers. If neither qualifies,
keep the current carrier and use set execution where it independently simplifies a kernel. Approve
any required rule change through the route below. Move the producers, workers and readers together
and retire the displaced path and mechanism-specific tests with the replacement. Finish the choice
and integration before cold-root authoring. [SBX-09
cutover](cutover-and-qualification.md#development-reset-through-sbx-09)

<a id="postgresql-placement-and-transfer"></a>
## PostgreSQL placement and transfer

Compare two placements. PostgreSQL can check facts about admitted rows in the publication
transaction. DuckDB can analyze an exact, finite, purpose-authorized projection locally and send
the result to native publication. Account for extraction, local joins, text and formula work,
conversion, result movement and publication. The pilot compares these routes for its population.
[SBX-19](kernel-trial.md#sbx-19) applies the
comparison to the complete scoped-relations operation and its artifact consumer.

Compare the existing authorized transfer with ADBC as the first columnar candidate. The [companion
export](../../../python/corpus-structure/src/corpus_structure/serve/companion_export.py#L125)
demonstrates importing the authority owner's exported snapshot into a bulk read transaction and
streaming Arrow from native exact-pin functions. Keep acquisition, purpose permissions, snapshot
lifetime, cancellation and current-use checks under their owning operations. Release acquisition
resources when the transfer is complete.

Try the DuckDB PostgreSQL extension on a private target when it can consume the purpose-authorized
projection and plausibly eliminate material work beyond ADBC. Inspect effective pushdown and
connections. Compare two related scans against a concurrent change to establish one exact cut.
Verify purpose scoping, revocation on the next live acquisition, bounded cancellation and cleanup,
ordered placement, null and presence, and exact decimals, timestamps and identity where carried.
Read-only attachment addresses write permissions. Pooled scans still need evidence of shared-cut
behavior. If the live contract fails, consider the connector only for immutable data. Retain the
existing exact-numeric restriction on consolidation pool loads. [Connector and pool
contracts](../../plan_improvement_reviews/set-based-execution-common-analytics_2026-11-22.md#I03) ·
[Database carrier decisions](../../design/D3-database.md)

**Operational ownership.** PostgreSQL owns current authoritative state and publication in this
series. An embedded DuckDB coordinator with one writer and immutable worker batches could simplify
database deployment. Quack and DuckLake introduce a service or catalog with different coordination
costs. A concrete alternative that simplifies cross-process coordination warrants a separate
architecture proposal. It must account for purpose permissions, exact support and selection, attempt
fencing, atomic product and proof publication, visibility, revocation and crash or
lost-acknowledgement recovery. [Transactional authority](../../design/DESIGN.md#section-b4) ·
[Review
alternatives](../../plan_improvement_reviews/set-based-execution-common-analytics_2026-11-22.md#I03)

<a id="decision-routes"></a>
## Decision routes

Use existing accepted boundaries for production during the comparison. Isolated comparative evidence
can exercise proposed forms. If the selected route changes an architectural rule, record the rule
impact and operator decision before adoption. Supersede the affected part of the decision through
the ADR and its owning design section, and reconcile [UDM's analytical
placement](../unified-domain-model-and-execution/analytical-placement-sql-and-retirement.md) where
its typed authoring or attachment policy is affected.

| Selection that changes a rule | Owning decision |
|---|---|
| Captured SQL at the DuckDB or native PostgreSQL owner | [ADR-0135](../../adr/0135-declared-facts-and-typed-database-programs.md), DESIGN §B4/B5 and D3 |
| Scoped-relations authoring or connection lifetime that changes the accepted trial | [ADR-0148](../../adr/0148-sbx-kernel-trial.md) and the SBX-18/19 owner |
| Typed worker transport that changes sealed custody | [ADR-0145](../../adr/0145-sbx-custody-boundary.md) and SBX-08/09 |
| Connector that changes snapshot or selected-read custody | [ADR-0026](../../adr/0026-columnar-semantic-operations.md), DESIGN §B4/B5 and D8 |
| Native typed layout that changes authoritative partition storage | [ADR-0144](../../adr/0144-sbx-partitioned-products.md), DESIGN and D3 |

Apply the [design review
cadence](../../design_review/design_principles/binding/corpus-structure.md#reviews-in-this-repository)
for a binding decision or substantial ownership or dependency change. Use the [shared qualification
scenarios](cutover-and-qualification.md#change-scenarios) and record final-source evidence under the
packages that exercise them. Compare timing or profile only when transfers, scans, memory or spill
could change the choice between conforming routes.
