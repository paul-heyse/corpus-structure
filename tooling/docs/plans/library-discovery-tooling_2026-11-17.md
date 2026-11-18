# Library-discovery tooling — plan series coordinator

**Status:** LDT-00–08 implemented and qualified for this scope on 2026-11-17; LDT-C1–C3 remain
conditional and unstarted. Owns the disposition of
[the tooling review](../../../docs/functional_reviews/library-discovery-tooling_2026-11-17.md)
O01–O10. **Revised:** 2026-11-17.

This coordinator owns the combined target, shared contracts, rule changes, package readiness and
opportunity disposition. The four companions own their designs and package descriptions:

| Companion | Packages | Opportunities |
|---|---|---|
| [Foundation and envelope](library-discovery-tooling/foundation-and-envelope.md) | LDT-00, LDT-01 | O01 |
| [Environment and offered surface](library-discovery-tooling/environment-and-offered-surface.md) | LDT-02, LDT-03 | O02, O03 |
| [Usage and comparison](library-discovery-tooling/usage-and-comparison.md) | LDT-04, LDT-05 | O04, O05 |
| [Adoption and conditional extensions](library-discovery-tooling/adoption-and-conditional-extensions.md) | LDT-06, LDT-07, LDT-08, LDT-C1–C3 | O06–O10 |

## Purpose and scope

The [leverage-library-discovery](../../../.claude/skills/leverage-library-discovery/SKILL.md)
skill compares what a library family offers with what this repository selects, installs and
uses. Today an agent gathers that by hand from inline recipes, and has never had a mechanical
list of what a library offers or an attributed account of how it is used. The series delivers a
command-line tool that produces those facts, each result stating its own baseline and coverage
limits, so the agent's effort goes into interpretation.

Complete means: the six committed opportunities (O01–O06) work as commands, the discovery guide
and skill point to them, and one existing account has been refreshed with them. O07, O09 and O10
are designed here and run only when their trigger occurs. O08 is not built in this series.

Out of scope: Rust crates, system tools such as PostgreSQL, navigation of the repository's own
code, any change to the product package, and the three later leverage stages.

This series stands apart from the declared-data-operations series by operator direction
(2026-11-17): tooling scope is planned here, product scope there.

## Basis

- Source: the tooling review at `9711e2402`, all of it `Proposed`. It was revised once by an
  independent challenge pass before publication; there is no separate recommendation audit.
- Retained probes: the
  [2026-11-17 evidence folder](../../../docs/design_review/evidence/2026-11-17_library-discovery-tooling/README.md),
  cited below as *probe* with the script name.
- Baseline: `main` at `9711e2402` plus unrelated uncommitted work, inspected 2026-11-17.
  Python 3.14.10, uv 0.13.7, griffe 2.4.1, libcst 1.9.0, ast-grep-py 0.51.2, pyrefly 1.4.0,
  ty 0.0.102, typer 0.28.0, rich 15.0.0, pydantic 2.14.1, markdown-it-py 4.2.0.
- Two preparation inquiries (repository wiring; uv, Griffe-extension, type-checker and `symtable`
  contracts) and an independent challenge of this series, all read-only on 2026-11-17. Their
  observations are marked *observed*; they were made with one-off commands and are not finalized
  evidence records.
- Standard: the [design principles](../../../docs/design_review/design_principles/core/design-principles.md)
  and heuristics, applied qualitatively. DP numbers below refer to them. No broad audit is
  started.

## Decisions and rule changes

Confirmed by the operator on 2026-11-17:

| Item | Decision | Route |
|---|---|---|
| Project boundary | uv workspace member | ADR in LDT-00 |
| Layout | `tooling/` is the project root; later tooling joins the same package and CLI | ADR in LDT-00 |
| Plan home | This series lives in `tooling/docs/plans/`, separate from DDO | This document; `docs/plans/README.md` row; saved note updated |
| Deferred opportunities | O07, O09, O10 as conditional packages; O08 routed, not built | Disposition table below |
| O07 | One overwritten summary file per account; no history, no drift command | LDT-C1 |

