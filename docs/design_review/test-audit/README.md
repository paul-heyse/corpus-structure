# Test code design principle audit

The separate living diagnostic account for test code, test evidence and shared infrastructure.
The [skill](../../../.claude/skills/design-principle-audit-tests/SKILL.md) owns method and the
[binding](../design_principles/binding/corpus-structure.md#test-code-design-principle-audit)
owns applicability and identities. This account diagnoses; reviews compare solutions and plans
own scheduled disposition. Publication authorizes no product repairs or qualification.

<a id="baseline"></a>

## Baseline

| Item | Inspected state |
|---|---|
| Date | 2026-11-05 |
| Audited source | `bc2208f9d6a12d3ad9cf71575fa1c6df388d885b` |
| Included dirty source/configuration | None; clean acquisition. Concurrent broad-audit/STATUS documentation edits are excluded from this test-source baseline |
| Standard | core3.3; heuristics1.0; test-assessment1.2; code-intelligence1.4 where applicable; repository binding |
| Previous account | 2026-11-02, source2495baae reconciled through25a23118; superseded as a current baseline, retained in Git |
| Kind | Full authored test-responsibility refresh; static architectural assessment |
| Publication | The commit publishing this account, distinct from the audited source |

Paths in topic pages are relative to `python/corpus-structure/` unless explicitly prefixed
with repository-root `scripts/`, `fixtures/`, `domains/`, `ops/`, `docs/`, or described as root tests.
Bare `test_*.py` module names designate semantic tests unless another family is named; shortened
production module paths designate `src/corpus_structure/`. All current source observations below
are **Interface-checked by source inspection,2026-11-05**;
no product behavior is freshly labelled Tested or Measured by this audit.

## Scope and method

The selected scope is all current authored Python under root/package test trees, plus shared
execution, prerequisite, ownership and qualification infrastructure. Production dependencies are
read far enough to understand the tested contract and assurance mechanism. Inline/doctest searches
of crates, product source, scripts, tools, services and domains found no additional maintained
inline test body. The Rust starter and nextest configuration remain included, with no Rust
functional coverage inferred.

The complete authored reading union is28root Python files/7,800lines and390package Python
files/107,101lines, all read in full. The reconciled package partitions are13core/5,401lines,
8schema/2,180lines,256semantic/72,226lines,112remaining/26,990lines and shared conftest/304lines.
The root reads the26root modules not assigned to infrastructure; the native contributor reads
test_native_auth and test_test_receipts. All five shared native/qualification scripts were read
completely; process-script and product dependencies were followed selectively. Output-truncated
source chunks were reread before declaring completion. Semantic coverage reconciles to82a–m
modules/22,152lines,84n–p modules/25,782lines (including36PDF modules/11,510lines),76q–z
modules/21,559lines and14support modules/2,733lines. Confirmed cross-partition reads fill named
skips; overlaps are not added.
These are source files and physical lines, not executable-node or test-pass counts. Authored
reference builders are included; JSON/binary references are assessed through provenance,
consumers and selected contents, without claiming every retained value was independently verified.
Historical standalone probes without a current assurance consumer remain excluded.

Reading is partitioned by responsibility: non-semantic product tests; schema/core and semantic
contracts; native/PDF infrastructure and receipt lifecycles. Semantic reading is further split
alphabetically to complete the large current scope. The root owns root/process tests, criteria,
source integration and publication. Contributors return exact coverage and limits; overlaps do
not increase the union. A fresh reviewer independently challenged material conclusions and source evidence before
publication. It confirmed the new local diagnoses, strengthened the ten-case rejection shortcut,
and narrowed the numerical perturbation observation to a local evidence limit under DTA-001;
it did not independently reread the complete source union.

Changes from the previous account, production-contract changes and completed TA packages are
investigation leads. Existing closures are checked in current source rather than inherited as
fresh passes. Representative scenarios include focused test selection, changed helper imports,
a tool failing before it reports violations, empty observations, wrong crop location, changed
compiler/schema inputs, early close/cancellation, actual-purpose authentication and interrupted
shared-cluster effects. No exhaustive trace or mandatory mutation campaign is imposed.

## How the foundations were assessed

- **FP-01/03:** follow scenario and lifecycle ownership, production composition versus synthetic
  kernel setup, and change propagation through helper imports. The six TA support extractions
  remain useful corrections; new private test-host specialization extends DTA-009's footprint.
- **FP-02:** distinguish consumed contracts from incidental implementations and identify which
  boundaries are actually exercised by doubles, native clients, CLI and SDK transports.
- **FP-04:** inspect independent canonical bytes, geometry, finite combinatorics, source readings,
  reference partitions and compiler identities separately from generated conformance. Shared
  validators are useful downstream setup; their own correctness needs independent expectations.
- **FP-05:** inspect invalid-input reachability, intended refusals, empty/partial/unknown states,
  process outcomes, resource acquisition and publication. LinkML invocation failure and a blank
  rendering fixture expose concrete discriminating-evidence limits.
- **FP-06:** examine case-defining defaults, mutable state, ambient targets and independent
  selection. The application sentinel is a substantial improvement; DTA-021 isolates controls
  that still depend on another test having run.
- **FP-07/A4:** assess cold/warm preparation, data movement, focused prerequisites, physical
  connection events, publication/reader lifetimes and recovery. DTA-018/022 explain unnecessary
  work structurally. Fresh committed clones, independent expectations and actual native
  authentication remain justified assurance. No timing shares or speedups are claimed.
- **Profile:** attributed evidence, unknown versus absent, pinned realizations and non-circular
  evaluation constrain applicable scientific/serving claims. Code-analysis-specific obligations
  are not imposed on unrelated process tests.

## Current diagnostic navigation

| Topic | Current concerns and retained identities |
|---|---|
| [Evidence and discrimination](evidence-and-discrimination.md) | DTA-001; DTA-023; reconciliation of006/007/010/011/013/015/019/020 |
| [Execution and qualification](execution-and-qualification.md) | DTA-018/021/022; narrowed003 question; reconciliation of002/017 |
| [Support structure](support-structure.md) | DTA-009; reconciliation of005/008/012/016 |
| [Retirement and transfer](retirement-transfer.md) | DTA-004/014 scoped correction and withdrawn broad diagnosis |

The new [test audit resolution coordinator](../../plans/test-audit-resolution_2026-11-05.md)
owns planned remaining work, all23 DTA dispositions/preservation obligations and the unnumbered
provenance/runner questions. Its status is Proposed; no repair or new qualification follows from
planning. The older [TA coordinator](../../plans/test-architecture-and-evidence_2026-11-02.md)
retains its completed packages and historical scoped conclusions without amendment. Renewed
manifestations do not erase those corrections or broaden their qualification. This account
remains the diagnostic source, not a duplicate execution ledger.

## Library and system-tooling assessment

Research connected actual test methods with pertinent local overviews under docs/libraries,
Context7 and exact installed sources. Installed pytest9.2.0, Hypothesis6.170.12, PyArrow26.0.0
and FastMCP4.1.3 agree with the pins. Current online documentation sometimes targets a later
patch; installed sources resolve consequential version details.

- **pytest:** fixture scope/finalization, monkeypatch restoration and hooks already provide
  useful mechanisms. Context7's version9.2.0 fixture documentation confirms pre-yield cleanup
  limits. DTA-021 concerns how assurance is composed across tests, not missing fixture features.
  [Fixture contract](https://docs.pytest.org/en/stable/how-to/fixtures.html#safe-teardowns).
- **LinkML:** DTA-001 identifies actual neglect of the linter's explicit process outcomes;
  JSON reports and exit-status semantics are available. Warning policy remains distinct from
  an unsuccessful invocation. Context7 plus installed1.12.1 CLI source settle the mechanism.
- **Hypothesis:** recursive/composite/schema-derived and grammar-aware generation are already
  used. Stateful rules/bundles can serve complex histories, but their absence alone is no
  defect. Broad suppressions and per-example cleanup are judged against each claim; the native
  codec explicitly rolls back each example. No blanket state-machine or fuzzing adoption follows.
  [Stateful capabilities](https://hypothesis.readthedocs.io/en/latest/stateful.html).
- **Arrow/model/scientific libraries:** native equality, metadata and validity operations do
  not replace independent semantics. Existing metadata-aware schema comparisons, precision/
  null controls, independent vectors and selective readers are strengths. Installed Arrow
  table/types source confirms equality excludes metadata by default and full validation may
  scan data; no blanket full-validation requirement follows.
- **FastMCP/AnyIO/Typer:** SDK clients, explicit stdio environment/lifetime, runner capture and
  actual child settlement are already leveraged. In-memory and wire claims retain separate
  scopes; test doubles do not establish provider execution.
- **SQLAlchemy/Psycopg/Alembic/PostgreSQL:** native clone preparation, NullPool where appropriate,
  savepoints, actual principals, parser/metadata inspection and SQLSTATE controls are useful
  established composition. DTA-022 concerns observation without a consumer, not lack of another
  database fixture plugin. Reusable validators and preparation are assessed under complete
  dependencies; cold-compiler and actual committed-isolation controls stay independent.

Read-only `pg_lsclusters` and `dpkg-query -W` inventory on2026-11-05 confirms PostgreSQL18.6,
pgTAP1.3.4, plpgsql_check2.10.16, pgBackRest2.60.0 and pgBadger13.3. Executable/source inventory
also finds pg_prove, pg_virtualenv, pg_regress and isolationtester/pg_isolation_regress. Tool
installation is distinct from database extension activation or successful end-to-end operation;
those were not exercised here. Dedicated18/corpus:5434 remains the normal owner; unrelated
18/main:5432 and18/tktest:5433 were untouched.

The [local system-tooling overview](../../libraries/postgresql/PostgreSQL_System_Tooling_for_Ubuntu.md)
identifies alternatives worth retaining: pgTAP for repeated SQL assertions; PostgreSQL's explicit
sessions/steps/permutations for SQL-only interleavings; pg_virtualenv for claims that require
cluster-level configuration isolation. They cannot substitute for Python retry behavior or actual
restricted authentication. No direct wiring was found in the bounded tests/scripts/ops/justfile
search, but this is not itself neglect. Existing lifecycle guarantees and integration burden
matter. No additional installation was justified and no tool was installed.
[Isolation-test contract](https://raw.githubusercontent.com/postgres/postgres/REL_18_STABLE/src/test/isolation/README),
[pgTAP assertions](https://pgtap.org/documentation.html).

## Limits and follow-through

No product tests, collection, provider calls, database operations or benchmarks were run for this
audit. Source-established unnecessary work is not a measured bottleneck. Existing failed and
interrupted qualification receipts retain their original dates, source/context and scope; this
audit closes no PCE, UM, provider, adoption or full-union acceptance obligation. Production causes
are followed only to judge test evidence, not to refresh the broad audit's DA baseline.

Each finding has one primary home. Stable IDs/anchors remain; removed diagnoses and their
supporting evidence are recoverable in Git. Current remaining observations are scheduled in the new resolution coordinator. Future
observations remain here until selected, with an explicit revisit trigger. Accepted architectural decisions do not establish implemented or tested correction.

## Publication checks — 2026-11-05

- **passed:** tracked-file/physical-line reconciliation via `uv run python` using `git ls-files`;
 418test/support Python files fully read, with duplicate contributor reading counted once.
- **passed:** `git diff --name-only bc2208f9 -- python scripts tests crates pyproject.toml
 Cargo.toml uv.lock Cargo.lock .config ops` is empty after concurrent broad-audit commit8d4d9e91;
 the captured test-source baseline remains applicable. Concurrent documentation is excluded.
- **not_run:** product tests, collection, provider/native controls, benchmarks, installations,
 `just test-all` and integrated hygiene; this diagnostic publication changes no product behavior.
- **passed:** `just docs-check`, log `build/test-audit-20261105-docs-check.log`; documentation
 publication only. No publisher/resolver implementation changed, so `just docs-test` is not_run.
- **passed:** `git diff --check -- docs/design_review/test-audit`; an ephemeral read-only anchor
 reconciliation accounts for23unique DTA identities, preserving001–020 and adding021–023.
- Root maintenance uses `just turn-end`; its result is reported with the publication commit.
 No design-alignment checker, process gate, library catalog or additional dependency was added.
