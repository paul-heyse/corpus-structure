# Model changes and target-bound deployment

**Proposed.** Companion to the [CLI operations coordinator](../cli-operations_2026-11-07.md).
Owns CLI-04 and CLI-05, with semantics in D2, database authority in D3 and transport in D8.
The model operation is callable from Python. Installed adapters consume the same request and result.
Keep `ci model check` on the owned `just model check` route. The new typed change composition is
an application operation.

<a id="CLI-04"></a>
## CLI-04 · Preview a declared change

Accept a canonical declaration diff against an identified baseline, or a typed request for a
supported repeatable change. Use a validated file or stdin, or a stored equivalent identity.
Require irreducible intent such as rename map, key consequences, conversion or a breaking-change
decision. Use `schema.change.diff()`, `derived()` and `check()` to compare declarations and
validate the requested revision. Use `semantic.regeneration.prepare_packs()` and
`semantic.operation_reporting.compare_semantic_releases()` for the composed layer. The comparison
already accepts prepared values. Expose an archived-to-local comparison without admitting the local
release. Inventory applicable generated and handwritten consumers separately. Declare unknown
dependency coverage and keep source locations where available.
[Declaration change owner](../../../python/corpus-structure/src/corpus_structure/schema/change.py) ·
[Prepared semantic comparison](../../../python/corpus-structure/src/corpus_structure/semantic/operation_reporting.py)

Refactor the local generation boundary so the full revision request and log validate before any
write. The current `schema generate` can write Stage A outputs before `record_root()` refuses a
revision. Reuse load/check/render and compare generated outputs in memory or staging. Preview
returns the declared and generated patch, compatibility and change record, applicability by effect,
independent checks and unresolved impact. Bind it to worktree/source, exact inputs, tool and generator
versions, and the native predecessor where native authoring is applicable. A provenance- or
description-only change can settle without DB access or unnecessary generation. Classify whether
a change affects model revision, semantic release or runtime binding. CLI-05 consumes this result
and its bindings. Where the reviewable result becomes an approved pending change, attach its
custody hold before any dependent work starts.
[Generator entry point](../../../python/corpus-structure/src/corpus_structure/schema/__main__.py)

### Introspection and edit decisions

Canonical generation remains the selected realization for derived representations. Qualify
narrow source tools against actual consumers. Candidate matches and lexical bindings establish
what they observed. Dynamic references, external consumers and semantic compatibility retain
explicit unknowns or domain-owner findings.