Rule and document changes proposed by this series. The operator accepted all six on
2026-11-17; each is carried out by the package named in the last column.

| Ref | Change | Consequence had it been rejected | Carried out in |
|---|---|---|---|
| RC1 | A new ADR records the tooling package and its CLI. ADR-0069 makes installed `ci` the routine interface; the new ADR scopes an explicit exception for repository tooling that inspects libraries and is not a product operation, and states that ADR-0069's managed-result custody does not apply to it. Whether this is a coexisting scoped decision or a supersession is settled with the `adr` skill. ADR-0072 stays in force; its revisit trigger is recorded as met. | The `tooling/` convention and the second CLI are undocumented and conflict with ADR-0069's wording | LDT-00, as [ADR-0132](../../../docs/adr/0132-tooling-package.md), a scoped decision beside ADR-0069 |
| RC2 | AGENTS.md gains path-table rows for `tools/` and `tooling/` and says tooling plans live in `tooling/docs/plans/` | Agents keep routing tooling scope to `docs/plans/` | LDT-00 |
| RC3 | Names: distribution `corpus-tooling`, import package `corpus_tooling`, console script `tooling`, discovery commands under `tooling library …` | Any other free name works; `ci`, `corpus-evidence`, `griffe`, `ty`, `pyrefly` and `ruff` are taken | LDT-00 (ADR), LDT-01 |
| RC4 | The discovery guide's inline recipes are replaced by the commands, and the skill's "use prepared tools" names them | The tool exists but the workflow does not point to it | LDT-07 |
| RC5 | The guide defines one interpretive coverage vocabulary (Used, Underuse candidate, Unused lead, Conditional, Unresolved); existing accounts adopt it at their next refresh | Three vocabularies continue | LDT-07 |
| RC6 | `tooling/docs/**/*.md` joins the published "Work plans" collection, and the documentation workflow's path filter gains `tooling/docs/**` | The series is linked from the site as a source file, not published | LDT-00 |

## Design choices made in this series

These are the author's choices within the review's target. They are ordinary design and
dependency judgment and do not wait on approval; the operator can redirect any of them.

| Ref | Choice | Why | Reopen when |
|---|---|---|---|
| D1 | Three official Griffe extensions as exact pins: `griffe-public-redundant-aliases==0.3.2`, `griffe-warnings-deprecated==1.1.2`, `griffe-typingdoc==0.3.2` | *Observed* with them loaded: typer's public top-level names go from 13 to 40, including `Typer` and `Option`; pydantic gains `deprecated` on 35 objects; `typer.Option` parameters gain their `Doc` text | An extension stops tracking Griffe, or mis-marks the LDT-03 fixture |
| D2 | The tool never imports the package it inspects; no inspection flag is built | The review allowed an opt-in flag. Importing a target has side effects and would have to run in the target interpreter. Compiled modules without stubs are reported as skipped inputs instead. | A family whose offered surface is mostly compiled without stubs |
| D3 | pyrefly, not ty, is the authority for deprecated use | Both report it; only pyrefly's message names the declaring path (*observed*), which is the join key | pyrefly's message format changes, or it misses a case ty reports |
| D4 | Selection is read from `uv tree --frozen --universal --format json`, with the lock reported as not verified | The installed uv emits the graph with extras, groups and markers as nodes (*observed*); parsing the text tree would re-derive it. `--locked` and platform-filtered reads execute the project's interpreter, which D2 forbids (*observed* during execution) | The preview schema changes incompatibly, or uv gains a lock check that runs no interpreter |
| D5 | Overview headings are read with markdown-it-py | It is already locked as a Rich dependency and its heading tokens carry line maps, so no code is copied from `scripts/` | — |

## Current baseline and foundations

- **No discovery tool exists.** The
  [guide](../../../docs/library_leverage/references/discovery-and-evidence.md) carries the
  recipes (lines 25–102) and names the triggers for a richer tool (lines 105–118), which the
  review found met.
