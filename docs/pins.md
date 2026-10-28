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

Every registry dependency is pinned exactly (`=x.y.z`) or by git `rev`; `just deps` checks it.
A row here is only for a hold. Declare crate families that must resolve to one version in
`[workspace.metadata.pins] families` in `Cargo.toml`; their members are pinned exactly like every
other dependency.

Documentation binaries are listed in [site.toml](site.toml) (latest releases as checked on
2026-10-28: mdbook 0.5.4, pagefind 1.5.2, lychee 0.24.2); the versions there are pinned and
`just bootstrap-docs` installs exactly those. Change them with focused `just docs-test` and
`just docs-check`.