| Mechanism and disposition | Intended use, limit and adoption trigger |
|---|---|
| Python 3.14.10 `ast.parse()`, `ast.NodeVisitor`, `ast.get_source_segment()`, `symtable.symtable()` | Use for bounded read-only inventory of declarations, annotations and lexical bindings when needed. Parse and compile changed syntax in the pinned interpreter. Locations and lexical resolution aid review without importing target modules. Use an independently selected fixture with shadowing and dynamic references to establish what remains unknown. [AST API](https://docs.python.org/3.14/library/ast.html#ast.NodeVisitor) · [Symbol table API](https://docs.python.org/3.14/library/symtable.html#symtable.symtable) |
| Existing ast-grep 0.51.0 `scan --json=stream` | Select for on-demand consumer shape searches using rule fields and bounded relational constraints. Report scope, skipped inputs and tool outcomes. If proposing edits, inspect replacement offsets and account for overlapping matches. Experimental outline serves navigation only. [Scan options](https://ast-grep.github.io/reference/cli/scan.html) · [Rule composition](https://ast-grep.github.io/reference/rule.html) |
| LibCST `parse_module(bytes)`, `MetadataWrapper`, `ScopeProvider` or `QualifiedNameProvider`, `ContextAwareTransformer` or `CodemodCommand` | Conditional on a recurring, explicitly mapped handwritten Python edit requiring trivia preservation. Use matchers, import helpers and skip diagnostics. Qualify repository Python syntax, byte round-trip, exact expected output, and ambiguous import/re-export refusal before selecting an exact pin. [Codemod API](https://libcst.readthedocs.io/en/latest/codemods.html) · [Metadata API](https://libcst.readthedocs.io/en/latest/metadata.html) · [Parser API](https://libcst.readthedocs.io/en/latest/parser.html) |
| ast-grep-py `SgRoot`, `SgNode.find_all()`, `SgNode.commit_edits()` | Conditional on repeated in-process correlation on the same Python-owned source snapshot outperforming the integration simplicity of existing CLI discovery. Qualify version and grammar, no-match and skipped-input outcomes, overlap, and character offsets against CLI byte offsets before pinning. [Python binding API](https://ast-grep.github.io/guide/api-usage/py-api.html) |
| Tree-sitter Python binding `Query` and `QueryCursor.matches()` | Conditional on a concrete mixed-language scenario where paired field captures are needed. Record grammar/version, source snapshot, parse recovery, locations and unsupported or truncated coverage. Qualify each grammar and compare with existing discovery. A persistent index requires a demonstrated repeated workload. [QueryCursor API](https://tree-sitter.github.io/py-tree-sitter/classes/tree_sitter.QueryCursor.html) |
| FastMCP 4.1.3 typed `@mcp.tool` and `ToolResult` | Use `NativeSourceRequest` and `inspect_native_source()` as the shared CLI/MCP operation control. Project one changed field and one typed refusal through installed CLI and fresh stdio MCP. New model-changing MCP tools are outside this selected scope. The generated server-backed Cyclopts CLI is a candidate only if remote tool access itself becomes required. [FastMCP tools](https://gofastmcp.com/docs/servers/tools) · [Shared source owner](../../../python/corpus-structure/src/corpus_structure/serve/native_source.py) |

**Acceptance.** Preview an additive SQL-visible field, a rename without then with explicit mapping,
and a provenance-only change. Verify applicable effects and generated diffs against independent
expectations. The provenance case avoids DB access. A rejected revision leaves generated files and
the log untouched. An archived-to-local comparison leaves release/archive state untouched.
Use the native165 relation-retirement case to trace affected Reader, CLI, MCP and detached
consumers. Verify any chosen introspection tool's reported gaps.
[Native165 repair](../witnessed-corpus-enrichment_2026-11-05.md#repair-disposition--2026-11-07)

<a id="CLI-05"></a>
## CLI-05 · Apply the approved preview and compose explicit deployment

Apply by exact preview ID. Revalidate source digests, worktree and approved paths, generator/tool
bindings and the applicable native predecessor before their write boundaries. Stage the complete
deterministic patch and record each settled file effect. Refuse stale or concurrently edited
inputs before the affected write. When interrupted, keep the staged patch and report partial
settlement. A retry accepts an already-settled effect only when its exact expected content is
present, revalidates unsettled work and preserves concurrent edits. Whole-worktree atomicity is
outside the supported guarantee. Move the generation callers through the same validation boundary
and remove any bypass that can write before revision validation.

For a native effect, reuse `prepare_series_candidate()`, native object validation and the
existing artifact materialization. Run authoring in rollback-only maintenance scope on the
persistent configured development DB. Use Alembic **1.20.1**
`MigrationContext.configure(connection=…, opts=…)` and `autogenerate.produce_migrations(context, metadata)`
inside that owner with existing comparison settings and native SQL checks. Autogeneration provides
a structured migration candidate. Native retirement, exact predecessor and admission depend on
repository-owned checks and frozen artifacts. Publish a managed candidate with its immutable
predecessor, migration and determinant bindings. An optional output path is delivery of that
artifact. Preserve distinct identities for the change, candidate, revision, semantic release
and runtime binding.
[MigrationContext API](https://alembic.sqlalchemy.org/en/latest/api/runtime.html#alembic.runtime.migration.MigrationContext.configure) ·
[Autogenerate API](https://alembic.sqlalchemy.org/en/latest/api/autogenerate.html#alembic.autogenerate.produce_migrations) ·
[Native candidate owner](../../../python/corpus-structure/src/corpus_structure/semantic/native_candidate.py)

Deploy only when explicitly requested against a resolved target and approved change. Compose
existing migration, archive/admission and verification operations under their current roles.
A later failure reports which stages settled and leaves resumable evidence for the exact target
and predecessor. Activation uses the release owner's compare-and-set path and explicit intent.
Selecting a completed run remains a separate explicit domain effect. Runtime-only repairs keep
semantic release identity when meaning and output contracts are preserved. Retire replaced
destination-required authoring and manual multi-step bypasses once installed callers use the
same managed owner. Preserve intentional lower-level recovery tooling.
[Release authority](../../../python/corpus-structure/src/corpus_structure/semantic/releases.py) ·
[Database authority](../../design/D3-database.md)

**Acceptance.** Exercise additive candidate creation and native retirement against real PostgreSQL,
with the intended persistent development authoring target and rollback evidence. Demonstrate
a stale file, duplicate revision, mismatched determinant and wrong predecessor before their
effects. Interrupt after a settled file effect and after migration but before admission. Resume
by exact evidence, preserving concurrent edits. Exercise explicit activation and wrong-role
refusal. A runtime-only correction keeps the release ID. Verify Reader, installed CLI, fresh
MCP and detached consumers wherever the approved change affects their contract.