- **`tooling/` holds only this series.** `tools/evidence` is the existing non-product workspace
  member: `uv_build` backend, `src/` layout, a console script, root dependency
  `{ workspace = true }`. Its tests live in the root `tests/evidence/`.
- **Every library the first set needs is already locked.** Only D1's three extensions are new
  packages. All first-set dependencies are declared in `tooling/pyproject.toml` by LDT-01, in
  one lock change.
- **uv, pyrefly and ty are executables the tool runs, not libraries it imports.** pyrefly and ty
  are pinned in the lock. uv is a host binary with no pinned version in this repository, so the
  tool records the uv version it ran and relies on a contract test.
- **Foundations to re-express, never import from the product:**
  - `corpus_structure/cli/output.py`: the `--json` contract, per-call consoles, broken-pipe
    handling and `report_fields`, about ninety lines. Its `safe_text` helper also redacts product
    credentials; the tool needs only the two terminal-control patterns.
  - `corpus_structure/schema/model_discovery.py`: the pattern of candidate matches plus lexical
    attribution with explicit coverage states. It is hashed into a readiness identity and is
    neither imported nor edited.
  - `corpus_structure/core/provenance.py` `code_commit()`: the revision-plus-dirty idea; a list
    of dirty paths is new.
- **Gaps the wiring must close** (details in the foundation companion): pytest `testpaths`,
  pyrefly `project-includes` and `search-path`, ruff `src`, and the managed test selector in
  `scripts/test_receipts.py`, which rejects `tooling/tests/...` today.

## Combined target

One installed command, `tooling`, with a `library` group:

```
tooling library [--project PATH] [--python PATH]
  baseline                        revision, dirty paths, interpreter, platform, lock digest, projects found
  selection DIST...               direct or transitive, paths, extras and groups selected
  metadata DIST...                installed version, extras, entry points, URLs, typing, import names, companions
  inventory PACKAGE               what the installed package offers
  census ROOT... --scope PATH...  how repository code uses it
  compare ROOT... --scope PATH... offered against used, with deprecated use
  overview FILE                   section map and target-version check
```

`ROOT` is an import root such as `pydantic`; a library family in an account's sense may span
several roots and distributions, and the agent names them. A discovery run is: `baseline`,
`selection` and `metadata` for the family's distributions, `inventory` for each import root,
`census` over the chosen scope, then `compare`. The agent reads the results, writes the briefing
and keeps all interpretation.

### Shared contracts

These are owned here; companions link to them and do not restate them.

**Target.** Every command resolves one target before doing work: a uv project (the directory
holding the nearest `uv.lock` by default) and an environment (that project's `.venv` by
default), with the environment's site-packages and Python version. The root workspace and the
independently locked projects under `services/` are targets of the same kind.

- The tool's own interpreter is never assumed to be the target.
- Selection facts come from the project and installation facts from the environment. If
  `--python` names an environment that is not the project's own, every result says so in
  `notes`, because the two may not correspond. Some environments under `services/` have no
  project or lock at all; for those, selection commands refuse and installation commands work.
- A scope that spans several uv projects is reported per project.

**Installation reader.** One component, delivered in LDT-01 and used by every later package,
reads the target environment's distributions: normalized-name lookup, version, entry points and
the map between import names and distributions. LDT-02 builds the `metadata` command on it;
LDT-03, LDT-05 and LDT-06 consume it directly.

**Envelope.** Every command returns one Pydantic model:

```
schema            "tooling.library/1"
status            "ok" | "failed"
error             present only when failed: kind, message, what to pass or fix
tool              tool version, and the version of each authority the command used
command           the invocation, normalized
generated_at
baseline          revision, dirty_paths, project, python, platform, lock_digest
view              the item kind this result holds
items[]           one declared kind per view; sorted by the kind's stable key
coverage          scanned, no_hit_scopes, excluded, skipped_inputs[], unresolved[],
                  unavailable_metadata[]
truncated[]       one entry per bounded list: list, shown, total
notes[]
```

