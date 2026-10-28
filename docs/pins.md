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
| sympy (spike env `docs/design_review/evidence/2026-10-28_design-spikes/pyproject.toml`; the math grammar's base) | 1.14.0 | ADR-0012: the math grammar extends SymPy's shipped Lark LaTeX grammar and subclasses its transformer; SymPy marks that parser experimental, so a release can change rule names the extension overrides | a SymPy release whose `parsing/latex/lark/grammar/latex.lark` or `transformer.py` changes; bump only with the extension reviewed against the new grammar and the math-grammar coverage record rerun | 2026-10-28: spike env `sympy.__version__` → 1.14.0, lark 1.3.1 |
| pylatexenc (spike env only; production M01 does not use it, D4 M01) | 3.0b2 (pre-release) | Its configurable `ParsingState` (math only from `\(…\)` and `\[…\]`, `$` as prose, comments off) is 3.x only; 2.11's default context opens comments and false math at Siegrist's 17 prose `%`/`$` (S1 V6). The math itself is read by the grammar (ADR-0012), so only these two uses depend on it | Release when the spike work ends: the text-math library note (2026-10-28) found no production use (the macro reader runs on the TeX tokenizer, and delimiting alone sets segment status) | 2026-10-28: spike env imports `pylatexenc.latexwalker` 3.0b2 (record e0.environment) |
| PostgreSQL server extensions on `18/corpus` (`ops/postgresql/extensions.txt`; packages `postgresql-18-pg-textsearch`, `postgresql-18-pgvector`) | pg_textsearch 1.5.1, vector 0.8.7, pg_stat_statements 1.12 (`extversion`) | DA-018: keys and BM25 plans are read against these versions, and D3's BM25 answer relies on version-specific behaviour (the silent fallback when the index predicate is omitted). `just db-provision` brings `corpus` and `cs_template` to the recorded versions and fails on a difference; the test fixtures fail on one, and the test template's name includes the installed versions. The apt packages are not held (`apt-mark showhold` lists none), so an `apt` upgrade changes the server library under the recorded extension SQL | an `apt` upgrade of either package, or a release the store needs; change the record, run `just db-provision`, then the database tests and the BM25/S6 queries against the new version | 2026-10-28: `just db-status` → corpus and cs_template at pg_stat_statements 1.12, pg_textsearch 1.5.1, vector 0.8.7 (as expected); dpkg: postgresql-18-pg-textsearch 1.5.1-1.pgdg24.04+1, postgresql-18-pgvector 0.8.7-1.pgdg24.04+1 |

Every registry dependency is pinned exactly (`=x.y.z`) or by git `rev`; `just deps` checks it.
A row here is only for a hold. Declare crate families that must resolve to one version in
`[workspace.metadata.pins] families` in `Cargo.toml`; their members are pinned exactly like every
other dependency.

Documentation binaries are listed in [site.toml](site.toml) (latest releases as checked on
2026-10-28: mdbook 0.5.4, pagefind 1.5.2, lychee 0.24.2); the versions there are pinned and
`just bootstrap-docs` installs exactly those. Change them with focused `just docs-test` and
`just docs-check`.
