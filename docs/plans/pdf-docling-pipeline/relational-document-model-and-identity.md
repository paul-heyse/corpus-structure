# Relational document model, identity and custody

**Status:** Planned, 2026-11-01; no implementation or qualification implied.
[Coordinator](../pdf-docling-pipeline_2026-10-31.md) alone owns PDF-17–19 state, streaming-review opportunity dispositions and I14–I19. Basis: [review](../../functional_reviews/pdf-streaming-and-storage_2026-11-01.md) O01/O02/O05 and [target](../../functional_reviews/pdf-streaming-and-storage_2026-11-01_target-model.md) §§1–4 at `1c6fc710`. RC08/RC09 were explicitly accepted for planning on2026-11-01.

## Outcome and foundation assessment

One logical integrated document must no longer require one native JSONB value or one canonical bytea envelope. The content still conforms to the pinned Docling schema; mandatory application relations retain inputs, alternatives, decisions, precision and coverage. Native export and exact retained-byte replay remain supported meanings, with different identities. Physical parts/batches never create semantic section chunks.

Reuse model declarations in `model/system.yaml`, `model/semantic/pdf-products.yaml` and `physical.yaml`, trusted execution preparation, `semantic/pdf_contracts.py`, `pdf_integrated.py`, existing item/region/occurrence/relationship tables and source pin readers. These are foundations, not a complete native decomposition: current item rows are derived access projections, and current preparation still hydrates a complete DoclingDocument. Their mapping must be extended before they can replace authoritative full content.

Core3.3/heuristics1.0 and the applicable profile/binding govern this design. FP-04 requires the model to own operations and state; FP-07/H15–24 favor bounded physical records and immutable publication premises. No new generic graph/EAV framework, task per primitive or alignment lint is needed. Material prerequisite uncertainty is recorded in the coordinator rather than silently resolved by serialization choices.

<a id="PDF-17"></a>
## PDF-17 — Successor decision and foundational investigation outcomes

**Input:** approved RC08/RC09, review/target and existing ADR-0039/0040/0041. **Output:** successor ADR and enduring owner amendments plus actionable decisions for dependent packages. A decision is not implementation evidence.

Create a new ADR superseding the affected ADR-0041 physical realization; accepted records are immutable. Amend DESIGN §B4 and D1/D2/D3/D4/D6/D8 as affected, distinguishing accepted target from0060 deployed/0061 committed undeployed behavior. Preserve PDF-only input, full Docling extras, Standard+RapidOCR/true triple pass, no semantic chunking, independent grading and existing frozen migrations/evidence.

Resolve early foundation questions through source inspection and only discriminating probes where needed:

- I14 identifies a credible exact Docling assembly/enrichment route before producer design freezes. Preserve whole-document algorithm semantics; report any remaining global graph explicitly.
- I15 specifies total supported-native-schema lowering; I16 specifies identity and independent native correspondence. These must be settled before finalizing record/publication contracts.
- I17 defines immutable freeze/validation/seal premises; I18 fixes wire-type and ownership profiles before transport choices become entrenched.
- I19 assesses optional section closure. Its result must not block initial atomic-document delivery.

The authoritative outcomes live in coordinator I14–I19 with links to the corresponding source-review I01–I06. Decisions can become ready independently; PDF-17 is not a barrier requiring every late consumer experiment first. An unresolved prerequisite names its exact dependent work and remedy. In particular, do not claim end-to-end bounded processing while required native assembly still materializes the book.

**Completion:** successor decision/owners agree with confirmed rules; each dependent contract has its necessary investigation outcome or an explicit blocked scope. No mandatory0061 deployment/book rerun is introduced merely to complete the old realization before designing its replacement.

<a id="PDF-18"></a>
## PDF-18 — Lossless native records and generated representations

**Input:** PDF-17 decision slice and I15 lowering specification; early I14 constraints. **Output:** executable document-record model, generated representations and complete reconstruction mapping, usable by staging and readers.

Extend fixed relation families for document headers, native typed records, ordered collection membership, qualified references, native address maps, provenance, rich table/grid/cell content and application companions. Preserve body/furniture, groups, pages, list structure, images/origin, fields outside selected analysis sections and every supported native reference-bearing field. Logical IDs are product/revision qualified and independent of delivery order; native array addresses are explicit projections, not global identity.

