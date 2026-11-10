# Authoring against the effective released model

**Proposed functional judgment, 2026-11-10.** [Shared baseline](../domain-data-model_2026-11-10.md).
Sources: [DDM-01/02](../../library_leverage/libraries/domain-data-model/briefings/semantic-declarations.md)
and [DDM-03](../../library_leverage/libraries/domain-data-model/briefings/executable-boundaries.md#ddm-03).

<a id="O01"></a>

## O01 — A release-scoped contract explorer and authoring workflow

**Recommend.** The operator and coding agents should be able to ask: under this release, what
may I construct, which operation consumes it, and which constraints actually execute?
Today these answers exist across authored modules, normalized definitions, generated schemas,
operation explanations and selected exports. A developer adding a recognizer or scientific
record must connect those sources manually. A bounded contract reader could expose effective
class/property/operation meaning and validate a candidate without initializing ingestion,
model assets or native publication.

**Resulting interaction.** Select an explicit release and a class, property or operation.
Inspect inherited range/cardinality, bounds, omission/presence, aliases, vocabulary membership,
related operations, physical correspondence and admitted enforcement scope. Obtain an illustrative
input skeleton with unresolved required values distinguished from actual defaults. Follow the
same source/release through validation and operation explanation. Optional rendered reference
pages could give model authors a browsable view; executable support must come from products.

**Existing foundation.** [PreparedRelease](../../../python/corpus-structure/src/corpus_structure/semantic/types.py)
already supplies indexes, demand-built adapters, `property_adapter`, structural/accepted
construction and validation/serialization schemas. `semantic_server.py` exposes release-bound
operation explanation; `serve/review_bundle.py` exports selected contracts. `prepare.py` has
effective class/range preview. The new value is an integrated, discoverable authoring interaction,
not a claim these representations or operation reports are absent.

**Preferred realization.** Extend current release/operation readers and CLI/MCP owners with
bounded named reads. Compilation continues using SchemaView contextual induction and closed
imports; consumers inspect normalized immutable products. Existing source-relative URI/collision
checks remain. The operation-call compiler has a distinct physical correspondence universe,
including provisional PTD fixes: share preparation facts only when their semantics coincide,
rather than merging semantic ranges and physical native kinds by API similarity.

LinkML `DocGenerator` supports class/slot/enum/type/subset/index templates and selected import
mapping (installed `generators/docgen.py:93–127,179–207,230–245`). It can render authored metadata
and diagrams, augmented with effective product support. Generic OpenApiGenerator instead uses
an endpoint/security template and separate schema generation (`openapigen.py:96–118`); it
does not establish parity with the admitted boundary. OpenAPI/GraphQL is conditional on an actual
service contract, not the preferred realization of this local authoring capability.

**Alternatives.** Existing Python/source navigation remains sufficient for compiler internals.
Native LinkML docs alone are useful authored reference but omit admitted execution distinctions.
An independent registry or universal modeling application would duplicate authority and add
unnecessary lifecycle. Prefer bounded current-owner reads with optional generated documentation.

**Relationship-authoring facet.** Existing `RelationshipDefinition` and `EndpointRole` already
own richer occurrence/qualification semantics. Native `represents_relationship` and
`relational_role` could help generic tooling discover roles, but must preserve that authority.
The discovery's broad unused classification needs qualification: the compiler already admits
`unique_keys`, selected `value_presence`, inverse, symmetric and transitive semantics. Native
ordered/unique collection and attributed-role constructs remain separate profile-expansion
candidates. Add one only for a selected relationship/collection with faithful native/graph/runtime
lowering; metamodel maturity and generator coverage remain material conditions.

**Delivery.** Inspect an inherited bound and its source without manually reading the closure;
distinguish shape from accepted-value obligations; inspect class-valued operation results and
their physical correspondence; read an archive without recompiling through today's model;
unsupported required features report located refusal. Skeletons must not fabricate meaningful
values. D2/D8 own the new read interface; selected profile expansion needs its explicit decision.

## Additional authoring and interoperability directions

SchemaBuilder/Schemasheets and generated data-entry templates could help researchers author
candidate records or domain declarations. Choose one actual authoring activity; flat spreadsheet
templates do not supply complete source/relationship enforcement. All candidates enter through
ordinary release-bound construction and protected publication.

Grammar generation, renderer/JS runtime and provider schemas could improve candidate previews
or client tooling under O01/O11. Preserve the model/grammar/runtime binding; syntactic output is
not scientific support. A Rust/PyO3 detached inspector or specialized kernel is a credible future
consumer, but current starter Rust code does not establish that demand or generated-validation
parity. Keep these conditional until a selected consumer can preserve presence, recursion,
qualification and identity. No general authoring service or replacement workflow engine is selected.
