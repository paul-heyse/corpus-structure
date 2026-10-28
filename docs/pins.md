# Pins

Every declared dependency is pinned exactly in its manifest, and the lockfiles hold the rest
(AGENTS.md, Dependencies). This page lists the holds, meaning pins that should not be bumped
casually, each with its reason and when to revisit it. It also lists toolchains. A pinned
dependency without a row can be bumped when the work calls for it. Add, change or remove a row
with the `pin-check` skill.

## Toolchains

| Component | Pin | Reason | Revisit when | Verified |
|---|---|---|---|---|
| Python | 3.14.8 (`.python-version`, uv) | Toolchain | a release the project needs | not yet (template): `uv run --no-project python --version` |
| just | 1.58.0 or later | Toolchain | a release the project needs | not yet (template): `just --version` |
| Rust toolchain | 1.98.1 (`rust-toolchain.toml`, `rust-version`) | Toolchain | a release the project needs | not yet (template): `rustc --version` inside the repo |

## Dependencies

| Component | Pin | Reason | Revisit when | Verified |
|---|---|---|---|---|

Every registry dependency is pinned exactly (`=x.y.z`) or by git `rev`; `just deps` checks it.
A row here is only for a hold. Declare crate families that must resolve to one version in
`[workspace.metadata.pins] families` in `Cargo.toml`; their members are pinned exactly like every
other dependency.

Documentation binaries are listed in [site.toml](site.toml); the versions there are pinned and
`just bootstrap-docs` installs exactly those. Change them with focused `just docs-test` and
`just docs-check`.
