# PDF semantic contracts, custody and access projections

**Status:** Planned; no model, schema or runtime change is claimed. **Created:** 2026-10-31.
The [coordinator](../pdf-docling-pipeline_2026-10-31.md) owns PDF-02/03 state and review/investigation
dispositions. Consumes the [review](../../functional_reviews/pdf-docling-pipeline_2026-10-31.md)
at `2c33372`, its [target](../../functional_reviews/pdf-docling-pipeline_2026-10-31_target-model.md),
PDF-00 decisions and relevant [PDF-01](foundations-and-investigations.md#PDF-01) results.

## Foundation assessment and physical reasoning

`semantic/metadata.py` compiles `model/semantic/physical.yaml` through LinkML `SchemaView` and
`schema.relational.compile_metadata(..., target="semantic")`; shared fixed `Table` objects serve
migrations, queries and publication. Releases add admitted rows rather than per-release tables.
`semantic/parsing_products.py` already binds immutable products, named dependencies and occurrence
endpoints to archived contracts. `semantic/archive_reader.py` reconstructs retained boundary
semantics without rerunning source ingestion. Reuse those owners rather than create a second
editable schema registry or PDF-specific transaction system.

The existing parsing tables and readers represent integer offsets and canonical transformations.
They cannot encode a PDF rectangle by renaming an extent. Extend only the responsibility gap:
native schema-qualified document custody, typed page-region addresses, conversion-qualified item
references and the access relations required by real consumers. Keep rich native JSON available;
do not require loading or validating a 1,589-page model for every one-formula lookup.

The chosen shape is native JSONB plus purposeful, rebuildable projections. JSON-only storage
would repeatedly traverse/hydrate the book; relational-only re-authoring would lose native
interchange and introduce a competing document vocabulary. Derived item/edge/region/cell indexes
add publication/index work but directly serve bounded joins. No quantitative improvement is claimed.

<a id="PDF-02"></a>
## PDF-02 — Connected semantic contracts and native-schema binding

**Owner:** semantic model/compiler and source-contract integration. **Inputs:** PDF-00 confirmed
rule changes; PDF-01 supplies I03/I04/I05/I06 details as relevant. **Output:** agreed early contract
slice, then compiled runtime/native requirements for producers and readers. PDF-03 owns deployed
physical enforcement. Early contract agreement can unblock PDF-01/04 design without pretending
that database enforcement already exists.

### Authority, concepts and relationships

Docling/core owns the native Pydantic document schema. Archive its versioned schema and qualified
adapter capability; application LinkML references it as an external artifact, not a manually
maintained copy of every upstream class. LinkML/trusted execution definitions own conversion
configuration, operations, identities, state/coverage, domain recognition and cross-product
relations. PostgreSQL owns instances. Native Pydantic validation, application boundary validation
and relational custody enforce different properties.

Model the smallest connected set of responsibilities:

- retained PDF original/acquisition; conversion specification with resolved package/model/runtime
  identity; native conversion product; separate conversion-health report;
- item occurrences, ordered relationships, page geometry/regions and qualified native pointers;
- section/subsection hierarchy, section/item analysis selections, derived Docling document and
  text projections with declared linearization and synthetic separators;
- formula recognition and its health, lazy interpretation/assessment, source/domain observations,
  packet/source-frame dependencies and declared read/export capabilities.

A concept need not create a new table, task or service. Conditional alternative-recognition
records are modeled only where activated by a concrete verification need; no generic OCR ensemble
or mandatory per-character record system is introduced.

Pointers such as `#/texts/3` are local to a conversion. Repeated equal formulas remain separate
occurrences; relationship identity is not merely endpoint equality. Record ordered containment,
reading order, caption association, cell-to-formula references, derivation and interpretation
basis independently. Cross-build correspondence, if selected, is another attributed relation.
Named dependencies explicitly authorize cross-product endpoints; matching spelling is not custody.

### Coordinates, states and behavior

Distinguish original PDF byte ranges, physical page number and dimensions, PDF point bounding
boxes with coordinate origin, native item-text spans, recognized LaTeX offsets and derived text
projection offsets. Printed page labels are presentation metadata, not physical-page identity.
An exact recognized-text offset does not establish exact PDF glyph attribution or original TeX.
Allow multiple provenance regions per item and represent unavailable geometry explicitly.

Separate attempt lifecycle from semantic result and coverage. Use the existing task state owner
for pending/running/completed/failed/cancelled work. Native conversion SUCCESS/PARTIAL_SUCCESS
and per-stage health map through the adapter; they are not mathematical correctness or source
fidelity. Formula health distinguishes attributable enrichment from unchanged fallback and unknown.
Coverage separately describes detected formula, inline math and table-cell math universes; absence
of a formula item is not complete absence of mathematics. Failed or partial dependencies cannot
satisfy a consumer requiring complete supported coverage.

Declare convert, organize sections, project views, recognize domain structure, interpret/assess,
build packet, publish, inspect and export operations. Each names input universe, configuration,
implementation binding, effects, dependencies, lifetime and failure/uncertainty outcomes. Resolve
the admitted context at operation/batch boundaries; no per-item database policy lookup. Native
stage execution may be fused while its semantic outcomes remain distinct.

No section chunking, splitting or token-window product is admitted. Section membership and
ancestry govern units; declaration applicability additionally retains source order and forward
extent so later declarations cannot govern earlier formulas or unrelated siblings. Rich document
labels produce attributed observations; consolidation remains the knowledge-claim owner.

### Concrete compilation and validation mechanisms

Use LinkML `SchemaView` effective/induced definitions in the existing compiler and finite adapter
admission. Derive reusable Pydantic/`TypeAdapter` application boundaries and JSON Schema artifacts;
reference a pinned local upstream schema rather than resolve network schemas during ordinary work.
Keep validators prepared at a valid lifetime. JSON-schema/reference validation establishes shape;
foreign-key/cross-product checks establish instance custody; neither establishes OCR accuracy.
Existing RDF/SHACL views can carry qualified occurrence relationships when consumed, without
introducing another independently authored ontology or new inference defaults.

**Acceptance:** independent invalid cases reject swapped coordinate units/origins, dangling or
wrong-build pointers, missing named dependencies, illegal state transitions and partial-as-complete
results. Repeated equal occurrences and ordered relationships survive. A supported behavior change
has one model/adapter owner and an actual consumer; a declaration alone does not complete support.

<a id="PDF-03"></a>
## PDF-03 — Native document custody and bounded relational access

**Owner:** physical model, storage/publication and source-read integration. **Inputs:** PDF-02
agreed contracts; I06 schema/geometry/image findings before layout finalization. **Output:**
shared Core metadata, forward migrations, protected publication and bounded readers consumed by
PDF-04/05/07/08/09. Pure producer development can use the agreed contract before deployment.

Retain original PDF bytes using existing content-addressed `bytea` custody, independently of
conversion success. Persist the complete native `DoclingDocument` as JSONB, linked to original,
conversion specification, producing task/release and separate health report. Native and derived
hierarchy documents are immutable distinct products; derive section containers without changing
the retained raw conversion. Reuse the product registry where its meaning fits.

Use `export_to_dict(mode="json", by_alias=True, ...)` under an archived serialization policy.
Finalize Pydantic/tree/reference validation before identity/publication: core 2.103.1
`validate_document()` can clamp bounding boxes. `model_validate_json`/`load_from_json` supports
qualified reload; reads must not normalize a stored product in place. Keep schema version distinct
from package version. JSONB retains JSON meaning, not original serialization formatting or PDF
bytes; physical integrity hashes and semantic identities remain distinct.

Store normalized conversion-qualified item, ordered edge, section membership, page-region and
cell projections only for required joins/queries. Reuse existing occurrence/endpoint relations
when compatible; add geometry/schema bindings through the physical model where needed. Every
projection names its native product, pointer/occurrence mapping and derivation recipe. Index
conversion/section/item selection and bounded page-region/cell access; choose access paths from
PDF-08 queries rather than indexing every JSON field or materializing all paths.

Image payloads use owned immutable artifact custody where needed. Preserve picture objects,
captions and region references even when no raster is retained. Avoid embedding all page images
as base64 by default; the original can support later rendering. I06 fixes retained figure/region
requirements and reloading semantics before deployment. Never publish ephemeral local paths as
complete artifact custody. A missing payload is unavailable evidence, not an absent picture.

### Native realization, publication and reads

Extend `physical.yaml` and the current `SchemaView` → SQLAlchemy `MetaData` route. Use shared
Core `Table`, `select`, joins, `exists`, set-based DML/`returning` and existing protected staging.
Typed psycopg COPY can share the SQLAlchemy-owned connection/transaction; do not create a second
pool or ORM session as a workaround for bulk source data. Native schema changes use frozen
forward Alembic revisions; preserve revisions through 0046 and all historical stored meanings.
Use existing pglast/physical comparison routes where the migration changes native definitions.

Validate/prepare privately outside scarce publication locks, then publish the document, health
and required projections coherently under existing run/task/attempt fences. PDF-09 integrates
converter lifetime and retry/cancellation into that owner; PDF-03 supplies the atomic storage
primitive, not another state machine. Restricted writers cannot mutate retained products or
create arbitrary physical schema. Corrupt/mismatched projections refuse rather than silently
rebuild history as valid; rebuilding is an explicit derived-product operation.

Readers pin conversion/build identity, resolve effective producer/reuse through existing rules,
and select item/section/cell/region subsets without transferring the whole JSONB document.
Explicit whole-document reload/export remains available as a distinct operation. An ambiguous
build selection refuses; a missing capability reports typed unavailable/rebuild requirements.
Native reference checks and bounded query validation remain attached to the archived contract,
not current process defaults. Old archived records remain readable without rerunning HTML.

**Acceptance:** actual restricted PostgreSQL publication/reads prove native JSONB roundtrip,
retained-original integrity, ordered occurrence multiplicity, geometry meaning, artifact custody,
wrong-build refusal and immutable raw/derived products. Force a failed publication and verify no
coherent completed product becomes visible; replay preserves the original successful identity.
Pure serialization tests are not native publication qualification. PDF-11 owns assembled source,
consumer and operational acceptance; performance remains unmeasured until separately supported.

## Library and owning references

- [Docling/core document API](https://github.com/docling-project/docling-core/blob/v2.103.1/docling_core/types/doc/document.py)
  and [review O02](../../functional_reviews/pdf-docling-pipeline_2026-10-31.md#O02): native JSON,
  normalization and schema boundaries.
- Local [LinkML](../../libraries/linkml.md), [SQLAlchemy](../../libraries/sqlalchemy.md),
  [psycopg](../../libraries/psycopg.md), [Alembic](../../libraries/alembic.md),
  [Pydantic](../../libraries/pydantic.md), [JSON Schema](../../libraries/jsonschema.md) and
  [pglast](../../libraries/pglast.md) orient the existing compiler/database mechanisms.
- [D1](../../design/D1-knowledge-representation.md), [D2](../../design/D2-schema-and-guidelines.md),
  [D3](../../design/D3-database.md) and [D6](../../design/D6-orchestration-metrics-policies.md)
  remain enduring architectural owners, updated through PDF-00 when implementation changes meaning.