- `--json` writes exactly this to stdout. Otherwise the result is rendered: Rich tables on a
  terminal, dense plain lines when stdout is not a terminal. Both renderings come from the
  columns each item kind declares once. Diagnostics and progress go to stderr.
- A command may offer more than one view (the census has a per-symbol summary and per-site
  rows). Each view is a declared item kind; `--json` follows the selected view.
- Lists are bounded by `--limit` and continued with `--offset`. A truncated result names the
  list and the totals, and the rendered view prints the command that returns the next page.
- **Skipped inputs** are things the tool could not examine: a file that failed to parse,
  unreadable metadata, a compiled module without a stub. **Unresolved rows** are things it
  examined and cannot attribute by its method: an alias Griffe could not resolve, an assignment
  alias, a member reached through an instance. They are different facts and never share a field
  (DP-02).
- Exit codes: 0 when a result is delivered, including zero hits and unresolved rows; 2 for a
  usage error; 3 for a tool or environment failure, returned as the same envelope with
  `status: failed`. `--strict` exits 1 when `skipped_inputs` is not empty.
- The embedded `baseline` is the six fields above. The `baseline` command's items add what a
  briefing cites once: workspace members, dependency groups, and the other uv projects found.

**Evidence classes and their one authority** (DP-01). Each item names its class and authority.

| Class | Authority | Owner |
|---|---|---|
| Selection | uv (`uv tree --format json`) | LDT-02 |
| Installation | `importlib.metadata` over the target's site-packages | LDT-01 reader, LDT-02 command |
| Offered surface, including which symbols are offered as deprecated | Griffe static load with the D1 extensions | LDT-03 |
| Written use | `ast` for import statements; the attribution engine for calls, keywords, bases and decorators | LDT-04 |
| Deprecated use | pyrefly | LDT-05 |
| Overview structure | markdown-it-py | LDT-06 |

"Is this symbol deprecated" is answered by the inventory for what a library offers. "Does the
repository use something deprecated" is answered by pyrefly, and a pyrefly row stands on its own
even when the inventory did not mark the symbol (the Griffe extension does not cover attributes
or aliases). `compare` reports such a row and notes the disagreement.

Release capability and documented intent stay with the overviews and Context7; runtime evidence
stays with existing records. The tool produces neither.

**Symbol identity.** A library symbol has four parts, kept separate because discovery needs each:

- `distribution`: normalized name and version, from the installation reader;
- `import_root`: the top-level import package;
- `exposed_path`: a path a user can write, such as `typer.Option`; one symbol may have several;
- `declared_path`: where Griffe finds its definition, such as `typer.params.Option`; exactly
  one.

A usage row carries the `written_paths` the attribution engine resolved: a set, because a name
bound in both branches of a `try` or under `TYPE_CHECKING` resolves to more than one.

**The join.** `compare` does not join on a published map. It holds the loaded Griffe collection
in the same process and, for each written path, looks the path up in the collection and takes
the found object's `canonical_path`, falling back to the longest resolvable prefix when the tail
is not found. This is what resolves members and inherited members: *observed* on pydantic 2.14.1,
`pydantic.RootModel.model_validate` resolves to `pydantic.main.BaseModel.model_validate`. A
saved census can be an input to `compare`; a saved inventory cannot, because a bounded,
top-level view does not contain member paths.

A written path that resolves to nothing is reported as `not in inventory`, never dropped. A
symbol the library binds by assignment from another distribution
(`pydantic.ValidationError = pydantic_core.ValidationError`) has its declared path in the
assigning module, and the result notes that the real definition is elsewhere.

**Mechanical states.** `compare` assigns only `referenced`, `unreferenced in scope` or
`unresolved`. A member of an offered class is `unresolved`, not `unreferenced`, whenever that
class has any use in scope (imported, named in an annotation or an `isinstance` check,
subclassed, instantiated or passed as a value) and the member is not referenced directly:
`MyModel.model_validate(x)`, `m.model_dump()` and a method called on an annotated parameter are
uses the attribution engine cannot assign to the library's member. A member reached through a
value whose class cannot be traced makes every offered member of that name `unresolved`. Execution widened this rule
from "subclassed or instantiated" after review found real false `unreferenced` rows
(2026-11-17). The same holds for every name a star import could bind. The interpretive vocabulary (RC5) belongs to the agent and
the account.

