# Executable acquisition, material identity and recovery

**Status:** Proposed · 2026-11-20. The [coordinator](../domain-model-operability_2026-11-20.md)
owns readiness and disposition. This companion implements the target from review
[O01][o01], [O02][o02] and [O06][o06]. All acceptance scenarios below are planned.

## Baseline and boundaries

N42 reproduced 624 installed objects and admitted the releases, then the cold Integrated
run failed before inference inside transform acquisition. An isolated replay reproduced the
asset mismatch from an M1 capture fix and an event read change. Equal source bytes at another
path reproduced the archive. A genuine transform code edit and a declared input edit moved the
asset as expected. The replay leaves the two historical edits' effect on actual Integrated output
open. The broad fallback includes observed modules for all mode roots and incompleteness also
feeds reuse eligibility. The M1 planner was missing from a separately maintained capture list.
These are different failure boundaries even though they currently use overlapping facts.
[N42 and M1 evidence][cause]

DMO-00 verified both N42 archives on the acquired stage. No stage project selects either release.
Prepare the two modes using the explicit archived release IDs and actual runtime custody. Report
archive verification, acquisition and project selection separately. [DMO-00 evidence](../../design_review/evidence/2026-11-20_dmo00-entry-baseline/README.md#current-target-observations)

| Decision | Authority and scope | Consumer |
| --- | --- | --- |
| Can this executable run? | Admitted selected operation, exact archive and acquired callable/resource bindings | Application and fixture preparation, then actual port acquisition |
| What can change its output? | Selected implementation, semantic input/support, parameters, resource and output contracts, and replicate where applicable | Recipe and material comparison |
| Can an earlier attempt be used here? | Sufficient material correspondence, authenticated original producer and artifacts, and current support/publication authority | Request attachment, intent reconciliation, draft or acknowledged page adoption |

<a id="dmo-01"></a>
## DMO-01 · Derive and verify the selected executable

Consume the existing admitted operation and its implementation declaration. Derive the selected
callable/resource specification from that declaration and selection, first for the Standard and
Integrated PDF transforms and M1. Capture the corresponding sources once and feed the same set to
early preparation and runtime verification. Include shared initialization, external bindings and
resource footprints where they affect the selected execution. Keep the broad code graph as
attributed discovery and change-impact evidence. Unresolved required correspondence continues to
refuse. Narrow an enforced dependency only when the selected boundary establishes its coverage.
The first refusal reports the operation, resource, and expected and actual basis through the
current typed diagnostic path. [Existing port verifier][verifier] · [Code asset owner][asset]

**Library realization.** Python 3.14 `inspect.ismethod` and `__func__` identify the implementation
of a supplied bound method. Resolve the physical origin from `inspect.getfile` through
`Path.resolve()` and match its bytes to the trusted archive. The existing verifier checks the
qualified binding, loaded `__code__` against code compiled from the recorded source and the
expected globals owner. Preserve those checks and the admitted resource verification. The existing
`ast.parse` and `NodeVisitor` analysis discovers source-level relationships and unknowns. It cannot
establish the actual runtime target of a dynamic binding. Retain authenticated distribution and
native file checks for extension code whose origin cannot be verified as a Python function.
Archive logical names remain stable across source relocation. [Python inspect origin](https://docs.python.org/3.14/library/inspect.html#inspect.getfile) ·
[AST parsing and visiting](../../libraries/python_introspection/ast.md#3-parsing-capabilities-and-compiler-controls) ·
[External runtime custody][runtime]

Use the same application resolver in fixtures. Retire the separately maintained capture and
verification inventories, the all-mode seed for a proven single-mode acquisition, and any fixture
path that treats archive logical names as physical filenames. Check remaining callers before
retiring the common fallback. The comparator and the diagnostic use the same acquired facts, so
an operator can take the identified corrective action before a provider submission or work claim.

**Acceptance.** Prepare both PDF modes and M1 from the admitted source. Exercise a relocation,
each historical edit independently, a genuine transform dependency change, a rebound callable,
modified source bytes, a changed provider resource, a wrong mode and a missing M1 planner.
A change of a real dependency remains visible in the correct owner. An unresolved effect of a
historical edit remains explicit. Verify actual M1 GLiNER publication, its CPU and logical-provider
receipt, and operation-scoped native readback through [DMO-08](qualification-and-adoption.md#dmo-08).

<a id="dmo-02"></a>
## DMO-02 · Compare material and recover compatible work

**Prerequisites.** DMO-01 supplies a selected executable contract. The numeric domains in
[DMO-05](json-contracts-and-settings.md#dmo-05) supply value meaning. The common schema package
supplies the installed contract identity when a wire transition affects the material basis.
The field comparison can start using current admitted inputs before any digest changes.

**Identity.** Give the existing identity owner named, versioned profiles for D1 keys, semantic
values and SQL parity where the contract has real consumers. Preserve D1 key bytes and hash
original retained bytes directly when the question is byte custody. Derive semantic digests from
model-owned fields rather than from JSON presentation, transport or PostgreSQL JSONB text. Define
numeric equivalence for any participating float, including signed zero and alternate spellings.
Inventory digests and the legacy Decimal tag collision using approved input sources. Allow arbitrary
literal objects only under an injective encoding when the owning value domain calls for them.
Retire canonical calls handling size, presentation or round-trip validation once the respective
owners migrate. Use a named transition and frozen forward generation when required bytes change.
Keep the prior canonical profiles only where authenticated historical interpretation requires them.
[Contextual identities](../../adr/0100-ddo-contextual-identities.md) · [D1 keys](../../design/D1-knowledge-representation.md)

**Material comparison.** Project the result-affecting implementation/resources, input/support
meaning, parameters, selection, output contract and replicate. Retain release, generation,
demand and attempt coordinates as provenance. Compare the typed fields and their sources at the
existing owner. Report unknown determinants conservatively and distinguish an unknown historical
field from a known differing recipe, support or scope. This resolves the two separate book cases.
The N29/N42 recipe census lacks constituent fields. The equal-recipe case was demand-scoped because
lowering proof was incomplete. An equal output can stop downstream changes only under its declared
substitutability contract. [Book evidence][cause] · [Python and native attachment][attach]

**Recovery.** Keep distinct paths for exact committed intent reconciliation, private draft adoption
and acknowledged page uptake. Apply the existing material projector and compare current declared
premises before choosing work. On uptake, verify original attempt, retirement and replay bytes and
acquire current support and publication authority. Keep exact same-demand recovery when a
cross-request determinant is unresolved. Convert compatible retained material where it is
practical and authenticated. Preserve raw originals and historical receipts, and regenerate
ineligible derived results through the current path. Retire active legacy readers, selectors and
adapters as the new owner takes their actual consumers. [Checkpoint contract](../../adr/0139-compatible-pdf-checkpoint-custody.md) ·
[Recovery contract](../../adr/0140-durable-recovery-and-exact-stop.md) · [Spool material projection][spool]

**Library realization.** Use PostgreSQL 18 native predicates and the existing generated attachment
and settlement operations for visibility, lease and publication decisions. Psycopg 3.3.6 obtains
transaction outcomes through the current transaction owner. Preserve the distinction among a known
rollback, an uncertain commit that needs authoritative readback, and a committed intent that can be
reconciled. SQLAlchemy Core 2.1.6 supplies declared typed statement expressions through the existing
connection owner. The material comparator never turns a driver retry into permission to repeat an
uncertain write. Use the existing process-owner retirement proof and the repository's manifest and
file-byte checks before adopting spooled material. [Psycopg transactions](../../libraries/postgresql/psycopg.md#10-transactions-savepoints-and-distributed-transaction-support) ·
[SQLAlchemy execution](../../libraries/postgresql/sqlalchemy.md#8-database-execution-transactions-and-resource-management)

**Acceptance.** Use independent key/SQL/value vectors and a bounded regional controlled stop.
Compare an orchestration-only change with genuine producer/schema/resource/parameter changes.
Confirm matching eligible pages survive with original attribution. Revoked support, modified replay
bytes and active or counterfeit producers must refuse. Compare equal and distinct request bases
from native readback. The unchanged repeat publishes zero new receipts. Exercise rollback,
uncertain commit, and exact intent replay separately before full-book qualification.

[o01]: ../../functional_reviews/udm-operability-and-json_2026-11-20.md#O01
[o02]: ../../functional_reviews/udm-operability-and-json_2026-11-20.md#O02
[o06]: ../../functional_reviews/udm-operability-and-json_2026-11-20.md#O06
[cause]: ../../design_review/evidence/2026-11-20_udm-operability-causality/README.md
[verifier]: ../../../python/corpus-structure/src/corpus_structure/semantic/data_operation_prepared_products.py#L16
[asset]: ../../../python/corpus-structure/src/corpus_structure/semantic/operation_code_assets.py#L21
[runtime]: ../../../python/corpus-structure/src/corpus_structure/semantic/external_runtime.py
[attach]: ../../../python/corpus-structure/src/corpus_structure/semantic/request_attachment_native.py#L1557
[spool]: ../../../python/corpus-structure/src/corpus_structure/semantic/pdf_spool_native.py#L244