Model native fields-set/presence and default-versus-absent semantics, explicit null, empty collection and populated values separately wherever native semantics require it. Keep lexical numeric/formula text, coordinate frames and precision. Large child/cell/provenance arrays become ordered rows. Bounded schema-qualified JSONB may retain genuine native extension detail; an oversized single scalar/subtree must have a defined artifact-part reconstruction route. Simply moving the aggregate limit to one enormous table item is insufficient. Unsupported schema changes refuse with a field/path diagnostic instead of being omitted.

Docling owns native content semantics. The semantic release owns application relations, lowerings and operation contracts. Compile Arrow field order/types/metadata, SQLAlchemy Core tables/FKs/CHECKs, Pydantic boundary adapters and native validation from those owners. Imported JSON Schema alone does not express every upstream custom/model-level rule: I15 must map these obligations explicitly to record or frozen-union enforcement.

Retain one immutable meaning across representations. Factor shared release-bound policy/configuration and custody-identical comparison context into references without merging independent occurrence decisions, equal text or correlated provider votes. Existing artifact bytes remain unchanged under their old pins.

**Mechanisms:** LinkML `SchemaView`/induced slots and existing compiler preparation; Core `Table`, composite `ForeignKeyConstraint`, uniqueness/CHECK support; reusable Pydantic `TypeAdapter`; `validator_for`/`check_schema` and pinned `referencing.Registry`. See [Pydantic](../../libraries/pydantic.md), [JSON Schema](../../libraries/jsonschema.md) §§2/4/8 and review sources. `model_construct`, permissive omission and experimental partial validation are not admission shortcuts.

**Completion:** independent examples cover all supported field/reference categories, shared provenance, repeated/parallel relationships, null/presence, rich cells and oversized values. Full reconstructed native values and ordered references match independent expected fixtures and reload through pinned Docling on bounded cases. No whole-document hydration is required on the ordinary record-write/read path. PDF-24 owns all consumer migration.

<a id="PDF-19"></a>
## PDF-19 — Streaming identity, exact artifact parts and replay

**Input:** I16, PDF-18 record/address contract and PDF-17 successor decision. **Output:** versioned product/byte identity rules and bounded artifact custody used by PDF-20/21/24/25.

Keep original/raw byte digest, logical product/revision identity and exact serialization digest distinct. Current `content_digest` remains SHA-256 of its historical complete canonical envelope; a new manifest hash must not silently reuse that meaning. Define a new contract version and qualified pins; preserve current retained pins through their archived readers. Native-address reindexing must never reassign an existing citation.

Specify deterministic typed record encoding, scalar normalization, presence markers, length/domain separation, collection ordinals and unordered-record ordering. Use stable key order or external sorting rather than a required whole-document Python sort. Transport batch size/order, compression and Parquet row groups cannot affect logical identity. Declared exact export bytes have their own serialization identity. A semantic JSON roundtrip is not byte-identical replay.

Artifact parts retain stream identity, ordinal/offset, length, bytes and verified inventory; large lists of members remain rows, not giant manifest arrays. Verify actual submitted content and its record mapping server-side, not merely claimed hashes. Frozen spool files have physical integrity hashes separate from logical content. Independent exact-byte correspondence and replay remain required even when derived indexes are regenerated.

Reuse incremental capture logical encodings only after establishing their native-field suitability; do not transplant KG envelope canonicalization. `hashlib` incremental hashing, ordered COPY/read iterators and existing artifact custody provide ordinary mechanisms; no Merkle service or new storage engine is required. I16 must settle the byte/record verification protocol and canonical ordering before implementation.

**Completion:** rebatching, reordering and recompression preserve logical identities; changed values/order/presence do not. Corrupt/missing/reordered artifact parts, conflicting duplicate keys and wrong source/release pins refuse. Exact retained serialization is recovered byte-for-byte and its original digest preserved. Migrated/native-address mappings preserve repeated occurrences and citation scope.

## Dependencies and boundaries

PDF-18/19 provide agreed schemas early to PDF-20 and PDF-24; actual publication/reader acceptance requires implemented mappings and native constraints. PDF-22 can investigate assembly concurrently. These are contracts and coherent outcomes, not a mandatory agent/worktree sequence. All new production SQL uses forward migrations; committed0061 is frozen even though undeployed. The coordinator owns final acceptance and planned/implemented/tested boundaries.
