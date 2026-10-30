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

Tools: `just`, `uv`, `git` with Git LFS, the Rust toolchain in `rust-toolchain.toml` with cargo-nextest, cargo-deny, sccache, clang and mold, ast-grep. `just doctor` lists what is
present. During implementation, run compile checks and targeted tests; once all functional scope
is implemented, run `just test-all` and `just hygiene` (the non-functional checks). The functional
qualification route retains streamed outcomes, command context and interrupted-run diagnostics
under `build/test-receipts/qualification/`; `just check` and `just py-test` remain developer routes.
`just turn-end` formats and
regenerates at the end of a turn; `just ready` re-checks the environment after a change.

After the scaffold lockfiles exist, run `bash scripts/setup-env` to prepare this checkout's
tools. Installed toolchains follow the pin files; setup
does not install Rust. If using direnv, review `.envrc` and run `direnv allow` once in each
checkout. Direnv loads local/native settings without installing, building or activating Python.
Personal overrides belong in ignored `.envrc.local`.

Use `uv run python …`, `uv run pytest …` and `uv run ruff …` for ordinary Python work.
uv selects the workspace's `.venv` and synchronizes declared dependencies automatically;
bare Python/tool activation is not required. Agent commands default to `UV_LOCKED=1`, so
stale lockfiles fail without changing them. Intentional dependency changes explicitly use
`UV_LOCKED=0 uv add …` (or the corresponding lock command); exact dependency pins still apply.
For cross-project work, select the tool working directory or use uv's explicit `--project`/
`--directory` options. `uv run script.py` discovers from the script, while `uv run python
script.py` selects from the current workspace. Documentation/process recipes retain their
explicit dependency-free `--no-project` mode with a local `UV_LOCKED=0` override.

## Documentation locally

Run `just bootstrap-docs` once to install the declared documentation tools and cache isolated test
dependencies. Then `just docs-check` builds and checks the complete static artifact under
`build/docs/site/`. `just docs-test` runs focused publisher and ADR tests. `just docs-serve` builds
and serves on http://127.0.0.1:8000. Rebuild after edits; the preview is not a watcher.
See [publishing operations](docs/publishing.md) for details.

Generated from [project-template](https://github.com/paul-heyse/project-template); `copier update`
brings template improvements.
