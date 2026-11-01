# Relational document model, identity and custody

## Structured-data amendment — PDF-18/19 integration

**Accepted planning target,2026-11-01; new implementation not_run.** [PDF-27/28](structured-payload-model-and-validation.md)
and coordinator RC10/11 qualify earlier universal native-field/SQL-interior requirements. Prior
foundation implementations/receipts below remain scoped baseline, not proof of this amendment.

PDF-18 consumes the per-family native/app→Arrow bridge and retains genuinely joined native
addresses, memberships, occurrence endpoints, inputs and coverage. Nested OCR words/candidates
can remain typed payload interiors when no SQL consumer needs their fields. Derive selected Core
lookup columns and read-only projections from the model; do not independently edit projected facts.
A new interior type then changes its model/codec rather than every SQL scalar/row validator.

PDF-19 extends identity under the declared representation profile. Exact IPC bytes, serialized
schema fingerprints and logical content identity are distinct: compression, dictionaries and batch
layout may alter the first without altering meaning. Preserve ADR-0043 and exact historical
bytes/receipts without promising maintained old-pin readers (RC12). Test independent expected variants/presence/null/order,
rebatching and projection correspondence. Broader native lowering replacement waits for I21/I23;
no silent coercion or dropped native fields. PDF-27 owns new codec work; this owner retains the
existing record/identity integration and retirement consequences. Consume PG-03 generated
`TypedColumns`/`Named`/`.with_cols` and PG-06 protected projections for SQL-visible structures;
PG-04 directional wire profiles describe transport, while PDF-27 owns nested codecs derived
from native/app definitions. Bind all necessary release/compiler/mapping/projection identities.
Changing a field's meaning without changing its SQL type must invalidate affected preparation.
Extend PG-08/09 native authoring/diagnostics for current objects, preserving committed history;
RC12 rebuilds current products and retains evidence rather than mandatory old-layout support.


> **Library improvement integration — 2026-11-01:** [review](../../plan_improvement_reviews/pdf-docling-streaming-improvements_2026-11-01.md) at `5d7a72c4`
> is incorporated into the [coordinator](../pdf-docling-pipeline_2026-10-31.md) and PDF-20–25 targets.
> The [streaming owner](streaming-processing-and-arrow.md) owns new source/crop lifetime and scheduler
> contracts; [publication](staged-publication-and-validation.md) and [consumer](integrated-document-consumers.md)
> packages own their integration. Delivered mechanisms and dated receipts below retain their scope.
> Already implemented public parser delegation, input release and inline/rich-cell handling are
> foundations to preserve, not new feature claims. Extra recognizers and caches remain conditional.

**Status:** PDF-17–19 foundation implemented, 2026-11-01; targeted verification below. Live publication/streaming producer and assembled qualification remain downstream.
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

**Mechanisms:** LinkML `SchemaView`/induced slots and existing compiler preparation; Core `Table`, composite `ForeignKeyConstraint`, uniqueness/CHECK support; reusable Pydantic `TypeAdapter`; `validator_for`/`check_schema` and pinned `referencing.Registry`. See [Pydantic](../../libraries/data_model/pydantic.md), [JSON Schema](../../libraries/data_model/jsonschema.md) §§2/4/8 and review sources. `model_construct`, permissive omission and experimental partial validation are not admission shortcuts.

**Completion:** independent examples cover all supported field/reference categories, shared provenance, repeated/parallel relationships, null/presence, rich cells and oversized values. Full reconstructed native values and ordered references match independent expected fixtures and reload through pinned Docling on bounded cases. No whole-document hydration is required on the ordinary record-write/read path. PDF-24 owns all consumer migration.

<a id="PDF-19"></a>
## PDF-19 — Streaming identity, exact artifact parts and replay

**Input:** I16, PDF-18 record/address contract and PDF-17 successor decision. **Output:** versioned product/byte identity rules and bounded artifact custody used by PDF-20/21/24/25.

Keep original/raw byte digest, logical product/revision identity and exact serialization digest distinct. Current `content_digest` remains SHA-256 of its historical complete canonical envelope; a new manifest hash must not silently reuse that meaning. Define a new contract version and qualified pins; retain archived pins/bytes as evidence without mandatory historical runtime readers under RC12. Native-address reindexing must never reassign an existing citation.

