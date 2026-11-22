# Common analytical basis

**Scheduled · 2026-11-22.** Companion of the [SBX
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

<a id="numeric-fidelity"></a>
**Numeric fidelity · Scheduled · 2026-11-22.** Derive physical scalar types from the effective
field bounds. Arrow `decimal256` supports precision through 76 digits and DuckDB `DECIMAL`
through 38. The generic codec permits 16,384 fixed-point digits. Use bounded numeric columns
where the declaration fits the engine's precision and scale. For wider generic values,
retain the canonical lexical decimal and semantic tag for exact transport and identity.
Any arithmetic on those values needs an exact compatible implementation. Include mixed
precision and scale, integer versus Boolean, SQL null versus JSON null or absent, and UTC
nanoseconds in the chosen boundary's independent controls.
[Efficiency review I06](../../plan_improvement_reviews/set-based-execution-validation-and-postgresql_2026-11-22.md#I06) ·
[Installed value probes](../../design_review/evidence/2026-11-22_python-postgresql-efficiency/README.md) ·
[Arrow decimal256](https://arrow.apache.org/docs/python/generated/pyarrow.decimal256.html) ·
[DuckDB 2.0 numeric types](https://duckdb.org/docs/2.0/sql/data_types/numeric)

<a id="typed-population-pilot"></a>
## Typed population pilot

**Decided · 2026-11-22.** Retain the acquired immutable annotation carrier and its admitted
blocks through the remaining consumers. The comparison protocol below records the completed
pilot method. Its dated results and selection are in [pilot evidence](#pilot-implementation-and-evidence).
The [post-pilot review I01–I06](../../plan_improvement_reviews/set-based-execution-through-sbx09_2026-11-22.md)
supplies the scheduled amendments whose current disposition belongs to the coordinator.

### Completed comparison protocol

The following directions retain the method used by the completed comparison. Current execution
uses the recorded immutable-carrier decision and final-root acceptance in the coordinator.

The protocol started with runnable SBX-01 partitions, the SBX-02 proof-binding slice, SBX-05 exact reference
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
conversion, result movement and publication. The completed pilot selected existing admitted
rows for its population and established the exact-snapshot ADBC route for comparison.
[SBX-19](kernel-trial.md#sbx-19) applies the
comparison to the complete scoped-relations operation and its artifact consumer.

Compare the existing authorized transfer with ADBC as the first columnar candidate. The [companion
export](../../../python/corpus-structure/src/corpus_structure/serve/companion_export.py#L125)
demonstrates importing the authority owner's exported snapshot into a bulk read transaction and
streaming Arrow from native exact-pin functions. Keep acquisition, purpose permissions, snapshot
lifetime, cancellation and current-use checks under their owning operations. Release acquisition
resources when the transfer is complete.

The pinned ADBC PostgreSQL 1.13.0 route reuses `pg_export_snapshot()`, an owned bulk connection
with `REPEATABLE READ READ WRITE` and `SET TRANSACTION SNAPSHOT` before the scope read, the
purpose-granted projection and `cursor.fetch_record_batch()`. The transaction mode permits the
existing native read locks while purpose grants constrain access. Keep the snapshot owner alive
through the child scan and release child readers, cursor and connection on success or cancellation.
The pilot established exact decimal, UTC and null fidelity on that route. A new consumer must
verify its own schema and exact selected cut. [Existing transfer and lifetimes](../../../python/corpus-structure/src/corpus_structure/serve/companion_export.py#L125) ·
[ADBC Python API](https://arrow.apache.org/adbc/current/python/api/adbc_driver_postgresql.html)

**Transfer selection after the efficiency review · Scheduled · 2026-11-22.** A cross-session
scan requires the exact acquiring pin to be committed or otherwise already visible in the
imported snapshot and the called projection to be purpose-granted. Snapshot export does not
make the acquiring transaction's uncommitted rows visible to the child. Exercise that visibility
condition with a concurrent change before choosing ADBC for a new live consumer.

Start live read improvement with native projection before packet construction and reuse of
the admitted page and exact same-cut binding facts. Keep the annotation fork's selected
immutable carrier. Use a columnar candidate when a named typed population or finite archive
can remove a complete extraction, materialization or repeated relation scan. Compare the
entire route through transfer, conversion, query, publication or archive authentication,
cold reopen and cleanup. The existing analytical owner supplies resources and relation
execution. Use relation `to_arrow_reader(batch_size=...)` for incremental output, with a
deliberately bounded `to_arrow_table()` when materialization serves repeat scans. A connection
`execute(...).to_arrow_reader()` copies the complete result in DuckDB 2.0. Verify actual
producer behavior and close readers before connection reuse. Preserve explicit keys, ordering
and bag multiplicity through both paths. SBX-11 owns live selection, SBX-12 owns the improved
D1 replay comparison, and SBX-18/19 own broader named computation placement.
[Efficiency review I06](../../plan_improvement_reviews/set-based-execution-validation-and-postgresql_2026-11-22.md#I06) ·
[DuckDB 2.0 Arrow export](https://duckdb.org/docs/2.0/guides/python/export_arrow) ·
[Analytical lifetime](kernel-trial.md#sbx-18)

Try the DuckDB PostgreSQL extension on a private target when it can consume the purpose-authorized
projection and plausibly eliminate material work beyond ADBC. Name that workload and the
removed transfer or preparation before trying `ATTACH` with the PostgreSQL extension. Inspect effective pushdown and
connections. Compare two related scans against a concurrent change to establish one exact cut.
Verify purpose scoping, revocation on the next live acquisition, bounded cancellation and cleanup,
ordered placement, null and presence, and exact decimals, timestamps and identity where carried.
Read-only attachment addresses write permissions. Pooled scans still need evidence of shared-cut
behavior. If the live contract fails, consider the connector only for immutable data. Retain the
existing exact-numeric restriction on consolidation pool loads. [Connector and pool
contracts](../../plan_improvement_reviews/set-based-execution-common-analytics_2026-11-22.md#I03) ·
[Database carrier decisions](../../design/D3-database.md) ·
[DuckDB 2.0 PostgreSQL connection pool](https://duckdb.org/docs/2.0/core_extensions/postgres/connection_pool)

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


<a id="capability-dispositions"></a>
## Capability dispositions after the pilot

**Scheduled · 2026-11-22.** This section carries the broad capability screen and investigation
conditions from the [post-pilot review](../../plan_improvement_reviews/set-based-execution-through-sbx09_2026-11-22.md#library-capabilities-examined-and-where-they-pay).
Each consumer owns its concrete API, acceptance and current disposition. These are bounded
investigations with decision outcomes, rather than obligations to adopt every available feature.
The library baseline is PyArrow 26.0.0 and DuckDB 2.0.0 from the exact dependency declarations.

The [efficiency amendment](../set-based-execution_2026-11-21.md#validation-postgresql-efficiency-amendment)
adds the visible-pin, full-path comparison and numeric conditions above. Apply them at the named
consumer, and record retain, adjust or adopt with the outcome and any unresolved condition that
could change the choice. The [qualification owner](cutover-and-qualification.md#sbx-efficiency-qualification)
keeps scoped capability probes distinct from integrated production evidence.

| Capability and placement | Disposition and decision condition |
|---|---|
| Typed Arrow schemas, nested lists/structs, dictionaries and chunks, presence and scalar kernels | Use at existing batch boundaries. Derive `pa.schema`, list/struct fields and exact scalar types from the model, and call `RecordBatch.validate(full=True)` for physical structure. Preserve semantic rules at their owner. SBX-03/08 use the selected immutable objects. Dense Arrow transforms may use `pyarrow.compute` expressions, `struct_field`, `list_flatten` and `list_parent_indices` when the consumer already owns those columns. |
| Arrow expressions, `Table.group_by`, joins and Acero `Declaration` execution | Conditional in SBX-18/19 when one already typed dense population can share preparation across several consumers. Compare the complete path with the current typed DuckDB owner and native sets. Verify exact null, presence, ordering and multiplicity before selection. Add no common engine abstraction in advance of a selected consumer. |
| DuckDB windows, grouped checks, semi/anti joins and bag differences | SBX-18/19 own the concrete trial. SBX-04/05 retain owner-native validation and admitted indexes. Independent typed comparisons are useful where they reveal a plausible wrong result. |
| Recursive `WITH ... USING KEY`, temporary relations, `MERGE` and triggers | A finite independent selector comparison is optional under SBX-06. Include role, occurrence and generation in the relevant state key, preserve bags using `EXCEPT ALL`, and compare explicit expected arms. The retained probe demonstrates loss from a node-only key. Native publication and readiness retain atomic effects. Revisit local state machinery only if a later analytical consumer needs it. [Probe](../../design_review/evidence/2026-11-22_sbx09-review/README.md) · [Recursive CTE contract](https://duckdb.org/docs/2.0/sql/query_syntax/with) |
| ASOF, range and NEAREST joins | Candidate in SBX-19 for batched correspondence proposals or range questions. Establish direction, tie rules, extent semantics and independent exact provenance before acceptance. A nearest candidate alone cannot establish occurrence identity. |
| IPC projection, C Data/C Stream and batch readers | SBX-16 owns projected candidate replay. SBX-18 owns analytical output lifetime. Retain typed buffer owners and treat an imported `RecordBatchReader` as a consumed stream unless explicitly materialized once for repeat scans. An input projection cannot establish omitted-column logical identity. |
| Parquet pruning, row groups, statistics, manifests and spill | SBX-12 owns frozen replay. Choose projected and filtered scans or a bounded reusable lookup from the actual access shape. Physical compression and row-group changes preserve logical identity. Investigate layout or spill quantitatively only when serious memory or scan uncertainty can change the choice. |
| DuckDB VARIANT and Arrow extension types, graph/spatial/text/vector extensions | Revisit only for a named consumer whose domain benefits from the extra representation or indexed query. Use model-derived fixed types for the present rules. DuckPGQ would introduce another graph projection and needs an actual uncovered analysis. Retrieval index choices belong with retrieval consumers. |
| Flight/Flight SQL, Substrait, device/GPU interchange, remote DuckDB/Quack and DuckLake | Deferred until a consumer can name the eliminated handoff or computation and account for the new execution, deployment and custody boundary. A new durable authority follows the existing architecture decision route. |

The [projection contract](#projection-contract) governs shape and semantics, and the
[decision routes](#decision-routes) govern changes to accepted authoring, custody and authority.
A documented capability establishes an available option. Selection still requires the named
consumer and its correctness and lifecycle evidence.
