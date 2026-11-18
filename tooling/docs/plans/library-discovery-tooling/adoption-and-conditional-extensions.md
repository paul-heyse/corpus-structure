# Adoption and conditional extensions — LDT-06, LDT-07, LDT-08, LDT-C1–C3

**Status:** Proposed. Part of the
[library-discovery tooling series](../library-discovery-tooling_2026-11-17.md), which owns the
shared contracts and package readiness. This companion owns the overview command, adoption into
the discovery workflow, assembled qualification and the three conditional packages. Sources:
[review O06](../../../../docs/functional_reviews/library-discovery-tooling_2026-11-17.md#O06),
[O07](../../../../docs/functional_reviews/library-discovery-tooling_2026-11-17.md#O07),
[O09](../../../../docs/functional_reviews/library-discovery-tooling_2026-11-17.md#O09) and
[O10](../../../../docs/functional_reviews/library-discovery-tooling_2026-11-17.md#O10).

## LDT-06 — `overview FILE`

### Behavior

For a library overview under `docs/libraries/`, the command lists each part and section with its
heading level and line range, flags headings that look malformed, and reports the version the
overview says it targets beside the version installed in the target. The disposition column of
an account's coverage table stays with the agent.

### Mechanism

- **Headings.** markdown-it-py (4.2.0, already locked as a Rich dependency and declared by this
  package): `MarkdownIt().parse(text)` yields `heading_open` tokens with their level and line
  map, and fenced code is a separate token, so a `#` line inside a fence is never a heading. A
  plain `^#` match over these overviews returns code comments as headings. The repository's own
  fence-aware reader in `scripts/design_sections.py` cannot be imported from an installed
  package, and using the library avoids a copy.
- **Parts.** An overview is a main text followed by addenda, each opened by a level-one heading;
  sections are numbered level-two headings within a part. Line ranges run to the next heading of
  the same or higher level.
- **Malformed headings.** A numbered section whose title is only a digit, or a numbering gap
  within a part, is flagged. One account inherited rows titled "5" and "0" this way.
- **Version.** The overview's stated target (title or opening lines, for example "Rich 15.0.0")
  is extracted with a small pattern and compared with `metadata` for the named distribution.
  When no version is stated the field is absent, not guessed. Two accounts noted overviews
  describing a later version than the one installed.

### Tests and completion

A fixture overview with a fenced `# comment`, an addendum, a malformed heading and a stated
version, with the expected map written by hand; a demonstration on `griffe.md`.

## LDT-07 — Adoption

The tool has no value until the workflow that needs it points to it. This package makes the
consumer changes and proves the commands on a real account.

### Changes (RC4, RC5)

- **[Discovery and evidence guide](../../../../docs/library_leverage/references/discovery-and-evidence.md).**
  The inline recipes (the `uv tree` command, the `importlib.metadata` script, the `ast` import
  script and the `ast-grep` command, lines 25–102) are replaced by the corresponding commands.
  The section "When a richer tool would help" (lines 105–118) is rewritten to describe what the
  tool covers and what still needs a targeted read. The evidence classes and the required
  distinctions stay as they are; the guide gains the mapping from each to an envelope field.
  The superseded recipes are removed, not kept beside the commands.
- **Coverage vocabulary.** The guide defines the interpretive states once: Used, Underuse
  candidate, Unused lead, Conditional, Unresolved. It states that the tool emits only mechanical
  states and that the agent assigns these.
- **[Discovery skill](../../../../.claude/skills/leverage-library-discovery/SKILL.md).** "Use
  prepared tools and existing records" names the commands and the order of a run. The sentence
  that representative reads suffice when evidence is unavailable stays, for families the tool
  serves poorly.
- **[Library account index](../../../../docs/library_leverage/libraries/README.md).** One
  paragraph on citing an envelope: the command line, the baseline revision and the coverage
  limits.

The three accounts that repeat the recipes in prose are not rewritten here. Each adopts the
commands and the vocabulary at its next refresh.

### Consumer demonstration

Refresh the `cli-and-logging` account in place, as the skill prescribes, using only the
commands for its mechanical facts. It is the right case because its recorded facts are known to
be stale: it says structlog is neither installed nor imported.

- Baseline table rows come from `baseline`, `selection` and `metadata`.
- The capability-to-use statements for typer, rich and structlog are checked against `compare`.
- Coverage limits are copied from the envelopes.
- Interpretation, research priorities and counterconditions are rewritten by the agent where the
  facts changed. That is discovery work under the skill, done to the depth the changed facts
  require, not a full new discovery.

What this demonstrates: the commands' output maps onto an account's tables without reshaping,
and a known-stale claim is corrected by the refresh.

### Completion

`uv run ci docs check` passes; the refreshed account records its command lines and baseline; the
guide no longer contains the superseded recipes.

## LDT-08 — Assembled qualification

After all committed packages:

- `uv run ci test` for the applicable functional lanes, accounting for the `tooling/tests`
  selection in the managed result;
- `uv run ci check` for repository checks (ruff, pyrefly, deps, docs, ADR lint);
- the lock diff across the series: the new member and the three D1 extension pins, and nothing
  else;
- a final read of the coordinator's opportunity table against what exists, with each committed
  opportunity's demonstration recorded.

Results are reported as `passed`, `failed`, `blocked` or `not_run` with the command. A package's
focused tests do not stand in for this.

## Conditional packages

Each is designed here and starts only when its trigger occurs. Until then it is not owed.

### LDT-C1 — Summary snapshot (O07)

**Trigger.** An account is refreshed with the commands for the second time, or the operator asks
for it.

**Behavior.** `compare` gains a `--summary` view: the selected and installed versions, the
selected extras, and per declared symbol its mechanical state and the number of referencing
files. No line numbers. The agent redirects `compare --summary --json` to `snapshot.json` at the
account's root, overwriting the previous one; `git diff` then shows which facts moved. The
embedded baseline changes on every refresh, since the revision does; the items change only when
a fact changes.

The tool adds a view, not a command, and never writes into `docs/` itself.

**Boundary.** One file per account, no dated copies, no comparison command, no history. This is
the form the operator accepted under the no-lookback direction; anything that accumulates past
runs is outside it.

**Depends on** LDT-07.

### LDT-C2 — Family rule packs (O09)

**Trigger.** A family account asks the same structural question in two refreshes and the census
does not answer it, for example a call shape defined by argument structure.

**Behavior.** An account keeps a YAML rule file; `tooling library rules FILE --scope PATH...`
runs it and returns matches in the envelope, labelled syntactic, with no attribution claim.

**Mechanism.** ast-grep-py: one `SgRoot(source, "python")` per file and `find_all` per rule
([ast-grep-py.md](../../../../docs/libraries/python_introspection/ast-grep-py.md) §3–6,
addendum 1 §4). Two conditions from the probes: relational rules need an explicit `stopBy`,
because the default returned no matches for a keyword inside a call; and the language is fixed
to Python, because an unsupported language name raises a panic that `except Exception` does not
catch. The installed `ast-grep` command (`scan --rule … --json=stream`) is the alternative with
no Python at all, but it is an unpinned host binary and its output would need adapting to the
envelope.

**Depends on** LDT-04 for scope handling.

### LDT-C3 — Version comparison (O10)

**Trigger.** A concrete question about what a newer release of a selected library would add or
remove.

**Behavior.** `tooling library diff PACKAGE --against VERSION` reports symbols added, removed
and changed between the installed version and another.

**Mechanism.** The other version is fetched into a cache directory with
`uv pip install --no-deps --target <dir> <dist>==<version>`, then loaded with a second Griffe
loader over that path. Removals and incompatible changes come from
`griffe.find_breaking_changes(old, new)`; additions come from a set difference of declared
paths, because that function never reports them
([griffe.md](../../../../docs/libraries/python_introspection/griffe.md) §7; addendum §8).
Griffe's `load_pypi` is not used (it shells out to pip and needs `wheel`, which is absent), nor
`load_git` (it creates a worktree).

**Conditions.** This is the only command that needs the network and the only one that writes
anything (its download cache). It must say so, fail clearly offline, and never touch the target environment or the
lock.

**Depends on** LDT-03.

### O08 — not in this series

Type-resolved references into a library are not planned here. The review points to
[agent-cli-capabilities O07](../../../../docs/functional_reviews/agent-cli-capabilities_2026-11-16.md#O07),
which no plan currently owns, and this series does not edit that review. Two observations from
preparation are kept here for whoever plans it: pyrefly 1.4.0's `--report-glean` writes
per-module JSON mapping byte spans to qualified targets, including member access; and ty's
`textDocument/references` missed a call made through an `as` alias. Revisit from this series
only if LDT-04's unresolved rows for members reached through instances and subclasses prove to
dominate a real family's census.
