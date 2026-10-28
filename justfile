# The only command surface agents need. `just` lists recipes.
# Check recipes do not edit source, except `ruff`'s auto-fixes; tests may create their own data.
# `fmt` and `adr new|supersede|index` edit the working tree. Three bundles, each
# keeping going after a failure: `turn-end` at the end of a turn that changed files, `ready` after an
# environment change, and `hygiene` once at scope end.

set shell := ["bash", "-euo", "pipefail", "-c"]

# List recipes
default:
    @just --list

# The functional tests agents run once all functional scope is implemented
check: test py-test

# Everything functional (end-of-scope acceptance, not the design loop)
test-all: check

turn_end_steps := "adr-index fmt"
ready_steps := "doctor-check"
hygiene_checks := "lint-agents adr-lint rules-scan rules-test ruff types docs-check deps clippy"

# End of a turn that changed files: regenerate the ADR index and format
turn-end: (_bundle "turn-end" turn_end_steps)

# After a dependency, toolchain or process-skill change, or an environment-shaped failure
ready: (_bundle "ready" ready_steps)

# Scope end, after `test-all`: every non-functional check; fix what fails (`just <id>` re-runs one)
hygiene: (_bundle "hygiene" hygiene_checks)

# Run each recipe, keep going after a failure, and list the failures
[private]
_bundle name steps:
    #!/usr/bin/env bash
    set -uo pipefail
    failed=()
    for step in {{ steps }}; do
      echo "== just $step"
      just "$step" || failed+=("$step")
    done
    if [ ${#failed[@]} -gt 0 ]; then
      echo "{{ name }}: ${#failed[@]} failed: ${failed[*]} (re-run one with just <id>)"
      exit 1
    fi
    echo "{{ name }}: all passed"

# Format everything (mutating)
fmt:
    cargo fmt --all
    uv run ruff format
    # Apply ruff's auto-fixes; what remains is the `ruff` check's to report.
    uv run ruff check --fix --quiet --exit-zero

# clippy, denying warnings
clippy:
    cargo clippy --release --workspace --all-targets --quiet -- -D warnings

# Rust tests share the release profile with shipped binaries, so repeated runs execute cached
# optimized test binaries. Snapshots never auto-accept (INSTA_UPDATE=no).
test *args:
    INSTA_UPDATE=no cargo nextest run --release --workspace --no-tests=pass {{args}}

# Every registry dependency pinned exactly (`=x.y.z`) and every git one by its rev; one version
# per declared family; cargo-deny bans and sources (licences are never a rejection reason)
deps:
    uv run --no-project python scripts/check_pins.py
    cargo deny --log-level error check bans sources

# ruff lint, applying its safe auto-fixes first
ruff:
    uv run ruff check --fix --quiet

# pyrefly type check
types:
    uv run pyrefly check --summary=none

# Python tests (scripts and packages)
py-test:
    uv run pytest

# ast-grep scan over the tree (rules/ grows from design-review findings)
rules-scan:
    @if ls rules/*.yml >/dev/null 2>&1; then ast-grep scan; else echo "rules-scan: not_run (no rules yet)"; fi

# ast-grep rule fixtures
rules-test:
    @if ls rules/*.yml >/dev/null 2>&1; then ast-grep test --skip-snapshot-tests; else echo "rules-test: not_run (no rules yet)"; fi

# Evidence records (ADR-0010): no args = index + catalog + check; or check | finalize <folder> <id>… |
# index | catalog | render <template.j2> [-o out] | schema. `index`, `finalize`, `render` edit files.
[positional-arguments]
evidence *args:
    @uv run python -m corpus_evidence "$@"

# ADR tooling: new <slug> [--title T] | supersede <ADR-NNNN> <slug> | index | lint | revisit
[positional-arguments]
adr *args:
    @uv run --no-project python scripts/adr.py "$@"

# Regenerate the ADR index (part of `turn-end`)
adr-index:
    @uv run --no-project python scripts/adr.py index

# ADR metadata and index
adr-lint:
    uv run --no-project python scripts/adr.py lint

# Codex discovery and dead-reference check for agent instructions and skills
lint-agents:
    uv run --no-project python scripts/check_agents.py

# Fail when `doctor` reports a missing or failing tool (part of `ready`)
doctor-check:
    #!/usr/bin/env bash
    set -uo pipefail
    out=$(just doctor 2>&1); status=$?
    printf '%s\n' "$out"
    [ "$status" -eq 0 ] && ! grep -qE 'MISSING|FAILED|below the declared floor' <<<"$out"

# The project-local PostgreSQL 18 cluster (D3 §3): initialize once under build/pg/, start it on its
# own socket (port 5440), and create cs_template with vector and pg_textsearch
db-up:
    @bash scripts/local_pg.sh up

# Stop the project-local cluster
db-down:
    @bash scripts/local_pg.sh down

# The project-local cluster's state, URL and cs_template extensions
db-status:
    @bash scripts/local_pg.sh status

# Tool presence and the versions in use
doctor:
    #!/usr/bin/env bash
    for t in just uv git git-lfs gh rg cargo rustc cargo-nextest cargo-insta cargo-deny clang mold sccache ast-grep; do
      printf '%-14s ' "$t"; command -v "$t" >/dev/null && "$t" --version 2>/dev/null | head -1 || echo MISSING
    done
    printf '%-14s ' python; uv run --no-project python --version
    printf '%-14s ' ruff; uv run ruff --version
    printf '%-14s ' pyrefly; uv run pyrefly --version
    uv run --no-project python scripts/docs.py doctor

# Install declared documentation binaries and isolated test dependencies (network allowed)
bootstrap-docs:
    uv run --no-project python scripts/docs.py bootstrap

# Build Markdown, Pagefind and offline link/fragment checks without product dependencies
docs:
    uv run --no-project --offline --no-python-downloads python scripts/docs.py build

# Existing metadata checks plus a complete publication
docs-check:
    uv run --no-project --offline --no-python-downloads python scripts/docs.py check

# Focused documentation/ADR regressions only
docs-test:
    uv run --no-project --offline --no-python-downloads python scripts/docs.py test

# Build then serve the finished artifact; no watcher or reindex during serving
docs-serve port="8000":
    uv run --no-project --offline --no-python-downloads python scripts/docs.py serve --port {{port}}
