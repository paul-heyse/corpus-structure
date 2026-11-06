# Pins

Every declared dependency is pinned exactly in its manifest, and the lockfiles hold the rest
(AGENTS.md, Dependencies). This page lists the holds, meaning pins that should not be bumped
casually, each with its reason and when to revisit it. It also lists toolchains. A pinned
dependency without a row can be bumped when the work calls for it. Add, change or remove a row
with the `pin-check` skill.

## Toolchains

| Component | Pin | Reason | Revisit when | Verified |
|---|---|---|---|---|
| Python | 3.14.10 (`.python-version`, uv; copier answer `python_version`) | Toolchain | a release the project needs | 2026-10-28: `uv run --no-project python --version` → 3.14.10 |
| just | 1.58.0 or later | Toolchain | a release the project needs | 2026-10-28: `just --version` → 1.58.0 |
| Rust toolchain | **Unpinned** by operator direction (2026-10-28): no `rust-toolchain.toml`, no `rust-version`; cargo uses the rustup default (nightly). The copier answer `rust_toolchain: 1.98.1` remains because it cannot express "unpinned"; a `copier update` may re-propose `rust-toolchain.toml`, which should then be declined | Operator direction | the operator asks for a pin again, or a nightly regression blocks work | 2026-10-28: `rustc --version` → 1.101.0-nightly (41089d07a 2026-10-27) |

## Dependencies

| Component | Pin | Reason | Revisit when | Verified |
|---|---|---|---|---|
| pytest / pytest-xdist (root test environment) | pytest 9.1.1 / pytest-xdist 3.8.0 | xdist 3.8 loadgroup writes legacy `_nodeid`; pytest 9.2 reads structured `_id`, so workers start but marked groups silently split. Keep the compatible pair; do not add a private NodeId adapter | xdist supports pytest 9.2 structured node identity; verify actual same-group ownership, canonical receipt aliases, 16 worker execution and retained timeout controls before moving the pair | 2026-11-06: new 40-case probe passed with 16 worker PIDs, one worker for the shared group and complete context for two real isolated native clones; [evidence](design_review/evidence/2026-11-06_parallel-test-execution/README.md) |
| sympy (product `python/corpus-structure/pyproject.toml`, `methods/math`; spike env `docs/design_review/evidence/2026-10-28_design-spikes/pyproject.toml`; the math grammar's base) | 1.14.0 | ADR-0012: the math grammar extends SymPy's shipped Lark LaTeX grammar and subclasses its transformer; SymPy marks that parser experimental, so a release can change rule names the extension overrides | a SymPy release whose `parsing/latex/lark/grammar/latex.lark` or `transformer.py` changes; bump only with the extension reviewed against the new grammar and the math-grammar coverage record rerun | 2026-10-28: spike env `sympy.__version__` → 1.14.0, lark 1.3.1; product pins sympy 1.14.0 and lark 1.3.1 (P0-I-2a) |
| duckdb (product `python/corpus-structure/pyproject.toml`, the pool's in-process engine `pool/duckdb_engine.py`; also `tools/evidence`) | 2.0.0 | ADR-0021: the engine must stay set-equal with the Python reference implementation of the pool's set steps. 2.0 is a new major release whose Python result lifecycle changed (Arrow only from relations; a second `execute()` silently ends an open result, record `p0q.pool-roundtrip`), and the engine relies on its JSON text forms (compact, key order kept), binary string order, `NULLS FIRST` and ordered `list`/`string_agg` | a 2.0.x patch the project needs, or a 2.1 release; bump only with `tests/pool` (the set-equality harness, its Hypothesis properties) rerun under the new version | 2026-10-28: `uv run python -c "import duckdb; print(duckdb.__version__)"` → 2.0.0 |
| PostgreSQL server extensions on `18/corpus` (`ops/postgresql/extensions.txt`; packages `postgresql-18-pg-textsearch`, `postgresql-18-pgvector`) | pg_textsearch 1.5.1, vector 0.8.7, pg_stat_statements 1.12 (`extversion`) | DA-018: keys and BM25 plans are read against these versions, and D3's BM25 answer relies on version-specific behaviour (the silent fallback when the index predicate is omitted). `just db-provision` brings `corpus` and `cs_template` to the recorded versions and fails on a difference; the test fixtures fail on one, and the test template's name includes the installed versions. The apt packages are not held (`apt-mark showhold` lists none), so an `apt` upgrade changes the server library under the recorded extension SQL | an `apt` upgrade of either package, or a release the store needs; change the record, run `just db-provision`, then the database tests and the BM25/S6 queries against the new version | 2026-10-28: `just db-status` → corpus and cs_template at pg_stat_statements 1.12, pg_textsearch 1.5.1, vector 0.8.7 (as expected); dpkg: postgresql-18-pg-textsearch 1.5.1-1.pgdg24.04+1, postgresql-18-pgvector 0.8.7-1.pgdg24.04+1 |

Every registry dependency is pinned exactly (`=x.y.z`) or by git `rev`; `just deps` checks it.
A row here is only for a hold. Declare crate families that must resolve to one version in
`[workspace.metadata.pins] families` in `Cargo.toml`; their members are pinned exactly like every
other dependency.

Documentation binaries are listed in [site.toml](site.toml) (latest releases as checked on
2026-10-28: mdbook 0.5.4, pagefind 1.5.2, lychee 0.24.2); the versions there are pinned and
`just bootstrap-docs` installs exactly those. Change them with focused `just docs-test` and
`just docs-check`.
