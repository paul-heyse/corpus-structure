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

### Pilot implementation and evidence

**Implemented · 2026-11-22.** Primary construction now uses the immutable row blocks already
acquired with `SourceAnnotations`. The support check still verifies graph slots, item addresses
and layout correspondence. Contextual reads also supply an exact nominal retained annotation;
that path acquires its row blocks against the retained collection commitment. This removes the
second header and packet parse from primary construction without introducing another carrier.

The [provider comparison](../../../python/corpus-structure/tests/semantic/test_sentence_partition_chain_native.py)
uses one captured source for both branches. Its candidates consume packets disclosed by the real
publication, and its read assertions follow exact producing inputs. The Arrow comparison reconstructs
canonical publication bytes from model-derived batches, including through a spawned pilot dispatch.
The PostgreSQL comparison checks geometry and membership after authority has supplied the tagged
packet. These candidate calls compare against actual published results. Each still has a different
publication and transport question from the ordinary provider journey.

**Tested · 2026-11-22.** The eight Arrow parity and real worker transport controls passed
(`uv run ci test`, `bed9d007ed4244868e5d560421167d71`). They cover exact canonical bytes over the
controlled input, explicit projection and schema matching, full-frame admission, malformed input,
stop and clean subsequent work. `uv run ci check --only types` passed for the integrated changes
(`48ea288fe4654ddeb4d68477bd35fa6f`). The first provider captures observed a source change while
running (`8c16fd2637e04037b9196f3e0c6827cc`, `02048ae2f2c64b5da0fa86707e9b646f`). A stable shared
fork then exposed an eager type-annotation import failure in reference resolution
(`43f5f0207ea946b1bc00f3bffb06a715`). Reference resolution now postpones those annotations so
runtime code can import the module under the existing captured contract.

**Tested · 2026-11-22.** The 39 selected `uv run ci test --native-host private` controls passed
(`2237d95ede954a5fac223057c1e9fa35`). They cover the retained annotation carrier, block placement,
memo and split/merge cases, exact selected references, native typed geometry and membership, and
ADBC borrowing and cleanup. The ADBC control used a committed publication pin and the granted
companion projection, exact decimal and UTC time values, and SQL null versus JSON null. A second
scan held the imported cut across a concurrent commit. An earlier attempt reached the expected
privilege refusal when the experiment called the private pin helper directly
(`2722c01cc422465d9720b71b6335e4fb`). That failure informed the use of the granted projection.

The shared provider run `8456c96758dc4ef0bcfb4b4a29751bd4` reached ordinary publication of both
branches, compared the spawned typed canonical output to the published bytes, and compared actual
selected annotation rows from the exact-snapshot ADBC adapter to the ordinary acquired rows.
Its final construction reference acquisition exceeded the existing 8 MiB examined-closure
limit. The fixture now requests the larger supported bound for that scoped read. The default
still bounds temporary indexing and read-transaction work for ordinary requests. SBX-11/12 own
the underlying structural preparation and textbook timeout.

The managed provider cohort `90493eda42ba42ecb7ce700513ee4670` passed four selected identities.
They exercised actual CUDA annotation to canonical publication, HanLP and declaration, primary
construction, and equivalent canonical computation under a distinct current support. The latter
case revoked one support and verified that the unaffected use remained readable. The combined
fixture was the cohort's sole failure at the earlier closure bound.

**Tested · 2026-11-22.** The shared-source rerun `52f96d62df8945858ebdbb3cddae97b2` passed using
`uv run ci test --native-host private --providers-only` for the exact fork test. Both branches
published on a private root built from the captured source. The test verified their producing
inputs, canonical byte parity from the spawned Arrow dispatch, exact ADBC row equality, the
selected construction addresses and the authorized missing-item refusal. The unchanged demand
produced zero new execution receipts. The structural request admitted the examined scope under
the explicit 64 MiB request limit. The output and record limits and global defaults still apply
through their existing owners.

**Pilot decision · 2026-11-22.** Keep the existing immutable carrier for the annotation fork
and use its acquired blocks at primary construction validation. That removes the second parse
and commitment reconstruction on the actual hot path. The model-derived Arrow trial removes the
tagged projection intermediate, while acquiring an Arrow table from tagged rows, framing IPC and
reconstructing Python rows for canonical publication. Its alternate dispatch established
transport and byte parity. The ordinary provider route established installed publication and
selected use. These candidates give no reason to introduce a second ordinary worker format in
this slice. The PostgreSQL membership route extracts and materializes tagged fields to answer a
lookup that can use the already admitted in-process rows. Its ADBC projection crosses the wire
with typed columns, while the protected native routine still constructs each tagged packet before
extraction. The DuckDB connector trial was `not_run` because this pilot exposed no additional
transfer work it could remove through that same guarded source. Keep these scoped findings for
the later SBX-18/19 placement decision. Qualify the selected carrier on the final SBX-09 root
with its remaining consumers.

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
