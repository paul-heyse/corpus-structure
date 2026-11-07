# Model changes and target-bound deployment

**Accepted target.** Companion to the [CLI operations coordinator](../cli-operations_2026-11-07.md).
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
revision. First extract the pure preparation boundary in the canonical owner. Reuse load/check/render
and compare generated outputs in memory or staging. Both the preview and `just model generate`
use that boundary. Stage A artifacts and the revision log are written only by the apply path
after preparation succeeds. This slice can proceed before managed-result delivery or optional
source tools. Installed preview publishes through CLI-02. Preview
returns the declared and generated patch, compatibility and change record, applicability by effect,
independent checks and unresolved impact. Bind it to worktree/source, exact inputs, tool and generator
versions, and the native predecessor where native authoring is applicable. A provenance- or
description-only change can settle without DB access or unnecessary generation. Classify whether
a change affects model revision, semantic release or runtime binding. CLI-05 consumes this result
and its bindings. Where the reviewable result becomes an approved pending change, attach its
custody hold before any dependent work starts.
[Generator entry point](../../../python/corpus-structure/src/corpus_structure/schema/__main__.py)

### Introspection and edit decisions

Canonical generation remains the selected realization for derived representations. Attach
bounded candidate discovery to the existing semantic impact report's declared consumers and
unknowns. Candidate evidence carries source snapshot/digest, analyzer, rule and grammar where
applicable, coordinates and units, and inspected scope. Distinguish inspected no-hit, skipped,
unresolved, failed and truncated. A structural match may locate a consumer for review. Domain
and native owners establish semantic impact and retirement. An empty search provides no authority
to remove an unresolved consumer.
[Existing semantic impact reporting](../../../python/corpus-structure/src/corpus_structure/semantic/operation_reporting.py)

