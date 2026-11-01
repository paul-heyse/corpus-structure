# Integrated document model and multi-input lineage

**Status:** Implemented foundation; targeted verification recorded below. Provider qualification is not claimed. **2026-10-31.**
[Coordinator](../pdf-docling-pipeline_2026-10-31.md) owns state, investigations and acceptance.
Consumes the [review](../../functional_reviews/docling-nemotron-triple-pass_2026-10-31.md)
and [target](../../functional_reviews/docling-nemotron-triple-pass_2026-10-31_target-model.md)
at `d25fff8`, especially O02/O05 and the singular-model comparison. PDF-12 owns decisions and
feasibility; this document owns PDF-13's connected contract/storage foundation.

## Target and foundation assessment

**Implemented foundation of the confirmed target; integrated producer/consumer adoption remains PDF-14–16.** Publish one integrated document contract:
DoclingDocument content plus mandatory application-owned relations for provenance, alternatives,
selection and coverage. Neither plain native JSON nor two documents merged independently by each
consumer meets this contract. Nemotron contributions may replace native content under a declared
policy; Docling remains the content schema owner, not an infallible recognition authority.

The current `pdf-products.yaml`, `semantic/pdf_contracts.py`, prepared execution bindings,
SQLAlchemy Core metadata and fenced native publication are suitable foundations. The predecessor
`ops.native_document_product` has one parent triplet. Native 0056 adds shared PDF identity and direct
input relations; ancestry traverses those inputs while preserving the native body and payload.
An optional structural base parent cannot stand for all provenance. Reuse existing typed parsing
relationship patterns where useful without reviving retired HTML adapters.

A new application-owned content schema replacing Docling is not selected. It would require replacing
hierarchy, rich tables/formulas/charts, validation and consumer interfaces. Revisit only if a concrete
required consumer cannot faithfully or reasonably use Docling content plus typed companion relations.
That decision needs an example, alternatives and affected contracts; missing metadata alone is not
a reason to fork Docling classes.

<a id="PDF-13"></a>
## PDF-13 — Executable integrated contract, custody and lineage

**Inputs:** PDF-12 confirmed decision route; existing native/release contracts; I10 geometry and I11
mapping results before their affected constraints are finalized. Early schema agreement can proceed
while runtime feasibility is resolved. **Result:** archived, model-governed integrated products with
multiple-input integrity, protected publication and usable qualified read contracts.

### Model the supported distinctions

Extend existing LinkML companion/execution definitions, not an informal JSON extension interpreted
separately by adapters. Compile effective slot constraints using existing `SchemaView`/induced-slot
preparation, generated/frozen Pydantic boundary adapters and archived JSON Schema. Preserve:

| Meaning | Contract and required relationships |
|---|---|
| Recipe and runtime binding | Provider, package/source, weights and tokenizer identities; prompt, effective decoding/seed, rendering, crop and provider-merge policies. Endpoint location is operational; actual served model/settings affect identity. |
| Submitted image and observation | Original/page/crop identity, submitted bytes digest, dimensions/encoding, exact transform; pass role A/B/C, raw response reference, finish reason, usage and outcome. |
| Occurrence and correspondence | Qualified source block/item/cell/formula/chart identities; separate relationship identity, typed endpoint sets, order, comparison method/evidence; many-to-many, ambiguous and unmatched outcomes. |
| Comparison and integration decision | Text/order/grid/mathematical comparisons remain distinct. Selected/add/replaced/retained-alternative/rejected/unresolved dispositions name governing policy, input observations and output occurrence. |
| Coverage and integrated product | Scope/content family/discovery policy and partial/capped/unrequested portions; one selected content graph, companion relations, complete input pins and validation/health reports. |

Additional providers, policy instances and recipes use these shared meanings and bindings rather
than independent branches. New semantic distinctions still extend the owned model. Specialized
algorithms remain ordinary domain functions behind explicit applicability/input/output/effect
contracts; no general workflow language or per-primitive database task is introduced.

### Address precision and lifecycle

Separate PDF points and page boxes/rotation, submitted page/crop pixels, normalized raw coordinates,
raw response tokens/ranges, recognized-text offsets, selected item ranges and analytical projections.
Record normalization/clipping and inherited/coarse witnesses. Nemotron `(0,0)` charspans are not exact
native offsets; block overlap cannot confer word/glyph or table-cell precision. Retain repeated equal
occurrences separately. I10 establishes trustworthy transforms before overlap can support qualified correspondence;
occurrence identity remains provider/product qualified.

Reuse task/attempt lifecycle and publication fences. Model recognition outcomes, mapping losses,
correspondence and integration decisions as domain results, not a second scheduler. Recognition,
mapping, comparison, selection, publication/binding and inspection operations declare prerequisites,
permitted outcomes/transitions, dependency identity and effects in the trusted execution model.
Execution completion, structural admission, coverage and source fidelity remain independent.
A later-pass failure preserves earlier evidence; a partial observation cannot satisfy a stronger
complete selection contract. Unknown is not successful emptiness.

