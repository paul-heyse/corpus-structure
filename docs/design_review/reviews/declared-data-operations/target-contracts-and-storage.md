# Declared data operations — target contracts and storage

Supporting document for the
[declared data operations review](../design_review_declared-data-operations_2026-11-12.md),
which owns the findings, the corrections C1 to C7 and their order. This page gives the
proposed declaration shape, binding, storage changes and special-case fit in the detail a plan
would need.

**Everything here is Proposed.** Names are conceptual: they express required meaning and do
not fix a type, table or file. The fit readings come from a delegated planning pass over the
code on 2026-11-12 and were not all re-read by the review's author. Nothing was run.

**Path convention.** Paths without a prefix are relative to
`python/corpus-structure/src/corpus_structure/`.

## Declaration

A `data_operations` section in `model/semantic/execution-model.yaml`, compiled to a sibling of
`OperationContract` in `semantic/contracts.py`. `OperationContract` stays for database and
protocol actions. The form generalizes three declarations that already exist:

- `CharacterizationOperation` (`model/semantic/characterization.yaml:66-100`): key, version,
  model, grammar, configuration, context, produced families, required layers, preconditions,
  effects, result determinants, outcomes.
- Analysis demands (`execution-model.yaml:14708`): an id, prerequisites and named
  determinants.
- Parsing adapters (`execution-model.yaml:14766`): implementation, frontend and grammar
  revisions and capabilities.

| Field | Meaning |
|---|---|
| `id` | Stable operation identity |
| `subject` | The concept the operation is applied to |
| `effect` | `derive` a new product; `augment` a base product with a layer; `author` a selection |
| `executor` | In-process, native host, or external agent |
| `behavior_version` | Bumped by hand when the operation's behaviour changes |
| `consumes` | Kinds, each with an optional family, a role, the outcomes that satisfy it, and whether it is optional |
| `produces` | One kind, with its families |
| `applicability` | Conditions on the subject beyond input presence |
| `determinants` | The parameters, assets, provider profile and numerical policy that affect the result |
| `outcome_domain`, `implementation` | As in existing contracts |

**Kinds** are existing concept ids, qualified by layer family where a concept has families.
Each kind needs a contract digest compiled with the release. Whether that digest is derivable
from the member walk the release comparison already performs is inferred, not verified.

**Applicability** is a conjunction of two row forms only:

1. a consumed kind is present for the subject with an outcome in a declared set;
2. a declared facet of the subject equals a literal, for example analysis eligibility
   (`methods/m1_source.py:319`).

Both project to fixed release relations, so SQL evaluates a semi-join and Python reads the
same rows. Existing invariants cannot carry applicability because they have no evaluator.

**Fingerprint.** A hash of the id, behaviour version, parameters, asset digests, provider
profile identity, numerical policy, and the contract digests of consumed and produced kinds.

## Configuration split

Today a `Config` carries three different things, and hashing it whole would give one operation
version per subject:

| Part | Role in the target | Example today |
|---|---|---|
| Parameters | Determinant; part of the operation version | Thresholds, model and grammar selections |
| Subject selection | The demand's subject set | Selectors in `methods/native_evidence.py:45-47` |
| Input pins | The derivation's inputs | Layer pins pushed through configuration by `orchestrate/characterization.py`; `cfg.inputs` in `methods/structural_products.py:1328` |

## Adapter binding

`Method` keeps `select` and `run`. Its name, version, family, tier, unit type, `Config` and
`input_digest` move to the declaration. A generated port per operation supplies typed
parameters and declared-kind inputs, following `render_operation_calls`
(`semantic/operation_call_generation.py:675`). `plan`, `original_recipe` and `close` become
declared port capabilities in place of `getattr` discovery.

## Storage

**New.**