### What the target accommodates

- **Another family or another project**: a new invocation, no code.
- **A new marker on offered symbols** (for example "async-capable"): one rule in the inventory;
  the envelope, census and join are untouched.
- **A different attribution engine**: the census consumes one function from source text to
  attributed and unresolved rows. LDT-04 chooses between two engines; a third would replace it
  without touching the census output or `compare`.
- **Another tooling command unrelated to discovery**: a sibling group beside `library` in the
  same package, reusing the output module. A command that mutates state would need its own
  decision, not an extension of this envelope.

## Where the series differs from the review

| Topic | Review | Series | Why |
|---|---|---|---|
| Selection source | Text of `uv tree --invert` | `uv tree --format json` (D4) | See D4 |
| Publicity and deprecation | Extension or hand-written rule, undecided | Official Griffe extensions (D1) | See D1 |
| Importing the target | Explicit opt-in flag | Never (D2) | See D2 |
| Deprecated use | ty | pyrefly (D3) | See D3 |
| Validity for an older target | `feature_version` or a subprocess in the target interpreter | `ast.parse(feature_version=…)` only, stated as best-effort | No command runs the target interpreter (D2); the limit is reported |
| Overview headings | Reuse `scripts/design_sections.py` | markdown-it-py (D5) | `scripts/` is not importable from an installed package |
| Inventory cross-check | Optional Astroid cross-check | Dropped | The hand-written fixture validates publicity; Astroid would be a dependency for this alone |
| Census reuse | Cache by file digest, worker processes | No cache; worker processes only if LibCST is kept | The workload is one run per family per refresh; a saved census feeds `compare` |
| Attribution question | A probe before planning | An opening slice of LDT-04 | Standing direction: resolve inside the consuming package |
| O07 | A file written by a discovery run | A projection of `compare --json` that the agent redirects to the file | The tool then never writes into `docs/` |
| Output code from `ci` | About forty lines | About ninety, minus credential redaction | Read of `cli/output.py` |
| Command names | `libscout env/deps/api/usage …` | `tooling library …` (RC3) | `tooling/` is the home for later tools as well |

## Packages

| Package | Delivers | Needs | Completion boundary |
|---|---|---|---|
| LDT-00 | RC1, RC2, RC3 and RC6 recorded; ADR accepted | Operator confirmation (given 2026-11-17) | ADR and AGENTS.md rows merged |
| LDT-01 | Installed `tooling` command; target and installation reader; envelope, output and exit contract; `baseline` | LDT-00 | `tooling library baseline --json` returns a valid envelope; fixture target tests pass |
| LDT-02 | `selection` and `metadata` | LDT-01 | The cli-and-logging baseline facts are reproduced, structlog reported as selected and installed |
| LDT-03 | `inventory` | LDT-01 | Fixture package inventory equals the hand-written expectation; typer inventory lists `Typer` as public |
| LDT-04 | `census`, opening with the attribution-engine decision | LDT-01 | Fixture repository census equals the hand-written expectation; unresolved rows listed by kind |
| LDT-05 | `compare` with deprecated use | LDT-02, LDT-03, LDT-04 | Join demonstrated where exposed and declared paths differ and through a repository subclass |
| LDT-06 | `overview` | LDT-01 | Section map of an overview with fenced `#` lines is correct; version mismatch reported |
| LDT-07 | Guide and skill point to the commands; one account refreshed | LDT-02–06; RC4, RC5 | The refreshed account's mechanical facts come from the commands |
| LDT-08 | Assembled qualification | All committed packages | `uv run ci test` and `uv run ci check` results accounted for |
| LDT-C1 | O07 summary snapshot | LDT-07; trigger | See companion |
| LDT-C2 | O09 rule packs | LDT-04; trigger | See companion |
| LDT-C3 | O10 version comparison | LDT-03; trigger | See companion |

