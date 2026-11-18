# Discovery and evidence

## Select the scope

Start with the library family, the repository objective, and the architectural owner and
representative consumers that make it relevant. Record the date, inspected Git revision,
relevant worktree changes and selected project, interpreter, platform and dependency groups.
Scope source reads to the question. Distinguish application and operator paths from tests and
experiments. Inspect the root uv workspace and independently locked provider projects separately.

## Read evidence at the level it supports

| Question | Evidence and limits |
| --- | --- |
| What does the release offer? | Use broad overviews for orientation and release-matched primary docs or source for significant capability claims. Look for configuration, native components, extension points and companion packages. Distinguish capabilities available in the selected release from ones requiring configuration, another platform or an upgrade. |
| What did the project select? | Read the owning manifest for requested versions, extras and groups, and the locked tree for the dependency paths in the selected context. A resolved edge establishes dependency selection in that context. |
| What is installed? | Read the prepared interpreter's distribution metadata for versions, advertised extras and entry points. Keep distribution names distinct from Python import names. A namespace can have several providers and an editable install can lack a mapping. Preserve unresolved correspondences. |
| What does source show? | Start with `rg` and read the actual configuration, wrappers and consumers. Structural matches locate written syntax. Read the surrounding code before describing what is wired, conditional or delegated. Aliases, rebinding, dynamic imports, re-exports and plugin loading can leave attribution unresolved. |
| What ran? | Use existing records to establish execution in their recorded scope. A selected extra, an import or a configured path alone gives no runtime observation. |

Record a scoped no-hit separately from unavailable metadata, excluded paths, parse failures,
truncated output and unresolved joins. A briefing can proceed with representative source reads and
release-matched references alone. State which questions still need the missing evidence.

## Gather the mechanical facts with `tooling library`

The `tooling` command ([ADR-0132](../../adr/0132-tooling-package.md)) supplies the facts that do
not need judgment. It reads; it never imports the inspected package, runs the target
interpreter, or writes into the repository. Each command returns one result that carries its own
baseline (revision, dirty paths, project, interpreter, platform, lock digest) and coverage.
`--json` gives the complete typed result; without it the output is a table on a terminal and
plain lines when piped, with long coverage lists summarized.

A run for a family, from the repository root:

```sh
uv run tooling library baseline
uv run tooling library selection typer rich
uv run tooling library metadata typer rich
uv run tooling library inventory typer
uv run tooling library census typer --scope python/corpus-structure/src
uv run tooling library compare typer --scope python/corpus-structure/src
uv run tooling library overview docs/libraries/python_introspection/typer.md
```

`--project PATH` and `--python PATH`, given before the command name, select another uv project
or environment, such as an independently locked provider project. `selection` and `metadata`
take distribution names; `inventory`, `census` and `compare` take top-level import names.
`census` and `compare` require `--scope`: there is no default scope.

| Evidence class | Command | What it establishes | What it does not |
| --- | --- | --- | --- |
| Dependency selection | `selection` | Whether the project's lock selects a distribution, directly or transitively, with paths, extras, groups and platform markers, across every platform | That the lock is fresh: it is read as it stands and reported as not verified. Run `uv lock --check` yourself when that matters |
| Installation | `metadata` | Installed version, advertised against selected extras, entry points, project URLs, typing files, import names, and installed companions | Companions that are not installed |
| Offered surface | `inventory` | Public symbols with the path users write and the path that declares them, signatures, and markers for deprecated, extension-point, configuration and extra-gated symbols; `--view package` lists environment variables and entry-point groups the package reads | Compiled modules without stubs and surfaces built at import time, which are reported as skipped |
| Written use | `census` | Imports, calls with keyword names, subclasses, decorators and references, attributed through import aliases, with path and line | Uses through instances, repository subclasses, assignment aliases, star imports, `getattr`, dynamic imports and strings, which are listed as unresolved rows |
| Offered against used | `compare` | Each offered symbol and parameter as `referenced`, `unreferenced in scope` or `unresolved`; unselected extras; unpopulated entry-point groups; deprecated APIs in use; written paths not in the inventory | Whether an unreferenced symbol matters: that is the agent's judgment |
| Overview structure | `overview` | Parts and sections with line ranges, malformed headings, and the overview's stated version beside the installed one | The disposition of each section |

