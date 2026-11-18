# Foundation and envelope — LDT-00, LDT-01

**Status:** Proposed. Part of the
[library-discovery tooling series](../library-discovery-tooling_2026-11-17.md), which owns the
shared contracts, rule changes and package readiness. This companion owns the project wiring,
the CLI model, target resolution, the installation reader and the implementation of the envelope
and output contract. Source:
[review O01](../../../../docs/functional_reviews/library-discovery-tooling_2026-11-17.md#O01).

## Why this work exists

Every later command needs an installed entry point, a resolved target and one way to return a
result. Settling these once keeps each command module small and makes the coverage block a
property of the tool, not of each author's care.

## LDT-00 — Decisions

Records the coordinator's RC1, RC2, RC3 and RC6 once the operator confirms them.

- **ADR** (`uv run ci adr new tooling-package --title "…"`). It decides: a second, non-product
  workspace member rooted at `tooling/`; a second installed CLI beside `ci`; and that ADR-0072
  remains in force with its revisit trigger met. ADR-0069's decision opens "Use installed `ci`
  as the routine interface", so the new ADR must scope an explicit exception: commands that
  inspect third-party libraries for discovery are repository tooling, not product operations,
  and do not take managed-result custody. The committed commands write nothing; their durable
  outputs are whatever the agent saves beside a briefing or in an evidence folder. LDT-C3, if
  ever triggered, writes a download cache and is named as the one exception. Accepted ADRs are
  immutable, so the `adr` skill settles whether this is a coexisting scoped decision or a
  supersession of ADR-0069. It cites ADR-0001 (real consumer for new machinery), ADR-0010 (the
  `tools/evidence` precedent) and ADR-0069. Rejected alternatives to record: an
  independent uv project (loses every existing lane and duplicates pins); commands under `ci`
  (the operator wants the tooling separate from the production package).
- **AGENTS.md**: path-table rows for `tools/` and `tooling/`, and one sentence that tooling plans
  live in `tooling/docs/plans/`.
- **Publication (RC6)**: add `"tooling/docs/**/*.md"` to the "Work plans" collection in
  `docs/site.toml` and `tooling/**` to the path filter in `.github/workflows/docs.yml`. The
  publisher rejects a glob that matches nothing, so this follows the series' first commit.

Completion: the ADR is accepted and indexed (`just turn-end`), `uv run ci adr lint` and
`uv run ci docs check` pass.

## LDT-01 — Project, CLI root, envelope and `baseline`

### Wiring

The member follows `tools/evidence/pyproject.toml`: `uv_build==0.13.6` backend, `src/` layout,
a `[project.scripts]` entry, exact pins. It declares `requires-python = ">=3.14,<3.15"` as the
product does (`tools/evidence` declares `>=3.14`).

| File | Edit |
|---|---|
| `tooling/pyproject.toml` | New. This package declares typer, rich and pydantic at the versions already locked. Later packages add the dependency they first use (griffe and its extensions in LDT-03, libcst in LDT-04 if kept, markdown-it-py in LDT-06). uv, pyrefly and ty are executables the tool runs, not library dependencies. |
| Root `pyproject.toml` | `[tool.uv.workspace].members` gains `"tooling"`; `[tool.uv.sources]` gains the workspace source; root `dependencies` gains the distribution, which is what puts the console script in `.venv`; ruff `src` gains `"tooling/src"`; pyrefly `project-includes` gains `"tooling"` and `search-path` gains `"tooling/src"`; pytest `testpaths` gains `"tooling/tests"`. |
| `scripts/test_receipts.py` | The managed pytest selector (`_forwardable_selector`) admits `tooling/tests`. Without this `uv run ci test -- tooling/tests/…` is refused. |
| `uv.lock` | `UV_LOCKED=0 uv lock`. The diff should add the member and its edge and no new third-party version. |

Tests live in `tooling/tests/`, a deliberate difference from `tools/evidence`, whose tests sit in
the root `tests/evidence/`. Root ruff excludes any directory named `docs`, so `tooling/docs/` is
not linted; `tooling/src` and `tooling/tests` are.

`scripts/check_pins.py` reads workspace members automatically and will require the exact pins,
including the build backend.

### Package shape

A sketch, not a requirement:

```
tooling/src/corpus_tooling/
  cli.py            root Typer app; registers groups
  output.py         JsonOpt, emit, consoles, plain-line rendering, safe text, broken pipe
  envelope.py       Envelope, Baseline, Coverage and the item base
  library/
    app.py          the `library` group and its callback
    target.py       target resolution
    installed.py    installation reader
    baseline.py     …one module per command, added by later packages
```

### CLI model

- A root `Typer(add_completion=False, pretty_exceptions_show_locals=False)`. Groups are attached
  with `add_typer(group, name="library")`; names are always explicit, because an unnamed merge
  drops the child's callback and a name collision overwrites silently
  ([typer.md](../../../../docs/libraries/python_introspection/typer.md) §2.2; advanced
  addendum §1).
- The `library` callback takes `--project` and `--python`, resolves the target once and stores a
  frozen state object on `ctx.obj`; commands read it through the context (typer.md §4.2). Group
  options therefore precede the command name: `tooling library --project P census …`.
- Options repeated across commands (`--json`, `--limit`, `--strict`, `--scope`) are `Annotated`
  aliases defined once (typer.md advanced addendum §2.3). Typer has no way to inject an option
  into every command of a group.
- Closed choices are `Literal` or `Enum` so help lists them (typer.md §3.2).
- Griffe and LibCST are imported inside the command functions that use them. Typer 0.28
  has no lazy command groups, and `--help` should not pay for them (typer.md §10.4).
- No prompts, no completion, no `Live` displays.

### Output and exit contract

The contract itself is in the
[coordinator](../library-discovery-tooling_2026-11-17.md#shared-contracts). Its implementation:

- `emit(result, json=…, render=…)`: under `--json`, `model_dump_json()` to stdout and nothing
  else. Rich's own JSON renderer is not used for the machine channel; it emits `NaN` by default.
- Each item kind declares its columns once; both renderings below are derived from them, so a
  new command writes no rendering code of its own.
- When stdout is a terminal, a Rich projection: `Table(box=None)` with
  `overflow="fold"` on path columns, since the default `ellipsis` truncates long paths
  (*probe*, `cli_typer_rich.py`); `Tree` for nested surfaces
  ([rich.md](../../../../docs/libraries/python_introspection/rich.md) §4.1).
- When stdout is not a terminal, dense plain lines, one item per line with the key fields, and a
  final line stating truncation and the command that returns the rest. This is the pipe-first
  view [agent-cli-capabilities O01](../../../../docs/functional_reviews/agent-cli-capabilities_2026-11-16.md#O01)
  argues for; agents otherwise add `--json` and post-process.
- Consoles are created per call (`Console(stderr=True)` for diagnostics), so test stream swaps
  and `COLUMNS` reach them (rich.md §2.1). Progress uses
  `Progress(console=stderr, disable=not stderr.is_terminal)`; without `disable` a non-terminal
  still receives a final bar line (rich.md §6.6, §7.12).
- Text that came from outside (paths, docstrings, messages) is rendered as literal text with
  terminal control sequences removed. This copies the two control patterns from the product's
  `_diagnostic_capture.py`, not its credential redaction.
- A broken pipe ends the command quietly, as `ci` does.
- Usage errors are Typer's own exit 2. Tool and environment failures raise one exception type
  that the root turns into exit 3 and the same envelope with `status: failed` and `error`.

### Envelope models

- `Envelope` is generic over its item type; each command declares its item model with a `kind`
  literal. The JSON Schema of each command's envelope can be produced from the models
  (`model_json_schema`); publishing it is not in scope.
- `Coverage` fields are always present, empty when not applicable, so a consumer never has to
  distinguish "absent" from "none".
- Unresolved rows carry a `kind` from one closed set defined here. LDT-03 and LDT-04 add their
  kinds to it; this is a shared edit surface.
- `--limit` and `--offset` are applied in one place to the selected view, which also fills
  `truncated`.
- `tool` records the tool version and the version of every authority the command used.
- Items are sorted by the key their kind declares (path and byte offset for locations,
  `declared_path` for symbols), giving stable output across runs.

### Target resolution

- `--project` defaults to the nearest ancestor holding `uv.lock`. `--python` defaults to that
  project's `.venv`. The site-packages directories and the Python version of the target are read
  without running the tool inside it: the version from `pyvenv.cfg`, the paths from the
  environment's layout. If either cannot be determined the command fails with exit 3 and says
  what to pass.
- The tool's own interpreter is never assumed to be the target, even when they are the same.
- When `--python` names an environment outside the resolved project, the target records the
  mismatch and every result carries the note. An environment with no project or lock (some under
  `services/` have only a `.venv`) is a valid target for installation commands; selection
  commands refuse it with exit 3.

### Installation reader

One component over `importlib.metadata.distributions(path=[site-packages…])`, which reads
another environment's metadata, including one for a different Python version, without running
that interpreter (*observed* against a Python 3.12 environment under `services/`). It provides:

- lookup by normalized distribution name, with close matches for a name that is not installed;
- version, requirements, extras, entry points and project URLs as read;
- the map between import names and distributions. `importlib.metadata.packages_distributions()`
  cannot be pointed at another environment, so the reader derives the same mapping from each
  distribution's `top_level.txt` or file list. Editable workspace packages have neither and are
  mapped from their `direct_url.json`. `uv workspace metadata` also returns such a map but is
  experimental and omits editables (*observed*); it is the alternative if the derivation proves
  unreliable. This is the package's one open design question.

An import name with several owning distributions, and a distribution with several import names,
are both returned as they are.

### `library baseline`

The embedded `baseline` block, defined in the coordinator, holds revision, dirty paths
(`git status --porcelain`, as a list, which no existing helper returns), project, target Python
and platform, and the SHA-256 of the project's `uv.lock`. The `baseline` command returns that
block and, as items, what a briefing cites once: the workspace members, the dependency groups,
and the other uv projects found in the repository with their Python requirement.

### Tests

`typer.testing.CliRunner`, asserting stdout and stderr separately (typer.md advanced
addendum §7). It runs single-threaded and does not install Typer's exception hook, so exception
rendering is not tested through it.

Revealing cases:

- `--json` stdout parses as exactly one envelope while a diagnostic is written to stderr.
- A result with unresolved rows exits 0; the same result with a skipped input exits 0, and 1
  under `--strict`.
- Piped output contains no box-drawing characters and ends with the truncation line when
  `--limit` cuts the list.
- A fixture target (a directory with a `uv.lock`, and a fake environment with a `pyvenv.cfg`
  naming Python 3.12 and hand-written `.dist-info` folders) reports that Python and that lock
  digest, not the tool's own.
- A fixture environment paired with a different project carries the mismatch note; a fixture
  environment with no project is refused by a selection-class command and accepted by
  `baseline`.
- The installation reader, over the fake environment: a normalized-name hit, a miss with close
  matches, an import name with two owners, and an editable distribution.
- Demonstration, not a test: `tooling library --project services/nemotron-parse baseline`
  against the real project.

### Completion

`tooling --help` and `tooling library baseline --json` work from an installed environment;
`uv run ci test -- tooling/tests` routes and passes; `uv run ci check --only deps` accepts the
manifest; the lock diff shows no third-party version change.
