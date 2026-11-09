# SQL analysis and source fidelity

**Discovery · 2026-11-09.** Local observations are source-inspected at `51b3c28de`;
capability details are Interface-checked only where the cited selected source was inspected.
All candidate benefits and research priorities are **Proposed**. See the
[family briefing](../briefing.md) for environment, scope and evidence limits. These are research
leads, not applicability verdicts or selected replacements.

## Current integration

[PreparedSQL](../../../../../python/corpus-structure/src/corpus_structure/semantic/prepared_sql.py) already owns parse reuse, private clones, original
statement slices, grammar-aware splitting, parser provenance and Unicode displacement conversion.
[Authored SQL admission](../../../../../python/corpus-structure/src/corpus_structure/semantic/authored_sql.py) combines a pglast Visitor/approved syntax
profile with restricted native catalog/type/access inspection. Parsing is not authorization.
[Signature extraction](../../../../../python/corpus-structure/src/corpus_structure/semantic/native_function_signatures.py) distinguishes overloaded
input identities from OUT/TABLE results. [SQL body authoring](../../../../../python/corpus-structure/src/corpus_structure/semantic/native_sql_body.py)
constructs SQL-standard envelopes; catalog observation remains independently owned.

[Projection analysis](../../../../../python/corpus-structure/src/corpus_structure/semantic/projection_analysis.py) already uses MappingSchema, strict
qualification, annotate_types(overwrite_types=False), build_scope, lineage(None) and exp.expand.
It supplies its own cycle/CTE/opaque/helper checks and records value and relational dependencies
separately. Enabling these APIs is not a new opportunity; extending their useful coverage may be.

## Research shortlist

| State | Mechanism and concrete seam | Proposed value | Defeating condition; next question |
| --- | --- | --- | --- |
| Candidate underuse | lineage(on_node=...), Node.payload and existing AST model-origin metadata | Retain typed relationship/origin annotations as nodes are built instead of reconstructing them afterward | Hooks cannot invent helper semantics or execution provenance. Do origins survive copies, qualification, nested/repeated expressions and all-output traversal with the required relationship identity? |
| Candidate underuse | Scope.sources/traverse_scope/find_all_in_scope and scope-aware find_tables versus local table/CTE collection | Delegate lexical resolution that local walkers reconstruct | Native helpers return sets and may omit occurrence/role information. Can they preserve missing sources, shadowing, multiplicity, correlation and materialization barriers? |
| Candidate underuse | Schema.get_udf_type/udf_mapping, expression_metadata and protected declared .type annotations | Share helper result typing from model declarations | MappingSchema's lookup is name-based, not PostgreSQL overload/argument/body binding. Can it discharge any current repeated fact without losing the exact helper contract? |
| Conditional | DataType representations and structured JSONPath/nested-field analysis | Preserve model/type/path distinctions through projected JSONB and arrays | Representability differs from inference and PostgreSQL semantics; JSON is not STRUCT. Which current recipe path loses structure that a consumer actually needs? |
| Candidate underuse | pglast shared AST facts, visitor actions/Ancestor helpers and printer precedence/name primitives | Remove residual generic traversal, tuple rebuilding or SQL parenthesization | Shared nodes must remain immutable and printer support complete. Which native authoring fragment has a fully supported structural replacement? |
| Conditional | SQLGlot diff, selected canonicalization, error metadata and serialization; pglast source spans/comments | Improve a concrete impact explanation or precise diagnostic | AST changes are not semantic equivalence and rewritten positions are not original source maps. What existing impact/diagnostic consumer cannot be served by current products? |

## Contract details that change the research

Installed SQLGlot30.27.0 lineage exposes on_node/Node.payload. Its hook runs after downstream
population; caller data is not independently validated provenance. MappingSchema.get_udf_type
provides return typing, not native signature binding. Expr and Expression are not aliases.
A package-wide selected Python source search found get_udf_type references in schema/type declarations,
not calls from annotate_types. Adding udf_mapping alone therefore does not establish Anonymous
call typing. Retain explicit checked helper .type annotations unless a real integration need justifies
a custom expression_metadata annotator. Likewise, current checked recipe IR lacks general subquery
expressions: scope-aware clause traversal is a credible extension seam, not an established nested-query
bug. Existing expansion collision checks remain necessary even with scope-aware table collection.
Structured placeholders insert AST structure/literals and are distinct from driver parameter binding.

pglast8.7 Visitor.__call__ treats a None action as Continue; directly driving Visitor.iterate has
a different action protocol. Use high-level traversal unless a real controller needs the lower API.
AST construction/type checking does not establish grammatical placement or catalog correctness.
ReferencedRelations deliberately loses occurrence/role multiplicity. Source APIs have different
byte/character/end conventions; no universal span or lossless rewritten source map is promised.

## Conditional territory and retention

Keep procedural parse_plpgsql dictionary inspection conditional on an actual unresolved native-body
dependency question. Native JSON/Protobuf parse/deparse interchange needs a version-matched
cross-language consumer. Fingerprints can group query shapes but cannot identify semantic facts or
partitions; printer round trips cannot establish native admission. SQLGlot optimizer/dialect passes,
PIVOT output reasoning, custom dialects/plugins and source expansion deserve a bounded operator or
portability need. Full Python execution, SQLFrame and acceleration have no selected replacement
consumer here. All remain represented in [coverage](coverage.md), rather than silently omitted.

## Sources and next assessment

[pglast overview](../../../../libraries/postgresql/pglast.md) and [sqlglot overview](../../../../libraries/postgresql/sqlglot.md), including all addenda.
[SQLGlot30.27 lineage](https://github.com/tobymao/sqlglot/blob/v30.27.0/sqlglot/lineage.py),
[schema](https://github.com/tobymao/sqlglot/blob/v30.27.0/sqlglot/schema.py),
[SQLGlot scope](https://github.com/tobymao/sqlglot/blob/v30.27.0/sqlglot/optimizer/scope.py),
[type annotator](https://github.com/tobymao/sqlglot/blob/v30.27.0/sqlglot/optimizer/annotate_types.py),
[pglast8.7 visitors](https://github.com/lelit/pglast/blob/v8.7/pglast/visitors.py).

First compare lineage hooks and native scope helpers against the current recipe analysis using
independent expected origins, predicate influences and explicit unknowns. A later focused probe
should include CTE shadowing/correlation and an opaque helper, not merely a happy-path SELECT.

Additional conditional APIs remain useful only at a concrete composition/diagnostic seam:
replace_placeholders inserts structured SQL rather than bound driver parameters; sqlglot.meta,
replace=false and sqlglot.anonymous influence parsing/replacement but do not supply model authority.
exp.Command marks opaque statement content; current analysis refuses it. Python AST == tests
structural equality whereas .eq() constructs a SQL predicate. In pglast8.7 parser.normalize and the
serialization enum_name option are unavailable; get_postgresql_version returns a two-element tuple.
Do not apply similarly named formatting commands or examples from other releases as these APIs.
