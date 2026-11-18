# Tooling for library-led discovery — functional-extension review

**Date:** 2026-11-17 · **Status:** all recommendations `Proposed`; nothing here is accepted scope.

## Recommendation in brief

Build a small Typer and Rich command-line tool under `tooling/` that gives an agent running
[leverage-library-discovery](../../.claude/skills/leverage-library-discovery/SKILL.md) four things
it gathers by hand today or cannot get at all:

1. the baseline, dependency selection and installed metadata block every briefing repeats
   ([O02](#O02));
2. a mechanical inventory of what an installed library offers, from Griffe ([O03](#O03));
3. an attributed census of how the repository uses it, from `ast` and LibCST ([O04](#O04));
4. the join of the two, with deprecated use from ty ([O05](#O05)).

All of it rests on one typed result that states its own coverage limits ([O01](#O01)). A section
map for overviews ([O06](#O06)) is a small addition. Four further ideas wait for a concrete need
([O07](#O07)–[O10](#O10)). The tool should be a uv workspace member, like `tools/evidence`; an
independent project is the alternative if the operator wants it fully outside the workspace.

## Scope

The operator asked what tooling would support execution of the discovery skill. Supplied
direction:

- the Python introspection overviews (`ast`, ast-grep-py, Astroid, Griffe, LibCST, ty,
  Tree-sitter) describe the range of ways to introspect and characterize a Python library;
- the tooling is driven by a Typer CLI with Rich presentation, separate from the production
  codebase, in a new folder under `tooling/`;
- Context7 is a useful source alongside the overviews.

In scope: what a Python library family offers, what this repository selects and installs, what it
uses, and how those compare. Out of scope: Rust crates (the workspace declares no dependencies),
system tools such as PostgreSQL, the three later leverage stages except where a discovery output
feeds them, and navigation of the repository's own code, which
[agent-cli-capabilities O07](agent-cli-capabilities_2026-11-16.md#O07) already proposes.

## Baseline and evidence

Source baseline: `main` at `d71291f67` plus concurrent uncommitted DDO work, inspected 2026-11-17.
Python 3.14.10; griffe 2.4.1, astroid 4.3.4, libcst 1.9.0, ty 0.0.102, ast-grep-py 0.51.2,
typer 0.28.0 and rich 15.0.0 are declared pins; tree-sitter 0.26.0, tree-sitter-python 0.25.0 and
markdown-it-py 4.2.0 are installed transitively.

Sources:

1. **The overviews**, read in full including their addenda (the later parts of each file):
   [griffe](../libraries/python_introspection/griffe.md),
   [Astroid](../libraries/python_introspection/Astroid.md),
   [ty](../libraries/python_introspection/ty.md),
   [ast](../libraries/python_introspection/ast.md),
   [LibCST](../libraries/python_introspection/libcst.md),
   [ast-grep-py](../libraries/python_introspection/ast-grep-py.md),
   [Tree-sitter](../libraries/python_introspection/tree-sitter.md),
   [Typer](../libraries/python_introspection/typer.md) and
   [Rich](../libraries/python_introspection/rich.md).
   [ast-grep](../libraries/python_introspection/ast-grep.md) (the command-line tool) was
   consulted for O09 only.
2. **Context7** lookups for the shortlisted mechanisms, and **installed source** for the
   contracts that matter.
3. **Read-only probes** against the installed packages and `python/corpus-structure/src`
   (710 files), kept in the
   [evidence folder](../design_review/evidence/2026-11-17_library-discovery-tooling/README.md).
   Results marked *probe* were observed on 2026-11-17. Timings are single wall-clock runs on a
   shared machine and are indicative only.
4. **A replay of the four discovery accounts** (`postgresql`, `cli-and-logging`,
   `domain-data-model`, `text-characterization` under
   [`docs/library_leverage/libraries/`](../library_leverage/libraries/README.md)) as workflow
   scenarios.
5. **An independent design-reviewer challenge** of the draft. It changed the project-boundary
   recommendation, the deprecation authority, the exit-code contract, O06, O07 and O08, and added
   the configuration and companion facts in O02 and O03. Where it disagreed with the draft and
   the disagreement is a real choice, both positions are stated.

Limits: no tool was built, so every resulting behavior is `Proposed`. ty behaviors are for one
pre-1.0 release. Very large packages such as torch were not measured. Where an overview, Context7
and the installed release disagreed, the installed release was taken as the fact.

"The guide" below is the
[discovery and evidence guide](../library_leverage/references/discovery-and-evidence.md). DP
numbers refer to the
[design principles](../design_review/design_principles/core/design-principles.md).

## Current capability

The skill says "use prepared tools and existing records". There are no prepared tools. The guide
supplies inline recipes instead: an inverted `uv tree`, an `importlib.metadata` script, an `ast`
import scan and an `ast-grep` command.

What the four accounts did, and how it went:

- **The same mechanical block was rebuilt in all four**: Git revision and dirty-tree note,
  selected versus installed versions, inverted dependency tree, metadata read, the list of
  independently locked projects, and an overview section map with line ranges.
- **No account enumerated a library's public API.** The offered side came from the overview and
  selective reads of installed files. There is no table with one row per capability and columns
  for selected, installed and called.
- **Every account records the same unmet wish**: a scoped no-hit that cannot become a statement
  about use, "representative reads" where a census was wanted, and alias or dynamic use left
  unattributed.
- **The accounts went stale unnoticed.** Each was written once on 2026-11-09 or 11-10 and has had
  only link maintenance since. Verified 2026-11-17:
  - `cli-and-logging` says structlog is neither installed nor imported; it is now pinned at
    26.1.0 and imported by five product files.
  - `text-characterization` lists the Lark forest and spaCy matchers as candidates; the product
    adopted them on 2026-11-11.
- **The three coverage vocabularies differ** (Used / Underuse candidate / Unused lead /
  Conditional / Unresolved in `postgresql`; other terms in the other accounts).

Existing strengths to keep: uv remains the selection authority; evidence classes stay separate;
interpretation, counterconditions and research priorities stay with the agent. The product's own
analyzers are left alone. `schema/model_discovery.py` in particular is hashed into a readiness
identity, so the tooling should re-express its idea, not import or edit it.

### ADR-0072's revisit trigger

[ADR-0072](../adr/0072-library-led-discovery.md) rejected "build a package and source census
first" because there was no demonstrated consumer. Its decision says "consider dedicated
automation when repeated work establishes the need", and its revisit trigger is "repeated
briefings require the same evidence extraction or routinely need stronger attribution than
representative source inspection can supply". Both halves are now observed: identical extraction
in four accounts, and an attribution caveat in every one. The guide's narrower triggers (a
metadata helper "if multiple briefings repeat the same extraction"; LibCST "if lexical
attribution of aliased or shadowed names becomes a recurring problem") are met as well. The
existing decision therefore already permits this tooling. A new ADR is needed only for what is
newly chosen: the tool's project boundary and the `tooling/` location.

## What the libraries can establish

One authority per fact class (DP-01), with a second tool only where it adds something.

| Fact | Authority | Second tool, and what it adds |
|---|---|---|
| Dependency selection, direct or transitive | `uv tree --locked --offline --invert` | — |
| Installed version, extras, requirements, entry points, distribution-to-import mapping, companions | `importlib.metadata` over an explicit `path=` | Workspace path mapping for editable packages, which `packages_distributions()` does not map |
| Public symbol inventory, re-export origin, signatures, overloads, docstring sections, bases, deprecations offered | Griffe static load | Astroid `wildcard_import_names()` as an optional cross-check |
| Compiled modules without stubs | Filesystem scan, reported as unknown | Griffe inspection inside the target interpreter, opt-in only |
| Entry-point groups and environment variables a library reads | `ast` scan of the library's own source | — |
| Import statements and their context in the repository | `ast` | — |
| Alias attribution of calls, keywords, bases and decorators | LibCST `QualifiedNameProvider`, per file | — |
| Repository use of deprecated library APIs | `ty check`, `deprecated` rule | — |
| Use through instances and other type-resolved use | ty language server (deferred, [O08](#O08)) | — |
| Structural shapes defined as data | ast-grep rules (deferred, [O09](#O09)) | — |
| API change between two versions | Griffe over two search paths plus a tool-side addition diff (deferred, [O10](#O10)) | — |
| Documented intent and release capability | Overviews and Context7 | — |

Findings that shape the design:

- **Griffe loads an installed package without importing it, quickly.** typer loaded in 0.06 s and
  pydantic (153 exports) in 0.23 s (*probe*). It also reads another environment's site-packages
  through `search_paths` (griffe.md §2.4, §4.1–4.4; addendum §1–2).
- **Core Griffe undercounts some public APIs.** typer re-exports with `from .x import Y as Y` and
  no `__all__`; Griffe marks `Typer`, `Option`, `Argument`, `Context` and `run` as not public and
  reports 13 public top-level names (*probe*). Astroid reports 28, including those names. An
  offered count needs the redundant-alias rule, from the `griffe-public-redundant-aliases`
  extension (griffe.md §8.6; not installed) or written into the tool.
- **A compiled module without a stub is silently absent** under static loading, and allowing
  inspection imports the package (*probe*). The tool must list such modules as unknown.
- **Griffe does not populate deprecation.** pydantic has 33 functions decorated `@deprecated`;
  `.deprecated` was set on none (*probe*). The decorator has to be matched, or
  `griffe-warnings-deprecated` added.
- **Parameter documentation can live in annotations.** typer 0.28 documents parameters with
  `Annotated[..., Doc(...)]`; reading those needs `griffe-typingdoc` (verified by the reviewer:
  about 150 `Doc(` uses in typer's source).
- **`ty check` reports deprecated use that a census cannot attribute.** It flagged `m.dict()` and
  `M.parse_obj({})` on a Pydantic model, an instance and a class-method use, and checked all of
  `python/corpus-structure/src` in about 0.7 s (reviewer's check, 2026-11-17; ty.md addendum
  §6.4). Machine-readable formats are `gitlab`, `sarif` and `junit`.
- **ty has no exported model**, so it cannot be an inventory: `workspace/symbol` returns nothing
  for library names (*probe*).
- **LibCST attribution is per-file and does not need `FullRepoManager`.** The earlier report of
  99 s for repository-wide resolution (agent-cli-capabilities O07) is scope-analysis cost at about
  0.2 s per file: 124 s for all 710 files, 47 s for the 239 that mention pydantic, with identical
  results (*probe*).
- **LibCST resolves import aliases but not assignment aliases or instance methods.**
  `import typer as t; t.Typer` resolves; `alias = t.Option; alias()` and `@app.command` come back
  as local names (*probe*; libcst.md §5.1–5.6). Those rows are unresolved joins, not misses.
- **`ast` is the cheap exact pass.** 710 files parsed in 1.4 s with no failures, finding 10,343
  import statements of which 4,550 are below module level, plus 351 `getattr` and 25
  `import_module` calls (*probe*). Function-local imports are the norm here, so a module-level
  scan would be badly incomplete.
- **ast-grep-py agrees with the attributed pass on counts and runs in about a second**, but it
  cannot tell pydantic's `Field` from another `Field`, and an unsupported language name raises a
  Rust panic that `except Exception` does not catch (*probe*).
- **Tree-sitter adds nothing for a Python census** beyond what ast-grep (built on it) and
  `ast.parse` give. Its Python grammar rejects PEP 696 type-parameter defaults (*probe*).
- **Sources disagreed in four places**, which is why installed source is the tool's authority
  while Context7 and the overviews supply intent: a Context7 snippet reverses the meaning of
  `griffe check -a/-b` relative to the installed help; Context7's LibCST material describes 1.8.6;
  an ast-grep README lists a `template` strictness the installed release lacks; the `ast` overview
  targets 3.15 features absent on 3.14.

## Opportunities

Names of commands, the project and fields are illustrative.

<a id="O01"></a>
### O01 — A discovery CLI with one evidence envelope

**Who and what.** An agent running discovery, and the operator reading the result, get one
command family in place of four inline recipes. Every result carries its own baseline and
coverage limits in a form a briefing can cite.

**Proposed behavior.**

```
libscout [--project PATH] [--python PATH]
  env baseline
  deps tree DIST...
  deps metadata DIST...
  api inventory PACKAGE
  usage census FAMILY --scope PATH...
  compare FAMILY
  overview map FILE
```

Every command returns one typed result:

```
{ schema, tool_version, command, generated_at,
  baseline { revision, dirty_paths, project, python, platform, lock_digest },
  items [...],
  coverage { scanned, no_hit_scopes, excluded, skipped_inputs, unresolved,
             unavailable_metadata, truncated { shown, total, next } },
  notes [...] }
```

- `--json` puts exactly that model on stdout. Otherwise the tool renders Rich tables on a
  terminal and dense plain lines when piped, as
  [agent-cli-capabilities O01](agent-cli-capabilities_2026-11-16.md#O01) recommends for `ci`.
  Diagnostics and progress go to stderr.
- The coverage block gives each distinction the guide requires its own field, so a missing result
  is never inferred from silence. It separates **skipped inputs** (parse failures, unreadable
  metadata: the tool could not look) from **unresolved rows** (dynamic references the method
  cannot attribute by nature).
- Items are sorted by a stable key so two runs can be compared.
- Exit codes: 0 when a result is delivered, including a recorded zero-hit and unresolved rows;
  2 for a usage error; 3 or more for a tool or environment failure. `--strict` exits 1 when
  inputs were skipped. Unresolved rows occur in nearly every census, so they must not look like
  failure.
- The target is always explicit (`--project`, `--python`), so the root workspace and the
  independently locked projects under `services/` are inspected the same way.

**Mechanisms.**

- Typer: named sub-apps with `add_typer(sub, name=…)`; a root callback placing a frozen state
  object on `ctx.obj`; shared options as `Annotated` aliases; `Literal`/`Enum` choices; heavy
  imports inside command functions; `add_completion=False`; `pretty_exceptions_show_locals=False`
  (typer.md §2.2, §3.2, §4.2, §10.4; advanced addendum §1, §2.3).
- Rich: `Console(stderr=True)` created per call; `Table(box=None)` with `overflow="fold"`,
  because the default `ellipsis` cut a long path (*probe*); `Tree`, and `Syntax(line_range=…)`
  for excerpts; `Progress(..., disable=not console.is_terminal)` (rich.md §2.1, §4.1, §6.6, §7.12).
- Pydantic models for the envelope, with `model_dump_json()` as the machine channel. Rich's JSON
  rendering is display only.
- Tests with `typer.testing.CliRunner`, asserting stdout and stderr separately (typer.md advanced
  addendum §7).

**Conventions to mirror from `ci`** by copying about forty lines of `cli/output.py`, not
importing the product: the `--json` contract, per-call consoles, literal-text sanitizing and
broken-pipe handling. **Not to mirror:** the command registry and partial-tree dispatch (a
startup optimization for a far larger command set) and ADR-0069 result custody. Durable discovery
outputs belong beside the briefing or in an evidence folder.

**Project boundary.** Two realizations are sound.

| | uv workspace member under `tooling/` | Independent uv project under `tooling/` |
|---|---|---|
| Pins | One set, in the root lock, checked by `check_pins` | Griffe, LibCST, ty, Typer, Rich and Pydantic pinned a second time in a second lock, free to drift |
| Lint, types, tests | Ruff today; pyrefly and pytest after adding `tooling` to three settings | None of the existing lanes: AGENTS.md puts a separate project in ruff's `extend-exclude`, and pyrefly, pytest and `check_pins` do not read it |
| Adding a Griffe extension | Resolved with the product | No effect on product resolution |
| Precedent | `tools/evidence`, a non-product member with its own script | `services/nemotron-parse`, separate because it needs Python 3.12 |
| Use from another repository | No | Yes |

Recommendation: **workspace member**. The product never imports it, so it is still separate from
the production package, and the root project already describes itself as holding repository
scripts and development tools. It is qualified by the lanes that exist, and every library it
needs is already locked. The draft of this review recommended the independent project for a
cleaner separation and reuse elsewhere; the challenge pass showed that the cost here is the loss
of all existing qualification and a second set of pins, for a reuse that has no consumer yet.
The condition that reverses the recommendation: the operator wants the tool usable outside this
repository, or its extensions prove to conflict with product resolution.

Nothing documents how `tools/` and `tooling/` differ; a row in the AGENTS.md path table would
settle it.

**Demonstrated by:** each command returning the envelope under `--json`, and a zero-hit census
exiting 0 with the scope listed in `no_hit_scopes`.

<a id="O02"></a>
### O02 — Baseline, selection and installation snapshot

**Who and what.** The block every account rebuilt by hand becomes commands whose output drops
into the briefing's baseline table.

**Proposed behavior.**

- `env baseline`: revision, dirty paths, project, interpreter, platform, dependency groups and
  the independently locked projects found.
- `deps tree`: direct versus transitive selection, with the paths.
- `deps metadata`: installed version; `Provides-Extra` against the extras actually selected;
  requirements with markers; entry points the distribution declares; `Project-URL` values, which
  give the documentation address for a version-matched Context7 or primary-source lookup;
  `py.typed` and stub presence; the distribution-to-import mapping with unmapped and mismatched
  names listed (one account wrote `term-validator` for the distribution `linkml-term-validator`).
- **Companions**: installed distributions that require this one, and installed distributions that
  populate its entry-point groups. This serves the skill's "companion packages" for what is
  already installed; uninstalled companions remain a documentation question.

**Mechanisms.** `uv tree --project P --locked --offline --no-python-downloads --invert --package
X` as a subprocess, uv staying the authority. `importlib.metadata.distributions(path=[…])` reads
a target environment without running its interpreter: 203 distributions were read from a Python
3.12 environment (*probe*). `packages_distributions()` plus a workspace path mapping for editable
packages, which it does not map (*probe*).

**Defeating condition.** None material; this is the lowest-risk and most-repeated part.

**Demonstrated by:** regenerating the `cli-and-logging` baseline and seeing structlog 26.1.0
reported as selected and installed.

<a id="O03"></a>
### O03 — Offered-surface inventory of an installed package

**Who and what.** The agent gets, for the first time, a mechanical list of what a library
exposes, so the offered side no longer rests on an overview and a few file reads. This is what
lets discovery "look beyond familiar entry points to configuration, extension points and
companion packages".

**Proposed behavior.** `api inventory pydantic` lists public modules, classes, functions and
attributes with exposed path and declaring path, kind, signature and overloads, first docstring
line, bases and decorators. It marks:

- **deprecated**, from the `@deprecated` decorator;
- **extension point**: Protocol or abstract base classes, abstract methods, and classes the
  library's own entry-point groups name;
- **configuration surface**: `TypedDict` configuration keys (pydantic's `ConfigDict`), settings
  classes, and the environment-variable names and entry-point group names the library's source
  reads;
- **optional-extra gated**: imports inside `try`/`except ImportError`.

The coverage block lists unresolved aliases, compiled modules without stubs and modules that
failed to parse. Views bound the output: `--depth`, `--kind`, `--match`, `--limit`.

**Mechanisms.**

- `GriffeLoader(allow_inspection=False, search_paths=[site-packages])`, `load`, and
  `resolve_aliases(external=False)`, which returns the unresolved set. Then `is_public`,
  `is_exported`, `exports`, `Alias.target_path` / `final_target`, `Object.aliases`; `Parameters`,
  `overloads`, `Expr` trees; `Docstring.parse`; `as_json` (griffe.md §3–6, §9; addendum §1–2,
  §5–7).
- Official Griffe extensions (griffe.md §8.6) are the first candidates for the gaps found:
  `griffe-public-redundant-aliases` for publicity, `griffe-warnings-deprecated` for deprecation,
  `griffe-typingdoc` for `Annotated` parameter documentation, `griffe-pydantic` for model fields.
  Whether each handles the installed packages was not checked; writing the two simple rules in
  the tool is the fallback.
- An `ast` scan of the library's source for `entry_points(group=…)` arguments and
  `os.environ` / `getenv` names.
- A filesystem scan for `.so`/`.pyd` without a `.pyi`, reported as unknown. Inspection stays an
  explicit opt-in that runs in the target interpreter and records that it imported the package.
- Optional `--cross-check` with Astroid `Module.wildcard_import_names()` in a separate process,
  because its manager shares state, reporting names on which the two disagree (Astroid.md
  addendum §2).

**Alternatives.** Astroid as the primary engine: rejected, because inference is partial, it
could not infer Pydantic fields (an earlier finding, confirmed in a probe) and it follows the
running interpreter's path. ty as inventory: not possible. The inactive library-skills extractor
`typer-rich/build/extract.py` shows a workable Griffe fact shape and five traps worth carrying
(definitions in private modules, publicity as two facts, assignment aliases, namespace packages,
source-local annotation spellings); it is a pattern, not a dependency.

**Defeating conditions.** A family whose surface is mostly compiled without stubs, or generated
at import time, yields a thin static inventory; the coverage block must say so. Packages that
export lazily through `__getattr__` are covered only where they also carry `TYPE_CHECKING`
imports, as pydantic does.

**Demonstrated by:** the typer inventory including `Typer`, `Option` and `Argument`; the pydantic
inventory reporting 153 exports and marking its 33 deprecated functions.

<a id="O04"></a>
### O04 — Attributed usage census

**Who and what.** "Scoped no-hit" and "representative read" become a census with stated scope
and honest limits: which symbols of the family the repository imports, calls, subclasses,
decorates with and configures, and where.

**Proposed behavior.** `usage census pydantic --scope python/corpus-structure/src` reports per
symbol: import sites with their context (module level, function-local, `try`, `TYPE_CHECKING`),
call sites with keyword names, subclass and decorator sites, each with path, line and UTF-8 byte
offset. Unresolved rows are kept by kind: assignment alias, instance method, `getattr`,
`import_module`, string reference. Mentions in `pyproject.toml` and YAML are a separate, labelled
item class.

**Mechanisms, in layers.**

1. Declared scope: roots, excluded globs, generated paths, and which uv project each root belongs
   to.
2. Exact pass over all files with `ast` (`Import`, `ImportFrom`, `Call`, `ClassDef`), building
   the set of files that touch the family directly or through a repository module that
   re-exports it (ast.md §4.3, §5.1–5.2; addendum §1.3, §7.1). About two seconds here.
3. Attributed pass on hit files only with LibCST `MetadataWrapper` and `QualifiedNameProvider`
   on `Call.func`, `Arg.keyword`, `ClassDef.bases` and `Decorator`, with `PositionProvider`
   (libcst.md §5.1–5.6; addendum §3.4, §5). This is the expensive step: cached by file digest and
   LibCST version, and run in worker processes.
4. Validity is judged by the target interpreter's grammar: `ast.parse(feature_version=…)` when
   the target is older than the tool's interpreter, or a subprocess in the target interpreter.
   LibCST is not the validity authority; it accepted `lazy import` although Python 3.14 rejects
   it (*probe*).

**Alternatives.**

- **`ast` with `symtable` for attribution.** An import map from `ast` plus compiler scopes from
  `symtable` could resolve import aliases and shadowing at parse speed, removing the cache, the
  worker pool and the minute-long first run. It was not probed, and `symtable` gives no
  per-occurrence positions (ast.md §10.1; addendum §5), so the join back to call sites is the
  open part. This is the one probe worth running before the census is planned.
- **A syntactic-only census with ast-grep-py** matched the attributed counts for pydantic but
  cannot attribute a bare name; see [O09](#O09).
- `FullRepoManager` is unnecessary.
- `schema/model_discovery.py` already combines ast-grep-py candidates with LibCST attribution and
  coverage states for declared-model consumers. The census re-expresses that design for
  third-party families.

**Defeating conditions.** A family used mainly through instances (`console.print`,
`app.command`), string names or dynamic loading is under-attributed. With LibCST, the first
uncached run on a broad family takes on the order of a minute.

**Demonstrated by:** the pydantic census reproducing the probe (`Field` 883 calls, `min_length`
314 keyword uses, `BaseModel` 303 bases) with unresolved rows listed, and the structlog census
finding the five importing files.

<a id="O05"></a>
### O05 — Offered-versus-used comparison

**Who and what.** The table no account has: one row per offered capability with selected,
installed and used columns, so the agent starts interpretation from complete candidates.

**Proposed behavior.** `compare typer` joins [O03](#O03) and [O04](#O04) and reports:

- public symbols never referenced;
- parameters and configuration keys of used callables that are never passed;
- extension points with no repository subclass or registration;
- extras advertised but not selected, and entry-point groups the library reads that nothing
  installed populates;
- **deprecated APIs the repository still uses.**

Each row carries a mechanical state only (`referenced`, `unreferenced in scope`, `unresolved`),
leaving Used / Underuse candidate / Unused lead / Conditional to the agent.

**Mechanisms.** A join on canonical path, using Griffe's exposed-to-declared map so that a use of
`typer.Option` matches `typer.params.Option`. Deprecated use comes from
`ty check --python <env> --output-format gitlab`, filtered to the `deprecated` rule; ty is the
single authority for that row because it sees instance and class-method uses the census cannot.

**Value and limit.** This is the core of what the skill asks: "comparing what it offers with what
this repository selects and uses". It produces candidates, not conclusions: an unreferenced
symbol is a lead only when a repository responsibility would benefit, and that judgment stays
with the agent. It serves families used mainly through their Python API (pydantic, typer, rich,
structlog). It serves much less a family driven by registries, string names, grammars or a
server: spaCy and Lark in `text-characterization` are used largely through factory names and
patterns, which the census can only list as unresolved.

**Defeating conditions.** For very large surfaces the unreferenced list is long; it needs
grouping by module and the O03 markers to be readable. ty is pre-1.0, so the rule name and output
format must be pinned with the version.

**Depends on** O03 and O04.

<a id="O06"></a>
### O06 — Overview section map and version check

**Who and what.** The coverage tables' mechanical columns (heading, line range) are generated,
malformed overview headings are flagged instead of being copied into an account, and an overview
that describes a different version from the one installed is reported.

**Proposed behavior.** `overview map docs/libraries/python_introspection/griffe.md` lists parts,
sections, line ranges, headings that look malformed, and the overview's stated target version
beside the installed version. The disposition column stays manual.

**Mechanisms.** The repository already has a fence-aware heading reader, `headings()` in
`scripts/design_sections.py`; reuse or expose it. Fence awareness matters: a plain `grep '^#'`
over these overviews returns code comments as headings (nine extra lines in `griffe.md`,
reviewer's check). The `postgresql` account inherited rows titled "5" and "0" from malformed
source headings, and two accounts noted overviews describing later versions than those installed.

**Defeating condition.** Small value on its own; worth doing because it is a few lines beside
O01 and every account needed it.

<a id="O07"></a>
### O07 — One summary snapshot beside the briefing

**Who and what.** A briefing's mechanical facts can be regenerated and compared with what was
recorded, so the structlog and text-characterization staleness would show at the next refresh.

**Proposed behavior.** A discovery run writes one summary envelope beside the account (versions,
selection, per-symbol file counts; no line numbers), overwritten on each refresh. `git diff`
shows what changed.

**Why not more.** The draft proposed dated snapshots and a `drift` command. The operator has
directed that nothing be built that looks back over past runs while the codebase moves this fast,
and dated snapshots accumulate exactly that. One overwritten file keeps no history and adds no
command. Staleness is still caught only when someone refreshes.

**Recommendation.** Optional; adopt only if the operator agrees it stays on the right side of
that direction.

<a id="O08"></a>
### O08 — Type-resolved references into a library

**Who and what.** Closes the census gap for use through instances (`console.print`,
`app.command`).

**Mechanisms.** A `ty server` session pointed at the real environment, issuing
`textDocument/references` and `typeHierarchy/subtypes` (ty.md §7.1). In the probe, references
from repository code into `typer.Option` were found, including in an unopened file, but a call
through an `as` alias was missed.

**Recommendation.** Do not build this in the discovery tool. It is the same capability as
`ci code refs` in [agent-cli-capabilities O07](agent-cli-capabilities_2026-11-16.md#O07) pointed
at a library symbol, and a second language-server client would duplicate it. If O07 there is
built, let it accept an installed-library symbol. Revisit when O04 shows how large the
instance-method gap is for a real family.

<a id="O09"></a>
### O09 — Family rule packs

**Who and what.** A family account can keep, as data, the structural shapes worth counting
("every `typer.Option(...)` and its keywords") and rerun them in about a second.

**Mechanisms.** The simplest route is the installed `ast-grep` command: `ast-grep scan --rule`
with `--json=stream` loads YAML rules with no Python (ast-grep.md §6.2, §7). The Python binding
(`SgRoot(...).root().find_all(config)`) is the alternative when results must join the envelope
in-process; relational rules need an explicit `stopBy`, and language names must be whitelisted
because an unknown one panics (*probe*; ast-grep-py.md §3–6, addendum 1 §4). The command is a
host binary and is not pinned.

**Defeating condition.** Without attribution a rule pack overcounts same-named symbols, so its
output must be labelled syntactic. It duplicates what O04 gives for most questions.

**Recommendation.** Wait for a family that asks the same structural question repeatedly.

<a id="O10"></a>
### O10 — Version-to-version API comparison

**Who and what.** Answers "what would the newer release give us".

**Mechanisms.** Two Griffe loaders over two search paths; `find_breaking_changes` for removals
and incompatible changes; a tool-side set difference for additions, which that function never
reports (griffe.md §7; addendum §8). The second version would be fetched with
`uv pip install --no-deps --target <cache>`. Griffe's own `load_pypi` shells out to pip and
needs `wheel`, which is absent here, and `load_git` creates a worktree.

**Defeating conditions.** It needs network access and a cache policy. Release notes often answer
the question with less machinery.

**Recommendation.** Wait for a concrete upgrade question.

## Set aside

- **Tree-sitter** as an engine: redundant here, with a grammar gap for PEP 696.
- **Astroid inference, transforms and brains**: partial results and shared manager state; kept
  only as the optional export cross-check in O03.
- **`rich.inspect` as evidence**: it imports the target and its output is presentation.
- **Griffe `load_pypi`, `load_git` and forced inspection**: pip and network, a worktree, and
  import side effects respectively.
- **Prompts, shell completion, `Live` dashboards, `rich.traceback.install()`**: no consumer in an
  agent-driven tool.

## How the opportunities fit together

- **O01 and O02** are the foundation and are worth having on their own; they remove the block
  every account repeats.
- **O03 and O04** are independent of each other and each useful alone. Together they enable
  **O05**, which is the point of the skill.
- **O06** is small and independent.
- **O07** is optional and needs the operator's view.
- **O08** belongs with agent-cli-capabilities O07. **O09 and O10** wait for the need named in
  each.

Recommended first set: O01 to O06.

## Rule and document impacts

These need decisions through the existing routes; none is made here.

- An ADR for the tool's project boundary and the `tooling/` location. ADR-0072 already permits
  the automation.
- The guide's recipes and its "when a richer tool would help" section would point to the
  commands, and the skill's "use prepared tools" would name them.
- A common mechanical state vocabulary for coverage tables, in place of three divergent ones.
- A `tooling/` row in the AGENTS.md path table; for a workspace member, `tooling` added to the
  pyrefly and pytest settings.
- New scope goes through the DDO series under a distinct prefix (for example `LDT-O01`).

## Open questions

1. Workspace member or independent project (O01)?
2. Which official Griffe extensions to add, against writing the two simple rules in the tool
   (O03)?
3. May the tool ever import target code, behind an explicit flag (O03)?
4. Does `ast` with `symtable` attribute well enough to replace the LibCST pass (O04)? One probe
   answers it.
5. Is the single summary snapshot acceptable under the no-lookback direction (O07)?