| Record | Content |
|---|---|
| Operation version | Operation, ordinal, fingerprint, determinants, first release |
| Product kind | Release, kind, contract digest |
| Data operation and its consumed kinds | The projected declaration rows used for eligibility |
| Derivation | Key, operation version, subject key, replicate, outcome, runtime identity, task, demand, times |
| Derivation input and output | The exact products consumed and produced |
| Revocation | Operation version, runtimes, reason |
| Operation version change | What changed between two versions of an operation |

**Changed.**

- `ProductReference` becomes kind, subject key and content digest. Product primary keys
  follow, with task and release as provenance columns.
- The source-view key drops the consuming release and the native task id
  (`ingest/pdf_hierarchy.py:348-370`).
- Observation keys drop the release and invocation key and use the derivation key.
- The task's input hash becomes the derivation key.
- The layer operation block shrinks to the operation version, so that a layer's content digest
  stops changing with runtime and task hash.
- The cut's task set becomes a derivation set.
- The runtime manifest drops the release.

**Dropped.** `ops.task_dependency` and its check; `ops.run_source_view`; `reused_task_id` and
the `reused` status; `ops.valid_reuse`; `ops.task_dependency_scope`; runtime equality as a
reuse condition; the random invocation-key default; `ops.method` and `ops.method_config`.

**Migration.** Forward migrations that drop and recreate from `model/semantic/physical.yaml`,
with no data transforms. Derived products are regenerated. Frozen revisions are left alone.

## Why product identity is content and not derivation

A product keyed by its derivation would change identity whenever its producing operation's
version changed, even if its content did not, and every consumer would then need updating.
Keying by content, with derivations as provenance that may share a product, means a rerun
producing identical content leaves consumers valid without comparing anything on read. D6 §4
already states this intent. It does not hold today because layer payloads embed the runtime
and the task hash.

## Why dependencies are not stored as planned edges

Dependent tasks are registered after their parents settle and the edge rows are written then
(`orchestrate/semantic.py:1236-1300`), so the stored edges are lineage, not a schedule.
ADR-0084 requires that order. The target keeps it: the planner decides what is eligible from
declarations and derivations, and derivation inputs carry the lineage.

## Fit of special cases

| Case | Reading | Adjustment |
|---|---|---|
| PDF private build (`orchestrate/pdf_streaming.py`, `semantic/pdf_staging.py`) | Its lifecycle of open, frozen, published and abandoned is an attempt workspace | Not recorded as history. `PdfBuildRef` is re-keyed by derivation key with task, attempt and holder as fences, so a frozen build survives a new demand |
| External agent tasks | Awaiting an agent is eligible and externally assigned | Declare the executor. The packet hash is the input pin. Policy trigger and run options, which enter identity today (`orchestrate/semantic.py:1653`), become demand provenance |
| Run-unit `structure.*` methods | Their inputs arrive through configuration | The subject becomes a content-addressed authored selection |
| `consolidate.claims` | Not a derivation in this model | Stays per run with the cut as its subject |
| `fresh` and the freshness seed | Hash salts (`orchestrate/semantic.py:731-744`) | A distrusted result is a revocation. A wanted rival observation is an explicit replicate on the derivation, selected explicitly under ADR-0082 |
| Non-deterministic GPU providers | Reuse selects an authentic retained observation under ADR-0085 | None. The determinant is the declared numerical policy |
| Source-view membership copied on reuse | `ops.select_reused_source_views` exists because membership is per run | Disappears; membership is the demand's subject set |
| Thread profile in the hash | `execution_native_profile` enters for primary producers (`orchestrate/semantic.py:729-730`) | Removed. Device class and dtype stay determinants through the provider profile |
| Cross-release inputs | Execution binds one release (ADR-0027) | Inputs are admitted by kind contract digest. An existing test already covers a new rule release reusing an original native layer (`tests/semantic/test_characterization_native.py:873`) |

## What a plan would still need to settle

- Whether a per-kind contract digest can be compiled from the existing release member walk.
- How fine the digest must be so that an edit to a shared model mixin does not change every
  kind.
- Which methods cannot separate parameters from selection.
- The reported form of update need for the `ci` view and the served read.
