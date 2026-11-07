# corpus-structure

Agent workflows and invocation examples are in the [process skills](.claude/skills/README.md),
with [shared roles](.agents/roles/README.md) for Codex.

Builds a highly structured representation of a set of documents

[STATUS](STATUS.md) owns the current checkpoint. Accepted architecture includes labeled targets.

- [Documentation and task routes](docs/README.md)
- [Architecture map](docs/design/README.md)
- [Development instructions](AGENTS.md)
- [Decision records (current rationale)](docs/adr/README.md)

## Development

Prefer the installed CLI for supported development and corpus operations. The
[ci skill](.claude/skills/ci/SKILL.md) explains the command routes, managed results and
how to handle a defect surfaced during work.

Use `uv run ci doctor` to check the prepared tools and `uv run ci context show` to inspect
the effective settings. Run `uv run ci test -- PATH` for targeted pytest selection and
`uv run ci test` for the full applicable functional campaign. Use `uv run ci results show ID`
to find retained outcomes and `uv run ci test retry ID` to retry unresolved test nodes.
Run `uv run ci check` for repository checks and `uv run ci format` for explicit formatting.
Use direct recipes for bootstrap and documented recovery. `just turn-end` formats and
regenerates repository metadata at the end of a turn.

After the scaffold lockfiles exist, run `bash scripts/setup-env` to prepare this checkout's
tools. Installed toolchains follow the pin files; setup
does not install Rust. If using direnv, review `.envrc` and run `direnv allow` once in each
checkout. Direnv loads local/native settings without installing, building or activating Python.
Personal overrides belong in ignored `.envrc.local`.

`uv` selects the workspace's `.venv` and synchronizes declared dependencies automatically.
Agent commands default to `UV_LOCKED=1`, so
stale lockfiles fail without changing them. Intentional dependency changes explicitly use
`UV_LOCKED=0 uv add …` (or the corresponding lock command); exact dependency pins still apply.
For cross-project work, select the tool working directory or use uv's explicit `--project`/
`--directory` options. `uv run script.py` discovers from the script, while `uv run python
script.py` selects from the current workspace. Documentation/process recipes retain their
explicit dependency-free `--no-project` mode with a local `UV_LOCKED=0` override.

## Documentation locally

Run `just bootstrap-docs` once to install the declared documentation tools and cache isolated test
dependencies. Then `uv run ci docs check` builds and checks the complete static artifact under
`build/docs/site/`. `just docs-test` runs focused publisher and ADR tests. `just docs-serve` builds
and serves on http://127.0.0.1:8000. Rebuild after edits; the preview is not a watcher.
See [publishing operations](docs/publishing.md) for details.

Generated from [project-template](https://github.com/paul-heyse/project-template); `copier update`
brings template improvements.