| Mechanism and disposition | Intended use, limit and adoption trigger |
|---|---|
| **Selected** Python 3.14.10 `ast.parse(type_comments=True)`, `ast.NodeVisitor`, `ast.get_source_segment()` | Inventory declarations and call sites in scoped Python files without imports. Use `symtable.symtable()` only for lexical claims and preserve ambiguity when it cannot be uniquely joined to a node. Account for decorators, comprehension/class scopes and type parameters. Use `compile(..., "exec", dont_inherit=True)` for an independent compile-only check, with optional `ast.compare()` for structural comparison. Handwritten edits must retain trivia. [AST](https://docs.python.org/3.14/library/ast.html#ast.get_source_segment) · [Symbol tables](https://docs.python.org/3.14/library/symtable.html) · [Compile](https://docs.python.org/3.14/library/functions.html#compile) |
| **Selected** ast-grep 0.51.0 `scan --json=stream` | Use explicit scope and rules, contextual `pattern` selectors and ordered relational `all` when they simplify discovery. `--inspect entity` can report execution details subject to input mode. Experimental outline serves navigation. Normalize and test CLI byte offsets against Python-facing coordinates before combining observations. [Scan](https://ast-grep.github.io/reference/cli/scan.html) · [Context selectors](https://ast-grep.github.io/advanced/pattern-parse.html) · [Composite rules](https://ast-grep.github.io/guide/rule-config/composite-rule.html) |
| **Conditional** ast-grep-py 0.51.1 `SgRoot` and `SgNode.find_all()` | Investigate only for several related queries over one pinned Python snapshot where repeated CLI traversal materially matters. Compare exact grammar, custom metavariables, skipped inputs, output and offset conversion. Keep advanced transformations and rewriting conditional on an independently supported edit case. [Python API](https://ast-grep.github.io/guide/api-usage/py-api.html) · [0.51.1 release](https://github.com/ast-grep/ast-grep/releases/tag/0.51.1) |
| **Conditional** Tree-sitter 0.26.0 `Query` and `QueryCursor.matches()` | Investigate a concrete paired-field or recovery workload beyond the existing route. Preserve capture pairing, grammar identity, recovery and termination. `did_exceed_match_limit` describes active match pressure. Bound input, output and duration independently. The installed 0.26.0 binding with Python grammar 0.25.0 segfaulted before its progress callback. Use an isolated worker with an external deadline or qualify a corrected exact binding before using the callback. Persistent indexing requires a repeated workload. [Query cursor](https://tree-sitter.github.io/py-tree-sitter/classes/tree_sitter.QueryCursor.html) · [Tagged callback](https://github.com/tree-sitter/py-tree-sitter/blob/v0.26.0/tree_sitter/binding/query_cursor.c#L128-L145) · [Probe](../../design_review/evidence/2026-11-07_cli-typer-028/README.md) |
| **Conditional** LibCST 1.9.0 `RenameCommand(CodemodContext, old_name, new_name)` | Try the shipped command before a custom transformer for a recurring handwritten edit with an explicit qualified mapping. Use `parse_module(bytes)`, `MetadataWrapper`, qualified-name metadata and import helpers on allowlisted uniquely supported occurrences. Name membership can match ambiguous candidates and some relative/star imports are skipped. Keep the explicit manual patch route for ambiguous or unsupported cases. `ByteSpanPositionProvider` reports UTF-8 units, so convert for other encodings. Require exact expected diffs and source-byte matches before apply. [Tagged rename](https://github.com/Instagram/LibCST/blob/v1.9.0/libcst/codemod/commands/rename.py#L204-L300) · [Name metadata](https://github.com/Instagram/LibCST/blob/v1.9.0/libcst/metadata/name_provider.py#L25-L71) · [Byte spans](https://github.com/Instagram/LibCST/blob/v1.9.0/libcst/metadata/span_provider.py#L87-L111) |

A qualified Python rename differs from a model name mapping and cannot choose migration, admission or
release effects. Keep broad rewrites, annotation reconciliation, incremental storage and new grammars
conditional on a demonstrated workload. Use the [CLI-06 shared source operation](corpus-and-operations.md#shared-refusals-and-read-authority)
for Reader, CLI and MCP consumer controls.

**Acceptance.** Preview an additive SQL-visible field, a rename without then with explicit mapping,
and a provenance-only change. Verify applicable effects and generated diffs against independent
expectations. The provenance case avoids DB access. A rejected revision leaves generated files and
the log untouched through both preview and the existing generator entry. An archived-to-local
comparison leaves release/archive state untouched. Check Unicode and CRLF, decorators, shadowing,
alias-only and excluded inputs, and parse-valid/compile-invalid text. For a qualified rename, also
test re-exports, relative/star imports and ambiguous references against independent expected diffs.
Use the native165 relation-retirement case to trace affected Reader, CLI, MCP and detached
consumers. Verify the old native signature is absent with the native authority, independent of
candidate discovery. Verify any chosen introspection tool's reported gaps.
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

The installed native path stages the wrapper with the candidate. Inspect it by managed ID,
then use `ci model change register CANDIDATE` to install the exact files in the checkout. The
registration writes the wrapper last and accepts exact already-installed bytes on retry.
It binds `ScriptDirectory.get_current_head()` to the approved predecessor and installs no database
effects. `ci model change deploy CANDIDATE` checks the registered revision and frozen artifact
hashes at the migration boundary. Use the optional `CORPUS_DEPLOYMENT__URL` profile and its
purpose credentials to configure a distinct destination. A request can pin `deployment_profile`
to `deployment` or `development`. Native authoring uses the working database profile and checks
its exact predecessor. Endpoint pins identify the declared URLs, including routing parameters.
[Alembic ScriptDirectory](https://alembic.sqlalchemy.org/en/latest/api/script.html#alembic.script.ScriptDirectory)

Deploy only when explicitly requested against a resolved target and approved change. Compose
existing migration, archive/admission and verification operations under their current roles.
A later failure reports which stages settled and leaves resumable evidence for the exact target
and predecessor. Publish this from the operation owner to the
[CLI-02 diagnostic view](managed-results-and-testing.md#action-driven-diagnostics) for resume by ID. Activation uses the release owner's compare-and-set path and explicit intent.
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

### Completion audit follow-up

**F02 · Approved effects and semantic inputs.** Preview records a canonical patch and can pin
a prepared release, and candidate preparation refuses a differing release. The preview still
leaves effect applicability and required checks to the request's native and deployment flags.
The existing canonical change routes do not feed the approved preview. A declaration change
does not produce an inspectable account of its applicable generated, native, admission and
consumer effects. Bind the independently classified effects and release determinants to the
reviewed change and use them when composing apply and candidate. Exercise additive, mapped and
provenance-only controls. Preserve the existing zero-write refusal and exact file recovery.
[Preview and staged effects](../../../python/corpus-structure/src/corpus_structure/schema/model_change.py#L118) ·
[Canonical change routing](../../../python/corpus-structure/src/corpus_structure/schema/change.py#L474) ·
[Candidate command](../../../python/corpus-structure/src/corpus_structure/cli/model.py#L239)

**CLI-CA03 · Consumer discovery.** The bounded locator reports AST and ast-grep hits for tokens
from canonical declaration changes. It does not establish lexical ambiguity, independently
compile affected Python or trace the approved semantic impact through declared consumers.
Archive-only comparison can produce no discovery because it has no changed canonical tokens.
Report structural versus semantic coverage, tool/input identity and ambiguity explicitly.
Qualify the accepted coordinate, compile-only and native165 retirement controls. Preserve the
manual patch route and the existing conditions on additional codemod tools.
[Locator](../../../python/corpus-structure/src/corpus_structure/schema/model_discovery.py#L15) ·
[Preview consumer selection](../../../python/corpus-structure/src/corpus_structure/schema/model_change.py#L196)

**F02a · Native authoring, registration and target fence.** Both installed authoring routes
omit retirement and recreation from their request to the owner, even though the owner requires
explicit retirement for general removed identities. The preview stages the core/system model,
while native authoring reads the separately owned physical model. The command does not convey an
approved physical change to that owner. Deployment verifies the registered wrapper's
bytes only when its basename is the generated name. A suffixed wrapper with matching IDs and
product digests can run different code. The target fingerprint hashes the declared URL while
libpq may fill omitted routing from its environment, so an equal fingerprint does not prove
acquired target identity. Bind applicable retirement, recreation and executable migration bytes,
then prove the same authorized acquired target before maintenance, admission and verification
effects. Use the registered generated wrapper in an installed additive/retirement journey and
exercise a renamed/changed wrapper, routing substitution, predecessor mismatch and interrupted
replay. The retained isolated PostgreSQL rehearsal used a historical wrapper and called activation
at the owner, which remains valid at that scope. Post-deploy command target continuity belongs to
[CLI-CA06](corpus-and-operations.md#completion-audit-follow-up).
[Native authoring adapter](../../../python/corpus-structure/src/corpus_structure/cli/schema.py#L238) ·
[Native series owner](../../../python/corpus-structure/src/corpus_structure/semantic/native_candidate.py#L1514) ·
[Wrapper and target checks](../../../python/corpus-structure/src/corpus_structure/schema/model_deployment.py#L228) ·
[Isolated rehearsal](../../../python/corpus-structure/tests/semantic/test_model_deployment.py#L28)