The required distinctions map onto the result's coverage block: `no_hit_scopes` for a scoped
no-hit, `unavailable_metadata`, `excluded`, `skipped_inputs` for parse failures and anything the
tool could not examine, `unresolved` for what it examined and could not attribute, and
`truncated` for bounded lists. `--strict` exits 1 when an input was skipped.

Read `compare` with these limits in mind:

- `unreferenced in scope` is a statement about the stated scope and about direct, attributable
  reference. It is a candidate for an unused lead, not a finding.
- `unresolved` is the honest answer for members of any class the code uses, since a method
  called on an instance cannot be attributed. A family used mainly through instances, string
  names, registries or grammars yields mostly unresolved rows; read its uses in context.
- Tests and experiments are outside a scope unless you name them.

Release capability and documented intent still come from the overviews, Context7 and
release-matched primary sources; `metadata` gives the project URLs for the installed version.
What ran still comes from existing records. Source reads remain the way to establish what is
wired, conditional or delegated: the tool locates use, it does not interpret it.

### Interpretive states

The tool emits only mechanical states. When an account classifies a capability, use one
vocabulary:

| State | Meaning |
| --- | --- |
| Used | The repository relies on the capability; cite a call site |
| Underuse candidate | The library is used for the responsibility, and a capability it offers could serve more of it |
| Unused lead | The capability is not used and a repository responsibility might benefit |
| Conditional | Useful only if a stated condition holds |
| Unresolved | Evidence does not settle whether or how it is used |

Existing accounts adopt this vocabulary at their next refresh.

### When a targeted read is still needed

- **Structural questions the census does not ask.** For a one-off shape, use the installed
  ast-grep CLI on selected paths and record the command, scope and tool version:
  `ast-grep run --lang python --kind import_from_statement --json=stream path/to/selected.py`.
  Read candidates in context. [ast-grep run](https://ast-grep.github.io/reference/cli/run.html)
- **Unresolved rows that matter to a lead.** Read the sites the census lists.
- **Other languages and error recovery.**
  [Tree-sitter](../../libraries/python_introspection/tree-sitter.md) remains the route for
  grammar-field queries across languages. Qualify the exact binding and grammar before relying
  on cancellation, given the
  [recorded callback failure](../../design_review/evidence/2026-11-07_cli-typer-028/README.md).
- **Families the tool serves poorly.** Representative source reads and release-matched
  references remain sufficient. State which questions still lack evidence.

## Write the briefings

Maintain `docs/library_leverage/libraries/<family>/briefing.md` using the existing family account
when there is one. Add a route from the [briefing index](../libraries/README.md#library-led-briefings)
when creating a discovery account. The entry point may contain the complete discovery or summarize
and link to focused briefings under `briefings/`. Choose the organization, document boundaries and
level of detail that sufficiently explain the opportunities, without a fixed segmentation scheme
or document count. When using multiple briefings, the summary connects findings, explains research
priorities across topics and identifies useful compositions. Focused briefings carry supporting
analysis and enough context for selective reading. Across the discovery account, include:

1. **Scope and evidence.** Objective, inspected baseline and selection, evidence used, and limits.
   When facts come from `tooling library`, cite the command line and copy the result's baseline
   revision and coverage limits; do not restate a count without its scope.
2. **Capabilities and current use.** A map of relevant capabilities and representative uses,
   with links to original docs, local call sites, configuration or existing evidence. Include
   useful territory outside the current integration.
3. **Research priorities.** For each direction, name the mechanism, potential value, conditions
   that could defeat it, and a question whose answer would change the next step. Describe any
   reason to retain the current approach.
4. **Handoff.** Link existing types, opportunities or assessments when they exist. A useful lead
   can remain a proposed question until a concrete responsibility warrants further work.

Refresh the summary and affected focused briefings together. Link shared baseline and coverage
context where appropriate; make differing dates or source conditions explicit and retain inherited
evidence dates.

For example, a synthetic family might advertise a batching plugin while an inspected test imports
an alias from a namespace with multiple possible providers. Record the advertised plugin, the
test-only import and the unresolved provider separately. If production configuration was outside
scope, leave production use unknown. A next question could ask whether the plugin preserves the
per-item error reporting a caller relies on.
