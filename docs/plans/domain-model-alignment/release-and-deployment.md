# Release and deployment authority

**Proposed · 2026-11-08.** D2 owns release preparation and D3 owns native
deployment authority. This plan supplies DMA-01 and DMA-02. The
[coordinator](../domain-model-alignment_2026-11-08.md) owns disposition and
qualification. [Source review](../../design_review/reviews/design_review_domain-model-alignment_2026-11-08.md#bind-release-products-and-native-admission-to-their-actual-determinants)

<a id="DMA-01"></a>

## DMA-01 · Prepare the same products from the same release inputs

The projection analysis currently hashes retained sources but qualifies them
against the installed `PHYSICAL_MODEL_ID` and supplies installed metadata
to projection preparation. Preview can see proposed bytes while the later
candidate sees those same bytes as installed. Equality of the release manifest
can then miss a change in the prepared artifact.

Extract the closed physical-source compilation already used by model change.
Acquire the retained physical root and resolved imports from the approved
input bundle. Use LinkML runtime's `SchemaView` and the existing
`compile_metadata(..., target="semantic")` to compile a SQLAlchemy metadata
product, identified by the same closure digest used in the release. Prepare
projection definitions and analysis against that product once per preparation
context. Move the installed-profile check to execution compatibility. A
compiler that cannot support the recorded profile produces the same explicit
unsupported outcome under the same declared capability and compiler identity,
or refuses full rederivation when it cannot supply the recorded capability.

Include every behavior-affecting determinant in the preparation identity and
cache. Bind the reviewed required-product digest in exact preview and compare
it before candidate creation or deploy. Preview, candidate, archive verification
and impact analysis use the same preparation contract. Ordinary archived reads
can continue to serve authenticated stored products. Remove the ambient
installed-profile branch and any callers that independently substitute local
metadata. Material changes in determinant or product meaning require a versioned
release preparation contract. Preserve prior receipts and archive identity.
[Existing closed compiler](../../../python/corpus-structure/src/corpus_structure/schema/model_change.py) ·
[Projection preparation](../../../python/corpus-structure/src/corpus_structure/semantic/companion_projection.py) ·
[Release preparation](../../design/D2-schema-and-guidelines.md#semantic-release-preparation-entry-point)

**Closure.** In separate processes with different installed profiles, prepare
identical proposed physical inputs before and after apply. Assert equal required
products and release identity. Vary a declared determinant and check its
identity or explicit unsupported consequence. Recompute a supported archived
product from its recorded inputs and refuse an unavailable historical compiler.
An independently altered product must fail the exact preview comparison before
a candidate effect.

<a id="DMA-02"></a>

## DMA-02 · Verify the acquired target under its own revision

Registration and deployment are separate. The current archive fence compares
the acquired database with the checkout head's descriptor and builds its
selected-fact expectation with installed metadata. Registration alone can
therefore affect an older target. A non-head migration can commit and only then
encounter the wrong expectation.

Use the approved Alembic revision and frozen products to resolve trusted
expectations for the acquired target's actual predecessor and proposed reached
revision. Reuse the existing candidate identity, revision and predecessor
fences. Resolve expected function bodies, ACLs, roles and selected-fact view
from that revision's trusted descriptor and bound physical metadata. If a
revision inherits an unchanged expectation, establish that through its frozen
lineage. Refuse absent, ambiguous or mismatched expectations before durable
migration. Use PostgreSQL catalog checks and the existing pglast structural
comparison of `pg_get_viewdef` against `selected_fact_query(target_metadata)`.
A revision label alone does not verify the catalog.

Preflight target identity, purpose roles, known predecessor and the frozen
successor expectations before the first durable effect. Under the existing
migration fence, recheck the acquired and reached identities before archive,
admission or activation. Keep these effects separately observable and make
retry consult the exact recorded revision and effects. The report identifies the
verified target and feeds DMA-08. Keep checkout-head verification for authoring
a successor and remove it from target verification.
[Current verifier](../../../python/corpus-structure/src/corpus_structure/semantic/execution_admission.py) ·
[Deployment sequence](../../../python/corpus-structure/src/corpus_structure/schema/model_deployment.py) ·
[Native custody](../../design/D3-database.md#semantic-releases-and-runtime-custody)

**Closure.** Register a different successor and verify the still-valid older
target. Apply an approved non-head candidate on the supported path. Refuse a
wrong endpoint, purpose role, predecessor or catalog before unrelated effects.
Inject failure after migration and establish an exact resume or refusal without
repeating completed effects or activating an unadmitted release. Observe the
actual catalog and pointers independently of the command's report.
