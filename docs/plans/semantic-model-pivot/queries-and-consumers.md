# Semantic queries and consuming interfaces

**Status:** Planned · **Created:** 2026-10-29 · **Proposed.** [Coordinator](../semantic-model-pivot_2026-10-29.md) owns state. Realizes O05 and consumes SP-01 meanings, SP-03 publication and SP-05/SP-07 outputs as needed.

## Target query interface

A query selects a semantic release, data snapshot, occurrence/fact/accepted-value or inferred projection, typed class/property handles, parameters and result demand. Handles resolve against prepared model definitions to shared SQLAlchemy Table/Column objects and composable expressions; they are not unvalidated SQL identifiers. `select`, joins, `exists`, subqueries, aggregates, windows and recursive CTEs retain database optimizer visibility. Domain-specific algorithms may remain ordinary functions using those primitives. No generic query language or custom optimizer is required.

Results carry qualification, evidence, coverage, interpretation/data identity and completion status. Parallel relationships remain separate where occurrence semantics are requested; grouping into facts is explicit. Unresolved references survive joins. Empty incomplete results are unknown, not absence. The required analysis universe is distinct from output selection. Page tokens pin query/parameters, semantic release, snapshot, ordering and inference policy; changing an active project pointer cannot change the next page.

<a id="SP-04"></a>
## SP-04 — Early native write, query and explanation journey

**Input:** working SP-01/SP-03 contracts. **Owner:** semantic query/compiler and database integration.

Build class/property lookup and a minimal evidence-backed query/explanation using the new fixed tables and Core expressions. Start with a newly admitted class, exact typed property and attributed relation absent from the installed initial domain. Submit two occurrences, publish, query both occurrence and fact views, and explain through evidence. Use a fresh database and actual application roles. This is an early integration slice, not a toy in-memory substitute or the completion of O05.

Resolve output types through the release-derived Pydantic/TypeAdapter boundary; preserve strict canonical values and explicit missingness. Do not coerce arbitrary SQL rows into a model while dropping unrecognized qualification. Keep SQL execution and result-schema mapping together so a wrong projection cannot be relabeled with correct metadata.

**Completion:** new declarations are usable without per-class Python code, DDL or regenerated import modules. Independent expected result/evidence sets include an unresolved endpoint, same-source repeated item, wrong-release handle and unknown coverage. SP-04 supplies working read/explain primitives for later producer integration while SP-08 remains responsible for the full current surface.

<a id="SP-08"></a>
## SP-08 — Complete current consumer migration

**Input:** SP-04; SP-07 only for consumers requiring consolidation/derived output; SP-05 for actual exports and analytical evaluation. **Owner:** serving/agent/CLI/evaluation integration.

Migrate all affected current `serve/protocol.py`, `registry.py`, `read.py`, `queries.py`, `journey.py`, `explain.py`, domain query implementations, CLI query/explain/schema/db/export commands and MCP tools. Inventory concrete entry points at execution start, including any dirty source legitimately adopted then. A representative query passing does not discharge the remaining surface. Replace hard-coded old table/key interpretation with semantic query primitives while retaining justified domain-specific algorithms and indexed access paths.

Coordinate agent packets, parsing and submission with SP-06; both producer and UI consume the same admitted boundary models. Migrate intervention records/publication without a hidden direct-write route. Source-backed explanation closes over the same snapshot; derived explanation includes rule and premises. Stale handles, locators and page tokens receive explicit failures rather than silently using a newer interpretation.

Migrate `evaluate/align.py`, `equivalence.py`, scoring/agreement/reference readers and golden submission/storage already present. Keep references out of extraction/consolidation inputs. Ontology mappings, corpus identity, string equality and symbolic/numeric equivalence remain different operations with undecided outcomes where necessary. Do not finish unrelated scoring features from old plans; replace current behavior and add only what establishes pivot correctness.

Use Pydantic runtime envelopes and generated dynamic models for configuration-free semantic boundaries; use Pydantic Settings only for execution configuration as defined in SP-06. Do not create another CLI parser merely because Settings offers one. Exports consume SP-05 projections and identify their semantic/data context.

**Acceptance:** real CLI/MCP dispatch and native query/export/evaluation integrations, with independent reference expectations for qualifiers, coverage, numeric meaning and evidence. Exercise continuation after active-release change, same bytes under changed identity/vocabulary policy, conflict visibility, multiple derivation supports, cancellation and stale submissions. A mocked provider is local protocol evidence only; actual required provider acceptance remains separately named by SP-10.

## Authored SQL and pglast integration

For current authored rules/views/query fragments that remain necessary, use SP-02's pglast admission/diagnostic boundary. Core expression construction remains the normal route. Parse authored SQL once per immutable definition, resolve the supported identifiers and declared dependencies against the binding/MetaData, then execute only the supported read/operation contract under appropriate database privileges. CTE aliases, nested scopes, quoted identifiers and functions require real resolution; a flat relation-name scan cannot establish completeness. Unsupported dependency analysis refuses that authored feature rather than claiming hermetic execution.

Sources: [SQLAlchemy overview](../../libraries/sqlalchemy.md), [pglast overview](../../libraries/pglast.md), [Pydantic overview](../../libraries/pydantic.md), [review O05](../../functional_reviews/semantic-postgresql-model_2026-10-29.md#O05). Keep library mechanics subordinate to the owned semantic contract, without recreating their AST, validation or transaction machinery.
