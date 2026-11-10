# Released domain types and native realization

**2026-11-09 · Proposed recommendations.** Source inspected at `d18183a22`; selected API
inspection is Interface-checked, not runtime qualification. [Discovery](../../library_leverage/libraries/postgresql/discovery/domain-types-and-invariants.md)
supplies the capability inventory. D2 owns released meaning; D3 retains instance authority.

<a id="O01"></a>
## O01 — Carry released distinctions into consumer types

Developers composing reads and calls could distinguish release, occurrence and fact identifiers
before execution. [Generated columns](../../../python/corpus-structure/src/corpus_structure/semantic/_typed_columns.py)
currently expose those distinctions largely as Named[str]. The
[generator](../../../python/corpus-structure/src/corpus_structure/schema/relational.py) uses python_type
although upstream compilation retains enum, range and pattern facts.

Recommend extending that generator with authoritative semantic range/reference bindings, deriving
NewType-style identifiers, finite Literal members and existing released structured-value types where
their meaning survives storage. Generate callable parameters and result construction from those same
declarations. Keep patterns and cross-row constraints as runtime obligations. with_cols supplies no
runtime validation, and broad SQLAlchemy comparison operators may still accept a wrong join: the
selected target must demonstrate which callable/result contracts actually reject consequential errors.

Handwritten aliases recreate authority; pervasive wrapper objects add conversions without necessarily
improving enforcement. Generic JSON remains appropriate for genuinely arbitrary JSON contracts.
Migrate selected public reads, operation calls, constructors and annotations together; remove replaced
handwritten mappings. Bind generated artifacts to complete semantic/physical determinants. Delivery:
a fact ID refused by an occurrence-specific callable, nullable closed-value results preserved, and
one vocabulary member added through regeneration. O01 needs no native-type migration or ORM adoption.

<a id="O02"></a>
## O02 — Typed adaptation and native invariants for richer values

An interval-aware domain or private graph-authoring workflow could accept meaningful values directly
while native constraints protect its real invariants. Prefer Core plus released value definitions,
extending existing codecs and
[CompanionProjection](../../../python/corpus-structure/src/corpus_structure/semantic/companion_projection.py).

For context-free repeated conversion, derive TypeDecorator.process_bind_param/process_result_value
from the released definition. Preserve JSON/ARRAY coercion through coerce_compared_value; cache_ok
requires stable cache-key state. Identity, normalization and context-sensitive admission remain explicit
operations. [Custom-type contracts](https://docs.sqlalchemy.org/en/21/core/custom_types.html).

For a selected structured-value consumer, scoped Psycopg Dumper/Loader, CompositeInfo/register_composite,
enum/range adapters can avoid mechanical intermediate representations. A non-sequence dataclass needs
make_sequence for dumping as well as construction. Registration does not update existing connections.
Bind adapters to native type/database generations and connection creation; missing OIDs/layouts refuse.
[Selected composite source](https://github.com/psycopg/psycopg/blob/3.3.6/psycopg/psycopg/types/composite.py).

A reusable scalar invariant can justify DOMAIN; nonoverlapping validity intervals can justify native
ranges plus ExcludeConstraint. Existing generated CHECK/FK/membership enforcement remains preferable
where sufficient. Native enums cannot replace release-scoped vocabulary membership generally, and
range canonicalization must not overwrite source bounds/spelling. Domain null/revalidation behavior
needs explicit treatment. [Domains](https://www.postgresql.org/docs/18/sql-createdomain.html),
[ranges](https://www.postgresql.org/docs/18/rangetypes.html).

A coherent private graph editor is a credible alternative: imperative mappings over generated Tables,
composite(), association objects and operation-scoped Session can coordinate draft edits. Select it
only where identity map/cascades/loading serve that whole workflow. Published immutable products
must not acquire ambient mutable lifecycles. Row factories are the smaller constructor-only read
alternative. [Composites](https://docs.sqlalchemy.org/en/21/orm/composites.html). ORM loaders, versioning,
write-only collections, registry hooks and frozen-result merging belong to that selected graph
lifecycle, not independent adoption projects.

The first richer value/editor is a scope decision, not assumed demand. Deliver its round trip,
invalid native write, rollback and post-migration read. Migrate Python, COPY/Arrow, catalog and
migration consumers together. Remove replaced conversions while preserving independent guards.
Native type generation/session replacement couples this opportunity to O08/O11/O13; O01 is independent.