Dependencies below whole packages:

- LDT-02, LDT-03, LDT-04 and LDT-06 need the target, installation reader and envelope as
  implemented code from LDT-01, and nothing from one another.
- LDT-04's import-statement pass does not wait for its opening decision; only the attributed
  pass does.
- LDT-05 needs working `selection`, `metadata`, the inventory loader and census rows, not just
  agreed shapes.

Shared edit surfaces when packages run in parallel:

- the CLI registration file, where each package adds a command;
- the coverage and unresolved-kind definitions in the envelope module, which LDT-03 and LDT-04
  both extend.

One useful route: LDT-00, LDT-01, then LDT-02, LDT-03, LDT-04 and LDT-06 in any order, then
LDT-05, LDT-07, LDT-08.

## Investigations and where they are settled

| Question | Source | Settled in |
|---|---|---|
| Can `ast` with `symtable` replace the LibCST pass? | Review open question 4 | Opening slice of LDT-04 |
| Which Griffe extensions? | Review open question 2 | D1; LDT-03 verifies them against its fixture |
| May the tool import target code? | Review open question 3 | D2 |
| Workspace member or independent project? | Review open question 1 | Operator: workspace member |
| Is the summary snapshot acceptable? | Review open question 5 | Operator: yes, single overwritten file |
| How are editable workspace packages mapped to import names? | Review O02 | LDT-01 |
| Does the preview JSON of `uv tree` hold the fields used? | Preparation | LDT-02, as a contract test |
| How does a stale lock behave under `--locked`? | Preparation | LDT-02: not used. Checking the lock runs the project interpreter, so the lock is read as it stands and reported as not verified |
| Do lazy `__getattr__` packages without `TYPE_CHECKING` imports appear? | Review O03 | LDT-03, reported as a coverage limit if not |
| Is pyrefly's deprecated message reliable enough to join on? | Preparation | Opening step of LDT-05 |

## Opportunity disposition