### Storage, validation and migration

Add direct product-input relations with typed roles and qualified pins, plus independently identified
correspondence/decision endpoints and necessary item/region projections. Use existing Core `Table`,
composite `ForeignKeyConstraint`, uniqueness/CHECK support and protected bulk publication. Enforce
original/project/release custody, endpoint existence and acyclic inputs at the admitted boundary.
Use indexed recursive CTEs for selected ancestry; do not materialize all paths or hydrate whole-book
JSON to inspect one occurrence. Change trace/source-frame reachability alongside new lineage writes.

Retain upstream document JSON/schema as native artifacts and application semantics as LinkML-owned
contracts. Reuse `validator_for`, `check_schema` and prepared validators; bounded `iter_errors`
diagnostics preserve failing instance/schema paths. Native refs remain local; introduce a retained
`referencing.Registry` only if multi-resource schemas are actually needed. JSON Schema cannot enforce
all cross-row custody. RDFLib/pySHACL may realize existing graph constraints where useful; check
pinned generator support instead of assuming all LinkML rules become SHACL. Freeze valuesets with
the release. No mandatory RDF store or ontology truth inference is added.

Use forward Alembic/native migrations; frozen migrations remain unchanged. Backfill historical
parent edges as structural-input relations under their original meaning, never as evidence of a
recognizer that did not run. Retain archived readers/schema admission. No automatic product rewrite,
regrading or old-frame re-anchoring. Publish product, projections, decisions and selected binding
atomically under the attempt fence; inference holds no database connection/transaction.

### Verification and completion boundary

Targeted controls establish multiple qualified inputs, cross-project/source rejection, cycles,
missing/ambiguous endpoints, repeated occurrences, precision loss, stale publication refusal,
archived reload and selective ancestry/trace. Include independent expected relationships rather
than validating actual and expected with the same transformation. One selected table cell must trace
to both provider observations and the original region. Policy-only recomputation yields a new product
without inference, while previous pins still resolve. PDF-16 migrates all consumers; PDF-11 owns
assembled qualification. Contract agreement or schema validation alone does not complete this package.

## Mechanism sources and extension reasoning

[Review O02](../../functional_reviews/docling-nemotron-triple-pass_2026-10-31.md#O02),
[O05](../../functional_reviews/docling-nemotron-triple-pass_2026-10-31.md#O05),
[LinkML overview](../../libraries/linkml.md), [jsonschema](../../libraries/jsonschema.md),
[Pydantic](../../libraries/pydantic.md), [SQLAlchemy](../../libraries/sqlalchemy.md),
[Alembic](../../libraries/alembic.md). The review's primary-source links supply exact mechanisms;
Context7 first, then pinned sources, resolves new API uncertainty during execution.
Changing a reconciliation policy should reuse raw observations and the same contracts. A new
recognizer supplies attributed observations through the same input-role structure; it must not
require consumer-specific source switching. Physical SQL/COPY/JSON layout follows actual access
and transport needs, not one table or transaction per conceptual distinction.

## Execution checkpoint — 2026-10-31

ADR-0039 records the confirmed integrated target and supersedes ADR-0038. The implemented common
`ops.pdf_product` identity supports native, recognition-observation and integrated products;
forward0056 backfills native identities/structural edges without rewriting old payloads. Typed
companion relations and protected publication enforce source/project custody, prior-only immutable
inputs, endpoint/decision inventory, supported precision, attributed coverage and exact replay.
Partial published inputs remain usable without being relabelled complete.

`semantic/pdf_integrated.py` supplies model-governed preparation/publication; common archived context
is separate from native schema admission. `semantic/pdf_storage.py` supplies bounded reads and trace,
including compact provider/image/raw-response descriptors. Native readers refuse integrated bodies
explicitly. Relation endpoints are bounded before hydration; submitted original bytes are validated
but not retransmitted during each observation publication. Integration/storage implementations are
archived release inputs. Future recognition/matching/integration algorithms remain unbound.

Supported submitted-image admission currently validates PNG bytes/dimensions. Provider frame precision
remains coarse/unknown pending I10/I11; this is not proof of arbitrary Nemotron/PDF coordinate mapping.
No Nemotron runtime, operational database upgrade/default cutover, all-consumer migration or corpus
fidelity claim follows. Existing operational0055 and its retained products remain unchanged.

Verification receipts and final focused outcomes are recorded in the coordinator. Original failed
attempts remain in `build/test-receipts/pdf13/`; a repaired rerun does not relabel those invocations.
PDF-14 consumes the published observation contract; PDF-15 implements actual mapping/selection;
PDF-16 migrates real consumers and PDF-11 owns assembled qualification.