Specify deterministic typed record encoding, scalar normalization, presence markers, length/domain separation, collection ordinals and unordered-record ordering. Use stable key order or external sorting rather than a required whole-document Python sort. Transport batch size/order, compression and Parquet row groups cannot affect logical identity. Declared exact export bytes have their own serialization identity. A semantic JSON roundtrip is not byte-identical replay.

Artifact parts retain stream identity, ordinal/offset, length, bytes and verified inventory; large lists of members remain rows, not giant manifest arrays. Verify actual submitted content and its record mapping server-side, not merely claimed hashes. Frozen spool files have physical integrity hashes separate from logical content. Independent exact-byte correspondence and replay remain required even when derived indexes are regenerated.

Reuse incremental capture logical encodings only after establishing their native-field suitability; do not transplant KG envelope canonicalization. `hashlib` incremental hashing, ordered COPY/read iterators and existing artifact custody provide ordinary mechanisms; no Merkle service or new storage engine is required. I16 must settle the byte/record verification protocol and canonical ordering before implementation.

**Completion:** rebatching, reordering and recompression preserve logical identities; changed values/order/presence do not. Corrupt/missing/reordered artifact parts, conflicting duplicate keys and wrong source/release pins refuse. Exact retained serialization is recovered byte-for-byte and its original digest preserved. Migrated/native-address mappings preserve repeated occurrences and citation scope.

## Dependencies and boundaries

PDF-18/19 provide agreed schemas early to PDF-20 and PDF-24; actual publication/reader acceptance requires implemented mappings and native constraints. PDF-22 can investigate assembly concurrently. These are contracts and coherent outcomes, not a mandatory agent/worktree sequence. All new production SQL uses forward migrations; committed0061 is frozen even though undeployed. The coordinator owns final acceptance and planned/implemented/tested boundaries.

## Execution decisions — 2026-11-01

ADR-0042 supersedes ADR-0041's required monolithic physical realization.0060 remains deployed;
0061,0062 and0063 remain undeployed. The successor preserves original/raw
bytes and old SHA-256 content_digest semantics. No source inference or operational cutover is
part of these foundation changes.

The mapping uses the exact bundled native schema to govern fixed native object, membership and
reference families. Finite inline scalar/structure payloads retain presence; repeated collections
are ordered rows. Native map/address/reference keys and large/NUL-containing leaves have typed
byte-stream overflow routes. Inline binary64 uses an explicit bit representation so JSONB cannot
remove negative zero. Explicit native callback conformance compares supplied state before/after
validation, not serializer output that may omit empty fields or add computed grids. Implicit
version, geometry, scalar-kind and list repairs refuse; normalization belongs before identity.

The record model is an archived implementation input and imported physical declaration. SQLAlchemy,
Arrow and Pydantic boundaries share induced model constraints. It is not inserted into the older
execution-boundary primitive profile as a fake supported JSON/bytes operation. New staging APIs
remain unavailable until PDF-20. The physical-model identity binds named length-framed local import
sources, not just physical.yaml. New compiler source changes are bound in execution ABI15;
ABI14 retained reads retain their archived meaning, without authorizing new writes under old code.

The selected identity profile is `pdf-record-sha256-fold-v1`: tagged/length-framed scalar and record
values with canonical64KiB byte blocks and independently authored PostgreSQL functions. Decimal
coefficient/sign/exponent and binary64 signed zero survive. Operational product/revision IDs,
transport grouping, file codec and native positional addresses are not implicit identity inputs.
Schema/release/source and supplied governing records remain meaning-bearing. Oversized inline and
external scalars share logical descriptors. Exact replay validates actual parts, contiguity/EOF,
byte fold and conventional serialization SHA-256 in the Python stream; native part verification
checks actual fixed-block folds. Native standard whole-stream SHA-256 for arbitrary new segmented
streams is not claimed without an independent incremental server facility. Retained-byte comparison
is authoritative only when PDF-20/21 supply bytes through trusted admitted custody.