| Opportunity | Disposition | Owner |
|---|---|---|
| O01 CLI and envelope | Scheduled | LDT-00, LDT-01 |
| O02 Baseline, selection, installation | Scheduled | LDT-01 (baseline, reader), LDT-02 |
| O03 Offered-surface inventory | Scheduled | LDT-03 |
| O04 Attributed usage census | Scheduled | LDT-04 |
| O05 Offered against used | Scheduled | LDT-05 |
| O06 Overview section map | Scheduled | LDT-06 |
| O07 Summary snapshot | Conditional | LDT-C1 |
| O08 Type-resolved references | Not built here; remains unscheduled at the review, which points to [agent-cli-capabilities O07](../../../docs/functional_reviews/agent-cli-capabilities_2026-11-16.md#O07). This series does not edit that review. | — |
| O09 Rule packs | Conditional | LDT-C2 |
| O10 Version comparison | Conditional | LDT-C3 |

## Verification and acceptance

- **During a package:** focused tests under `tooling/tests/` with `uv run ci test -- PATH`.
- **Expectations are independent of the code under test.** Target, inventory and census tests
  run against small fixture trees written for the purpose (a fake environment, a package, a
  repository), with expected results written by hand. Checks against installed typer, pydantic
  and structlog, and against real projects under `services/`, are demonstrations recorded in the
  package's completion note, not unit tests, because those versions and environments move.
- **Contract tests** cover the fields read from `uv tree --format json` and from pyrefly's JSON,
  so a version change that alters them fails loudly.
- **Assembled (LDT-08):** `uv run ci test` and `uv run ci check` after all committed scope.
- No timing target is an acceptance criterion.

## Current state

**Implemented, 2026-11-17.** The `tooling` command is installed with seven `library` commands:
`baseline`, `selection`, `metadata`, `inventory`, `census`, `compare` and `overview`. The
discovery guide and skill point to them, and the `cli-and-logging` account's mechanical facts
were regenerated with them, which corrected its stale claim that structlog was not installed.

| Package | State | Evidence |
|---|---|---|
| LDT-00 | Done | [ADR-0132](../../../docs/adr/0132-tooling-package.md) accepted; AGENTS.md rows; `tooling/docs/` published |
| LDT-01 | Done | Reviewed once; nine findings repaired |
| LDT-02 | Done | structlog 26.1.0 reported as selected and installed |
| LDT-03 | Done | typer inventory lists `Typer`, `Option`, `Argument` as public with declared paths under `typer.main` and `typer.params`; pydantic reports its seven unresolved aliases without failing `--strict` |
| LDT-04 | Done | LibCST kept after the opening slice; pydantic census over the product source: `Field` 885 calls, `BaseModel` 304 bases |
| LDT-05 | Done | Reviewed once; ten findings repaired, including five confirmed false or wrong states; pyrefly confirmed for deprecated use |
| LDT-06 | Done | typer and ty overviews reported as older than the installed versions |
| LDT-07 | Done | Guide, skill, account index and the `cli-and-logging` refresh |
| LDT-08 | Done for this scope | See below |

**Qualification, 2026-11-17, at `6556a0b45` plus the account edit** (Python 3.14.10, uv 0.13.7,
pyrefly 1.4.0):

- **passed:** `uv run ci test -- tooling/tests tests/scripts/test_test_receipts.py`, result
  `8cd3bc5aa2b24d5a9e5d8d4c4a69270b`, 302 tests (138 under `tooling/tests`). This is the
  functional scope the series changed: the new package and the edited managed-test selector.
- **passed:** `uv run ci check`, result `34811b452107403d90e5035f8a2e0550`: lint-agents,
  adr-lint, ruff-check, types, docs-check, deps and clippy passed; rules-scan and rules-test
  are `not_run` (the repository has no rules yet).
- **passed:** each of the seven commands returns one `tooling.library/1` envelope under `--json`
  with exit 0 against the root project.
- **Lock:** across the series the lock gained `corpus-tooling` and the three D1 extensions and
  nothing else.
- **not_run:** the full product suite (`uv run ci test` with no selector). No product source
  changed, and another agent was changing the product tree throughout.

Formatting and auto-fixes were run on `tooling/` and the one edited script only, not through
`just turn-end`, because another agent was working in the tree.

**What execution changed from the design** (each recorded where it is owned):

- Selection reads `uv tree --frozen --universal` and reports the lock as not verified, because
  every lock-checking route executes the project interpreter (D4).
- The class-member rule in `compare` was widened to any class with a use in scope, after review
  found real false `unreferenced` rows.
- All first-set dependencies were declared in one lock change.
- The inventory leaves out names bound only under a `__main__` guard and lists members
  inherited through private bases.

**Known limits, stated by the tool in its results:**

- `unreferenced in scope` covers direct, attributable reference in the named scope only.
- Members reached through instances, subclasses, star imports, dynamic imports and strings are
  unresolved, so `compare` is most useful for libraries used by direct reference.
- Members of classes reached through repository subclasses or instances are attributed only
  where the class or instance is bound in the same file.
- `TypedDict` keys passed in dictionary literals are not seen.
- The census worker processes start from the tool's own interpreter, which in this repository is
  the same environment as the root target.

**Next:** nothing is owed. LDT-C1 (summary snapshot) becomes due when an account is refreshed
with the commands a second time; LDT-C2 and LDT-C3 wait for their triggers. The other three
discovery accounts adopt the commands and the shared vocabulary at their next refresh.

## Risks

- **Preview and undocumented interfaces.** `uv tree --format json` is a preview schema on an
  unpinned host binary, and pyrefly's message text is not a documented contract. Contract tests
  and the recorded versions make a change visible; they do not prevent it.
- **Thin inventories.** Families that are compiled without stubs, or built at import time, yield
  little statically. The coverage block says so; D2 keeps it that way by choice.
- **Families used through strings, instances or subclasses.** spaCy factory names,
  `console.print` and inherited Pydantic methods are unresolved, not attributed. `compare` is
  most useful for families used through their Python API by direct reference, and its notes say
  when a family is not one.
