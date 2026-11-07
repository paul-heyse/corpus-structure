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

# Parallel ordinary functional lane; the exclusive fault lane follows separately when required.
[positional-arguments]
test-all *args:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n ${CORPUS_CI_RECEIPT_DIR:-} ]]; then
      options=(--managed-lane ordinary --out-dir "$CORPUS_CI_RECEIPT_DIR")
      if [[ -n ${CORPUS_CI_SELECTION_FILE:-} ]]; then
        options+=(--selection-file "$CORPUS_CI_SELECTION_FILE")
      fi
      if [[ ${CORPUS_CI_PYTHON_ONLY:-0} == 1 ]]; then
        options+=(--python-only)
      fi
      exec uv run --no-sync python scripts/test_receipts.py run "${options[@]}" -- "$@"
    fi
    exec uv run python scripts/test_receipts.py run --out-dir "build/test-receipts/qualification/$(date -u +%Y%m%dT%H%M%SZ)-$$" -- "$@"

# Exclusive shared-cluster authentication fault controls; run after the parallel lane finishes.
[positional-arguments]
test-native-faults *args:
    #!/usr/bin/env bash
    set -euo pipefail
    export CORPUS_TEST_NATIVE_AUTH_CRASH=1
    if [[ -n ${CORPUS_CI_RECEIPT_DIR:-} ]]; then
      options=(--managed-lane fault --out-dir "$CORPUS_CI_RECEIPT_DIR")
      if [[ -n ${CORPUS_CI_SELECTION_FILE:-} ]]; then
        options+=(--selection-file "$CORPUS_CI_SELECTION_FILE")
      fi
      exec uv run --no-sync python scripts/test_receipts.py run "${options[@]}" -- "$@"
    fi
    exec uv run python scripts/test_receipts.py run --python-only --out-dir "build/test-receipts/qualification/$(date -u +%Y%m%dT%H%M%SZ)-faults-$$" -- -n 0 -m shared_cluster_fault tests/scripts/test_native_auth.py "$@"

turn_end_steps := "adr-index fmt"
ready_steps := "doctor-check"
hygiene_checks := "lint-agents adr-lint rules-scan rules-test ruff types docs-check deps clippy"

# End of a turn that changed files: regenerate the ADR index and format
turn-end: (_bundle "turn-end" turn_end_steps)

# After a dependency, toolchain or process-skill change, or an environment-shaped failure
ready: (_bundle "ready" ready_steps)

# Scope end, after `test-all`: every non-functional check; fix what fails (`just <id>` re-runs one)
hygiene: (_bundle "hygiene" hygiene_checks)

# Read-only repository checks for the installed CLI.
ci-check: (_bundle "ci-check" "lint-agents adr-lint rules-scan rules-test ruff-check types docs-check deps clippy")

# Bootstrap from the installed CLI is an explicit effect.
ci-setup:
    @bash scripts/setup-env

# Ruff inspection without the fixes applied by the maintenance recipe.
ruff-check:
    uv run ruff check --quiet

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
    INSTA_UPDATE=no cargo nextest run --release --workspace --no-tests=warn {{args}}

# Every registry dependency pinned exactly (`=x.y.z`) and every git one by its rev; one version
# per declared family; cargo-deny bans and sources (licences are never a rejection reason)
deps:
    UV_LOCKED=0 uv run --no-project python scripts/check_pins.py
    cargo deny --log-level error check bans sources

# ruff lint, applying its safe auto-fixes first
ruff:
    uv run ruff check --fix --quiet

# pyrefly type check
types:
    uv run pyrefly check --min-severity warn --summary=none

# Python tests (scripts and packages)
py-test:
    uv run pytest

# The model's Stage A files (core/vocab.py, core/_model/): `just model generate` rewrites them and
# the root revision; `just model check` (the default) only checks declarations, log and drift
model action="check":
    uv run python -m corpus_structure.schema {{action}}

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
    @UV_LOCKED=0 uv run --no-project python scripts/adr.py "$@"

# Regenerate the ADR index (part of `turn-end`)
adr-index:
    @UV_LOCKED=0 uv run --no-project python scripts/adr.py index

# ADR metadata and index
adr-lint:
    UV_LOCKED=0 uv run --no-project python scripts/adr.py lint

# Codex discovery and dead-reference check for agent instructions and skills
lint-agents:
    UV_LOCKED=0 uv run --no-project python scripts/check_agents.py

# Fail when `doctor` reports a missing or failing tool (part of `ready`)
doctor-check:
    #!/usr/bin/env bash
    set -uo pipefail
    out=$(just doctor 2>&1); status=$?
    printf '%s\n' "$out"
    [ "$status" -eq 0 ] && ! grep -qE 'MISSING|FAILED|below the declared floor' <<<"$out"

# The dedicated PostgreSQL 18 cluster 18/corpus (D3 §13): create or reconcile it from
# ops/postgresql/ (sudo, idempotent): config, roles, extension versions, `corpus` and cs_template
db-provision:
    @bash scripts/pg_provision.sh

# Restricted semantic publisher/reader principals and local peer mappings; no data deployment.
db-semantic-roles:
    @bash scripts/pg_semantic_roles.sh

# Start the cluster
db-up:
    @sudo pg_ctlcluster 18 corpus start

# Stop the cluster
db-down:
    @sudo pg_ctlcluster 18 corpus stop

# Cluster state, version, preload, checksums; expected vs installed extensions (corpus, cs_template)
db-status:
    @bash scripts/pg_provision.sh status

# Tool presence and the versions in use
doctor:
    #!/usr/bin/env bash
    for t in just uv git git-lfs gh rg cargo rustc cargo-nextest cargo-insta cargo-deny clang mold sccache ast-grep; do
      printf '%-14s ' "$t"; command -v "$t" >/dev/null && "$t" --version 2>/dev/null | head -1 || echo MISSING
    done
    printf '%-14s ' python; UV_LOCKED=0 uv run --no-project python --version
    printf '%-14s ' ruff; uv run ruff --version
    printf '%-14s ' pyrefly; uv run pyrefly --version
    UV_LOCKED=0 uv run --no-project python scripts/docs.py doctor

# Install declared documentation binaries and isolated test dependencies (network allowed)
bootstrap-docs:
    UV_LOCKED=0 uv run --no-project python scripts/docs.py bootstrap

# Build Markdown, Pagefind and offline link/fragment checks without product dependencies
docs:
    UV_LOCKED=0 uv run --no-project --offline --no-python-downloads python scripts/docs.py build

# Existing metadata checks plus a complete publication
docs-check:
    UV_LOCKED=0 uv run --no-project --offline --no-python-downloads python scripts/docs.py check

# Focused documentation/ADR regressions only
docs-test:
    UV_LOCKED=0 uv run --no-project --offline --no-python-downloads python scripts/docs.py test

# Build then serve the finished artifact; no watcher or reindex during serving
docs-serve port="8000":
    UV_LOCKED=0 uv run --no-project --offline --no-python-downloads python scripts/docs.py serve --port {{port}}
