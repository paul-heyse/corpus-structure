# Boundaries and composition

These findings concern module and library boundaries, configuration and lifecycle in the
go-forward architecture, at the [audited baseline](README.md#baseline). The operator scoped the
audit to the go-forward design. Legacy modules are therefore examined only at the edges where
go-forward code depends on them ([DA-045](#da-045)).

Paths are relative to `python/corpus-structure/src/corpus_structure/` unless they start with
`scripts/`, `ops/` or `docs/` (repository root), or `rev/`
(`python/corpus-structure/semantic_alembic/versions/`).

<a id="da-018"></a>

## DA-018 — Retired at this baseline

*Was: "Server extension versions are neither pinned nor reconciled, and the test template ignores
them" (2026-10-28).*

Phase 0 corrected it before the pivot:
- `ops/postgresql/extensions.txt` records each expected `extversion`;
- `scripts/pg_provision.sh` installs and verifies them (`:45-53`, `:115-121`);
- `core/db/extensions.py` refuses a mismatched database at `ci db init` (`cli/db.py:84-94`) and at
  every engine open (`core/db/store.py:93-94`);
- the semantic test fixture checks them too.

Verified 2026-10-29 at `ad4593f`. The earlier text is in Git.

<a id="da-019"></a>

## DA-019 — Retired at this baseline

*Was: "Test-database sweeping can drop a template another live session is using" (2026-10-28).*

The legacy fixture now takes advisory-lock leases and sweeps only what it can lock
(`python/corpus-structure/tests/conftest.py:18-20`, `:65`, `:167`, `:242-295`). The semantic
fixture creates a unique database per test and has no sweeper. Any remaining residue and harness
design belong to the [test audit](../test-audit/README.md) (DTA-002). Verified 2026-10-29. The
earlier text is in Git.

<a id="da-020"></a>

## DA-020 — Cluster coordinates, principal names and resource settings are repeated or unconsumed

**Principles:** DP-01, DP-20, DP-24, FP-02. **Subject:** implemented, and design text.

*Continues the 2026-10-28 finding. The repetition has moved into the semantic additions.*

### Diagnosis

**Coordinates and names.**
- Port 5434 is read from `ops/postgresql/corpus.conf:5` by `scripts/pg_provision.sh:21`, and
  hard-coded again in `scripts/pg_semantic_roles.sh:5,9,60` and `settings.py:35-36`.
- The template name appears in `pg_provision.sh:24`, `settings.py:38` and
  `core/db/extensions.py:17`.
- The database name `corpus_semantic` exists only in `settings.py`; provisioning creates `corpus`
  (`pg_provision.sh:104-109`).
- The four restricted role names are literals in six Python modules and the shell script.

**Resource settings no longer match their consumers.**
- `AnalyticsSettings.threads`, `memory_limit` and `scratch_path` (`settings.py:69-75`) are never
  consumed. The only go-forward `AnalysisScope` uses duplicated constructor defaults
  (`semantic/domain_operations.py:2044`; `semantic/analytics.py:490-506`), with scratch space outside
  the configured path.
- `LlmSettings` and `GpuSettings` have no go-forward consumer, and `--gpu-mode` is refused.
- Execution resources are hard-coded instead:
  - the lease is 5 minutes in both Python and SQL (`semantic/operations.py:314`;
    `rev/semantic_0023_execution.sql:353`);
  - the provider timeout is 1800 s with 120 turns (`intervene/automated.py:35`, `:144-145`);
  - the pool size is 4 (`semantic/runtime.py:67`).
- The generic `ci regenerate` defaults to `slice="trace"`, which only the statistics pack defines
  (`cli/regenerate.py:104`).

**Stale design text.** D3 §13 still describes the `corpus` database and read-only sessions through
`corpus_ro` (D3:1592, D3:1616). That role holds `pg_read_all_data` and is granted to the owner
(`pg_provision.sh:97-102`), which makes it a read path outside the semantic principal model
([DA-030](native-integrity.md#da-030)).

### Consequence

Low for coordinates, because mismatches fail loudly. Moderate for settings:
- `CORPUS_ANALYTICS__MEMORY_LIMIT` has no effect, yet `settings_report` shows it as resolved;
- the consolidation memory budget cannot be adjusted;
- the prose misdirects an operator.

**Evidence:** diagnosed from source.

<a id="da-045"></a>

## DA-045 — Go-forward contracts still live in legacy modules, and one layer depends upward

**Principles:** FP-01, FP-03, DP-13–DP-17 (DP-17: module boundaries follow ownership), DP-18, A1.
**Subject:** implemented.

### Diagnosis

The go-forward architecture owns its release, publication and serving contracts. It does not own
several contracts it runs on, which still live in modules the pivot treats as legacy. This is
recorded as boundary facts. The legacy internals were not audited.

| Contract the go-forward code relies on | Legacy owner | Go-forward consumers (examples) |
|---|---|---|
| Method contract, `Reader`, `UnitResult` | `core.method` | `semantic/operations.py`, `observations.py`, `operation_results.py` |
| Execution and observation enums (task unit, observation kind and outcome, run kind, measurement scope, run and task status) | `core.vocab`, generated from the legacy `model/core.yaml` and `system.yaml` | `semantic/operations.py:28,131,739-923`; `orchestrate/commands.py:13`; `cli/orchestrate.py:24` ([DA-012](structure-and-invariants.md#da-012)) |
| kb identity recipes (`document_key`, `rendition_key`, `segment_key`, `content_digest`) | `core.evidence` | `semantic/operations.py:480,526` |
| Connection pool and extension check | `core.db.store.open_store`, `core.db.extensions` | `semantic/runtime.py:70`; `cli/db.py` |
| Physical compiler, naming convention, digest CHECK names | `schema.relational` | `semantic/metadata.py:18` ([DA-031](native-integrity.md#da-031)) |
| Rule-visible view types and kernels | `schema.rules`, `schema.rulelang`, `validate.views` (including private names), `pool.steps`, `pool.duckdb_engine` (private SQL), `consolidate.finalize.GRAMMAR_KINDS` | `semantic/domain_operations.py:2298-2454, 2938-2950`; `semantic/analytics.py:40, 673, 757` ([DA-005](semantic-model-and-authority.md#da-005)) |
| Scientific equivalence | `evaluate.equivalence` (private `_constraints`), `core.values` | `semantic/domain_operations.py:2183-2249, 2627, 2811` ([DA-034](semantic-model-and-authority.md#da-034)) |
| Locator grammar, canonical JSON for tokens, label normalization | `core.locators`, `core.canonical`, `core.keys.normalize_label`/`LabelRules` | `semantic/source_frames.py`, `proposals.py`, `source_projection.py`; `serve/journey.py`; `semantic/domain_operations.py:817-974`; `evaluate/semantic_alignment.py` |
| Pack location and run configuration | `schema.pack.DOMAINS`, `orchestrate.phase0` (which imports legacy `consolidate.pass_` and `validate.runner`), `orchestrate.registry`, `orchestrate.policy`, `orchestrate.runs.code_commit` | `orchestrate/commands.py`, `project.py`, `cli/regenerate.py`, `cli/orchestrate.py`, `semantic/regeneration.py` |

Two contract defects sit at these edges. They are in go-forward code, not in the legacy modules:
- **The method boundary's read-only promise is a convention.**
  - The legacy contract documents `Reader.connection()` as "a read-only connection"
    (`core/method.py:226-228`). The go-forward `BoundReader` returns the run's own connection
    (`semantic/operations.py:905-908`).
  - `method.select` runs inside the task-creating transaction (`orchestrate/semantic.py:211-217`).
  - Methods issue raw SQL against `kb.document`, `kb.rendition` and `ops.run`
    (`ingest/methods.py:155-163, 175, 256-261, 274-279`; `methods/math/methods.py:163`;
    `methods/llm/packet.py:458`).
- **One layering inversion.** `semantic.contracts`, the semantic authority layer, imports the
  execution layer (`orchestrate.project`, `orchestrate.semantic`; `semantic/contracts.py:37`).

### Consequence

- Changing a go-forward method contract, execution enum, physical naming rule, rule-visible field
  or equivalence rule means editing a module the plans treat as retiring.
- Importing the semantic run path imports the legacy `consolidate` and `validate` packages.
- SP-09 retirement of these modules is blocked by live edges no retirement list names (the leverage
  review recorded that SP-09 names no module list).
- Method plug-ins encode physical table names outside the MetaData.
- The read-only, run-scoped method contract is not enforced, although natively the writer cannot
  write `data` or `sem`.

### Counterevidence

Several of these are deliberately reused pure algorithms. The pivot coordinator says "useful pure
algorithms … remain". The defect is the unowned contract and the direction of the dependency, not
the reuse.

**Evidence:** import facts observed at `ad4593f`. The contract defects are diagnosed from source.

<a id="da-047"></a>

## DA-047 — Surfaces are maintained without a go-forward consumer

**Principles:** DP-16 (G7), DP-01; AGENTS.md "check that it has a real consumer". **Subject:**
implemented.

### Diagnosis

Several go-forward surfaces are built, versioned or rendered with nothing consuming them:

| Surface | Evidence |
|---|---|
| The `data.selected_fact` view | Created in revision 0002. No Python or native consumer; `semantic/query.py:436-445` re-expresses the accepted projection directly |
| Authored SQL | Admission, archival and the native admission requirement all exist (`semantic/authored_sql.py`; `require_execution_release`). Nothing executes authored SQL, no pack supplies any, and the current activation route cannot admit it ([DA-030](native-integrity.md#da-030)) |
| `record_direction` and `ops.intervention` | The MCP tool writes free-text directions under `actor="agent:session"`. No go-forward Python reader exists (SQL readers were not searched exhaustively) |
| The `propose_claims` schema hash | Substituted with the expected value when the agent omits it (`intervene/semantic_server.py:388`), so attestation is optional. Packet integrity is still re-derived server-side |
| The consolidation `fuse` product | Built over an empty `CandidateInput`. Its only use, `candidate_facts - fused_ids`, is decidable from the batch (`semantic/domain_operations.py:2011-2022, 3101-3103`) |
| `StatusReport.orphaned` | Always `[]` (`orchestrate/commands.py:298, 340`), while `cli/status.py:67-69` renders an orphan hint ([DA-041](structure-and-invariants.md#da-041)) |
| CLI options `--agent-reuse by_unit` and `--wait` | Advertised (`cli/orchestrate.py:139-140`), but refused by the semantic run path (`orchestrate/semantic.py:69-77`) |
| `PreparedRelease.queries` | Trivial per-class descriptors with no consumer |
| `semantic/routines.py` and `semantic/sql/*.sql` | Dead and stale ([DA-032](native-integrity.md#da-032)) |

### Consequence

Each surface needs maintenance and review and suggests a capability that does not exist. Two of
them create real hazards:
- the dead `deploy_routines` would grant UPDATE broadly;
- the optional schema hash weakens an attestation the protocol appears to require.

**Evidence:** diagnosed from source. Absence claims rest on grep over the go-forward packages, and
dynamic access was not traced.

<a id="da-052"></a>

## DA-052 — Claim-proposal production is welded to the interactive `agent.opus` path, not to a declared producer contract

**Principles:** FP-03, DP-02, DP-08, A2; §E change locality. **Subject:** implemented.

### Diagnosis

Native code recognizes agent work generically, by method tier or family `'agent'`
(`rev/semantic_0018_*.sql:24`; `rev/semantic_0020_*.sql:25`; `rev/semantic_0023_execution.sql:188, 370`).
Python binds it by the method *name* `agent.opus` at five sites:
- propose (`orchestrate/semantic.py:99, 523, 584-591`);
- the MCP lease (`intervene/semantic_server.py:126`);
- the automated provider (`intervene/automated.py:57, 202`).

Status reporting uses a third predicate, tier (`orchestrate/commands.py:316`; [DA-003](semantic-model-and-authority.md#da-003)).

The agent's operation contract has two sources:
- the registered `AgentOpus` method declares version, family, tier and confidence source
  (`methods/llm/agent_opus.py:100-107`);
- `queue_agent` builds its own literal descriptor and hashes configurations by a second scheme
  (`orchestrate/semantic.py:468-480`; compare `orchestrate/registry.py:220`).

Methods are registered through a hard-coded tuple in `orchestrate/phase0.py:88-95`, which imports
legacy `consolidate` and `validate` code.

Claim proposals have one writer and one reader:
- only the MCP commit writes `AgentStoredBatch` (`intervene/semantic.py:218-220`);
- source-path producers can write only `SourceObservation` (`semantic/operations.py:707`);
- consolidation projects only `AgentStoredBatch` (`semantic/domain_operations.py:1224-1231`), and
  every other report becomes `unanalysed` coverage.

### Consequence

Scenario SC5 shows what a second producer meets:
- **A second agent method** (another name, tier `agent`) is refused at propose. If queued another
  way, it would never be leased by MCP or the automated provider, and its open tasks would block
  finalization forever (`orchestrate/commands.py:268-275`).
- **A hosted-model producer** (tier `hosted_llm`) cannot contribute claims at all. Native code does
  not treat it as agent work, so the hold-and-resubmit protocol does not apply.
- **A cheaper model as a second `agent.opus` configuration** works only in manual MCP mode, with
  misattribution possible ([DA-051](served-claims.md#da-051)). The automated provider refuses it.
- **Adding a tier** means editing descriptor literals and five name checks.

### Counterevidence

A cheaper model can be configured under `agent.opus` (`AgentOpusConfig.model`), and native
recognition is already generic.

**Evidence:** diagnosed from source (W2-C scenario SC5, 2026-10-29).

**Related:** [DA-026](semantic-model-and-authority.md#da-026) (operation bindings),
[DA-045](#da-045) (legacy registry and method contract).