Opaque extensible native JSON detail uses a named encounter-order exact-byte profile; it does not
claim canonical unordered-JSON equivalence. Declared native fields/maps use the schema-owned logical
ordering. This preserves unknown supported detail without a generic EAV store or whole-extension
Python sort. Full reconstructed native values are an explicit hydration demand; ordinary lowering,
identity and selective records do not construct a whole DoclingDocument.

### Investigation outcomes and remaining integration

- **I14 partial, source-inspected:** StandardPdfPipeline2.145 `_assemble_document`1155–1178 collects
  page elements then invokes reading-order and hierarchy; BasePipeline173–223 prepares enrichment
  from the assembled document. Keep these semantics and required crop lifetime in a narrow pinned
  adapter. Actual disk-backed assembly/producer integration remains PDF-22, so strict bounded
  end-to-end memory is not established by this foundation.
- **I15 foundation outcome:** native field/reference/presence mapping and callback placement belong
  to the record codec; full frozen-union native closure remains PDF-21. Pinned2.105 callbacks can
  mutate version, geometry and list structure; reads cannot silently invoke that repair behavior.
- **I16 foundation outcome:** versioned bounded framing/fold and exact-part/replay primitives supply
  the new protocol. Actual staged-record/artifact correspondence and complete native-export byte
  comparison remain PDF-20/21/24, not established by a client digest or primitive parity test.
- **I17 contract outcome:** existing attempt/holder, append/freeze serialization, immutable validation
  inputs and short fenced seal remain the chosen lifecycle; live protected operations remain PDF-20/21.
- **I18 foundation outcome:** induced model types/constraints drive Core/Arrow/Pydantic; unsupported
  nested wire values use child rows/explicit parts. Actual bulk COPY, ADBC/snapshot readers, total
  buffer lifetimes and operator-specific spill remain scoped to PDF-20/23/24.
- **I19 conditional:** no early section can be deemed closed merely because its last page completed.
  Global heading/enrichment/context dependencies need explicit closure; PDF-26 remains optional.

The coordinator retains each investigation's single current disposition. These outcomes do not
close the downstream operations or turn source reasoning into provider/whole-book qualification.


## Foundation verification and current handoff — 2026-11-01

The implemented interfaces are `iter_native_records`, `NativeRecordReader`, explicit
`reconstruct_native_document`, `validate_native_callbacks` and `native_record_identity_fields`.
`NativeRow.physical_values` projects only declared JSONB columns from the UTF-8 Arrow wire.
`record_arrow_schema` and `record_boundary_adapter` derive constraints from the physical model.
`LogicalIdentity`, scalar descriptors, `ArtifactPart`/`ArtifactPin` and `replay_artifact` supply
versioned framing, fixed-block folds and exact-byte primitives; historical identity.py is unchanged.

Forward0062 creates private fixed-family tables and pure/native artifact functions. Frozen0063
corrects the integration findings without rewriting0062: a shared pglast input-signature helper
excludes OUT/TABLE parameters and retires phantom descriptor signatures, model-owned read_roles
control exact table/column SELECT privileges, and graph-cell IDs are distinct from document
pointers under their declared field discriminator. The relational compiler is now3; execution
ABI15 preserves ABI14 archived reads while refusing new writes under the old implementation.
Core/system revision0.6.3 records compiler3 with a parented change record and regenerated schema
identities; semantic classes and key scheme1 are unchanged. Historical revision entries and
frozen migrations remain unchanged; the live0060 database still records core0.6.2.
No new private append/seal/consumer API is claimed: those are PDF-20/21/24 obligations.

Independent controls include90 codec cases (all64 admitted native object classes/declared fields),
17 identity cases, native artifact corruption/custody/privacy, actual release admission, graph-cell
codec-to-SQL insertion, model/role counterfactuals and frozen product reproduction. The initial
assembled failure is retained; its causes were owned-function test setup, OUT/TABLE signature
authoring and the blanket public-read assumption. Corrections preserve independent native
validation rather than weakening it. [Receipts and limits](../../design_review/evidence/2026-11-01_pdf-record-foundations/README.md)
own exact commands/outcomes and final source applicability. No full pipeline/provider qualification
or efficiency measurement follows from these controls.
