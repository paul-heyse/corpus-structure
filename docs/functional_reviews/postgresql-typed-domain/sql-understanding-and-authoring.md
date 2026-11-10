# Attributed SQL understanding and authoring

**2026-11-09 · Proposed recommendations.** Source inspected at `d18183a22`; selected API contracts
are Interface-checked without native qualification. [Discovery](../../library_leverage/libraries/postgresql/discovery/sql-analysis-and-source-fidelity.md)
retains capability coverage and version corrections.

<a id="O03"></a>
## O03 — Explain projections through attributed dependency occurrences

Release reviewers could ask why an output depends on a field, which predicate changes membership,
and which consumers a change reaches. [Projection analysis](../../../python/corpus-structure/src/corpus_structure/semantic/projection_analysis.py)
already qualifies, annotates, scopes and computes lineage. Its product separates value/relational
dependencies; operation_reporting._projection_impact already compares them. The extension is an
inspectable explanation beyond changed tuples, not first-time lineage adoption.

Recommend retaining checked model-origin/occurrence data during lineage construction through
lineage(on_node=...) and Node.payload, with Scope.sources and scope-aware traversal. The hook runs
after downstream construction; its payload is caller annotation, not validated provenance. Derive
attribution from checked recipe/source/relationship bindings. Repeated references sharing endpoints
and output versus filter/join influences retain separate identity and kind.

Emit versioned explanation detail through the existing
[analysis-product owner](../../../python/corpus-structure/src/corpus_structure/semantic/projection_analysis_products.py),
including analyzer/configuration determinants, source/model references and explicit unknowns. Expand
detail on demand rather than retaining every path. Keep checked helper .type with overwrite_types=False:
udf_mapping alone does not feed selected annotate_types or establish native overload/body binding.
[Selected lineage](https://github.com/tobymao/sqlglot/blob/v30.27.0/sqlglot/lineage.py),
[scopes](https://github.com/tobymao/sqlglot/blob/v30.27.0/sqlglot/optimizer/scope.py).

Current tuples remain an adequate presentation alternative where detail has no consumer; a new
provenance store would add custody. Replace post-walk reconstruction only if hooks preserve its
obligations. Keep expansion collision and opaque-helper safeguards. Migrate archived product readers,
impact comparison and human/machine reports together; unavailable old detail remains unavailable.
Deliver filter-versus-output edits, two occurrences sharing endpoints and an unknown helper body.
Metadata survival through copies/qualification, CTE shadowing and correlation are settling cases for
the selected explanation shape. This has immediate consumers and precedes broad language expansion.

<a id="O04"></a>
## O04 — Source-aware authoring, richer queries and controlled portability

A release author could inspect a candidate change, locate diagnostics, understand structural edits
and affected consumers before admission. Existing
[PreparedSQL](../../../python/corpus-structure/src/corpus_structure/semantic/prepared_sql.py) already
preserves source, slices, version and Unicode coordinates;
[authored admission](../../../python/corpus-structure/src/corpus_structure/semantic/authored_sql.py)
and [native SQL bodies](../../../python/corpus-structure/src/corpus_structure/semantic/native_sql_body.py)
retain independent native binding and Core/pglast composition.

Recommend a candidate-authoring report composed from those owners and O03: original excerpts,
structural SQLGlot diff edits, dependency explanations and separately reported native admission.
AST diff explains structure, not equivalence. Transform private AST clones using pglast visitors and
precedence-aware printers; rewritten coordinates are not original positions. Structured placeholders
insert syntax and differ from bound driver parameters.
[Selected diff](https://github.com/tobymao/sqlglot/blob/v30.27.0/sqlglot/diff.py).

Develop three conditional branches:

- **Richer model-bound query forms:** a concrete nested, aggregate/window, recursive, PIVOT or JSON-path
  consumer can extend the finite recipe IR with Core lowering and native scope/qualification. Preserve
  output shape, correlation and membership effects. Current IR lacks general subqueries; this is a
  new capability, not an established current nested-query bug.
- **Procedural understanding:** pglast parse_plpgsql can expose helper-body structure and candidate
  dependencies for an investigation. It returns dictionaries rather than ordinary typed ASTs. Dynamic
  SQL, exceptions and runtime binding retain explicit unknowns; no complete authorization/dependency
  analysis is promised. [Selected parser](https://github.com/lelit/pglast/blob/v8.7/pglast/__init__.py).
- **Portability/query laboratory:** pinned transpile(read, write, unsupported_level=RAISE), declared
  source expansion and selected optimizer passes can support offline export or alternative-query
  research. Qualify generated SQL and compare required destination semantics. Specialized transforms,
  custom dialects/plugins, pipe syntax, temporal formats, JSON/Protobuf interchange and fingerprints
  belong to a selected integration. Fingerprints never own semantic identity. PythonExecutor,
  SQLFrame and compiled acceleration remain alternatives for a selected research workload, not a
  production replacement justified by catalogue availability.

Start with diagnostics/impact; select other branches on their resulting workflow. Keep admission
until a replacement profile is qualified, migrating recipe consumers, archive readers and native
bodies coherently and retiring replaced builders. Deliver Unicode diagnostics, a predicate edit
with affected consumers, a shadowed correlated query, dynamic procedural SQL reported unknown, and
portability refusal rather than silent approximation. Arbitrary authored-query support changes the
approved profile and needs a concrete architecture decision.

Retain selected-version distinctions: exp.Command is opaque; .eq constructs SQL whereas Python ==
is structural; meta directives do not establish meaning; pglast8.7 lacks parser.normalize and the
serialization enum_name option. No recommendation depends on these unavailable APIs.
