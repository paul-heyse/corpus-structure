# Declared data operations — identity, reuse and provenance baseline

Supporting document for the
[declared data operations review](../design_review_declared-data-operations_2026-11-12.md),
which owns the findings and every remedy. This page records how identity, reuse and lineage
work at product source `8c0f4f951`.

**Evidence.** Interface-checked by source inspection, 2026-11-12, through a delegated read-only
mapping that also read the development database catalog. The review's author re-read the task
hash construction, `ops.task_dependency_scope`, `ops.valid_reuse`, the layer operation block and
ADR-0063. The rest was not re-read. Row counts are from the development database on that date
and describe that database only. Nothing was run.

**Path convention.** Paths without a prefix are relative to
`python/corpus-structure/src/corpus_structure/`.


**Audit reconciliation2026-11-12.** This remains an implementation/authority baseline,
not the target specification. The [corrected target](target-contracts-and-storage.md) and
[principal §§4–11](../design_review_declared-data-operations_2026-11-12.md#4-corrected-target-state)
supersede original proposed mechanisms; the [companion](../audits/design_review_declared-data-operations_2026-11-12_audit.md)
records every recommendation disposition. Original dated counts and unrefreshed observations
remain historical, not new execution evidence.


## Identities in use

| Identity | How it is computed | Where |
|---|---|---|
| Run id, task id, cut id | Database sequences | `ops.run`, `ops.task`, `ops.input_cut` |
| Task invocation key | Random | `ops.task`; hashed into observation keys |
| Task `input_hash` | Hash of release, input realization and revision, the scoped run dependency manifest, method name and version, config hash and the method's input digest, plus optional producer origin, native thread profile and freshness seed | `orchestrate/semantic.py:701-745` |
| `config_hash` | Hash of method, version and resolved parameters, with references inlined and artifacts replaced by their hashes | `core/evidence.py:197-199`, `orchestrate/registry.py:170-223` |
| Method | Name and a hand-declared version string; a trigger refuses a changed configuration schema under one version | `semantic/operations.py:215-249` |
| Release id | Hash of the canonical release manifest | `semantic/prepare.py:866-882` |
| Runtime id | Hash of a manifest of the release, compiler and interpreter versions and about 150 owned source files | `semantic/runtime_bindings.py:100-150` |
| Code commit | Git head with a dirty marker; informational | `core/provenance.py:7-22` |
| Run dependency digest | Hash of the run's dependency manifest | `orchestrate/semantic.py:467-583` |
| Realization id | Named by the caller, usually from a run | Prefix of every `data.*` primary key |
| Fact, occurrence and alternative ids | Hashes that include the release and the realization | `semantic/identity.py:41-78` |
| Observation key | Hash that includes the release, the task hash and the invocation key | `semantic/operations.py:420-437`, `semantic/observations.py:224-239` |
| Source artifact | Hash of the original bytes | `kb.source_artifact` |
| Source-view key | Hash that includes the consuming release and the native pin with its task id | `semantic/sql/source_views.sql:166-169` |
| `ProductReference` | Producing task id, product key and content digest | `semantic/product_reference.py` |
| PDF build id | Hash that includes the task id | `semantic/pdf_staging.py:135-160` |
| Provider and model profiles | Hashes of declared profile fields, with acquisition location excluded | `methods/native_profiles.py:60-175`, `methods/gliner.py:137-141` |

Fingerprint exclusions are scattered in code: model snapshot location, artifact paths in batch
receipts, resolved device placement, and manifest keys dropped per method. The
`data.identity_exclusion` table and its comparison tool are unrelated; they record that two
references are not the same entity.

## Fingerprint machinery

**Task reuse key.** The run dependency manifest holds library versions chosen by hard-coded
lists per method set, every source document's identity, selected sources, characterization view
pins, every operation's version and configuration, guideline, agent configurations, corpus,
scope and policy. `ops.task_dependency_scope` narrows it for `extract.m1_annotations` and
`extract.m1_candidates` only. For every other method it removes two admission keys and keeps
the rest, so a change to any operation's configuration or any listed library changes every
method's scope.

**Code.** Executable bytes are absent from the task hash. They enter through `ops.valid_reuse`,
which requires an equal `ops.run.runtime_id`.

**Characterization layer operation block.** Built at `orchestrate/semantic.py:1007-1024` with
key, version, runtime, configuration, input, model, grammar and context, and extended with
produced families, required layers, preconditions, effects, result determinants and outcomes
(`methods/native_evidence_layers.py:88-110`). Its schema is `CharacterizationOperation`
(`model/semantic/characterization.yaml:66-100`). The whole layer, including this block, is
hashed into its content digest, so the digest changes with runtime and task hash.

**Release comparison.** `compare_semantic_releases` (`semantic/operation_reporting.py:763`)
diffs two releases' declared members and lists directly referenced consumers, retaining unknown closure; it does not implement the proposed transitive data-operation impact graph. Runtime and
implementation changes are reported as unknowns. It invalidates nothing.

## Run-keyed and content-keyed data

| Keying | Tables |
|---|---|
| Content only | `kb.source_artifact`, `sem.*` by release, `ops.method_config` by config hash |
| Task id plus content digest | `ops.characterization_product`, `kb.characterization_*`, `ops.pdf_product*`, `kb.pdf_*` |
| Task id only | `ops.task_result`, `kb.source_contribution*`, `kb.contextual_*`, `kb.observation` |
| Run | `ops.run`, `ops.task`, `ops.input_cut`, `ops.cut_task`, `ops.completed_result`, `ops.run_source_view`, `ops.measurement` |
| Realization and release | Every `data.*` table |

## Provenance and history

**Recorded per derived object.** The task row holds its configuration, hashes, unit, status,
attempt, timestamps and `reused_task_id`; `ops.task_result` holds the bound report. The run
row holds its dependency bytes, options, runtime id and code commit. Layers hold their
operation block, dependencies and native run profiles.

**Lineage edges.** `ops.task_dependency` (425 rows, one kind, in the development database);
`kb.observation_input` (no rows there); `ops.pdf_product_input`; layer required layers;
`data.fact_input` and `data.entity_input`; `data.derivation_premise`; `ops.cut_task`.

**Append-only.** About 120 tables refuse mutation, including `data.*` facts and records,
`kb.*` products, PDF and characterization products and `sem.*`. Each publish appends a
`data.batch` row holding the batch content and its digest at a new revision, so a realization
at revision N is the union of its batches. There are no retractions; selection is additive.

**Overwritten in place.** Task status, attempt, holder and lease; run status and seal;
realization state and revision; project activation pointers; PDF stage build state. No history
of these is kept, and no activation history table was found (*inferred*).

**Served reads.** `source_decision_journey`, `contributions` and `records` reconstruct their
answers at read time from a pinned completed result. None is backed by a stored journal.

## Reuse and what a change invalidates today

Reuse is an exact twin: `create_task` (`semantic/operations.py:301-363`) finds a prior done or
empty task with the same configuration, input hash, unit, packet hash, project, release,
runtime, input realization and revision, and an equal scoped manifest, and records the new
task as reused. The development database held 2,409 tasks, 1,628 distinct input hashes and 45
reused tasks.

| Change | Effect today |
|---|---|
| One method's configuration | That method's tasks, and every other method's except the two M1 methods |
| A listed library version | All methods |
| Any of the runtime-listed source files | No task reuse |
| Any release change | No task reuse |
| Fresh result wanted | A hash salt or a per-method `fresh` flag |

Nothing is invalidated in place. A new run creates new tasks and reuses twins or recomputes;
earlier products remain. Upstream reuse without recomputation is explicit pinning of product
references through run options.

## Intermediate state

Originals are stored by content digest. PDF parse and recognition output is staged, then
published to product tables. Language annotations are observations and characterization
layers. Step inputs are retained as immutable pinned products, so a later run can pin them,
but only under a new run, and their identity is tied to the producing task.

## Obstacles to operation-derived identity

- Observation keys include a random invocation key.
- Product primary keys include the task id.
- Fact and occurrence identities include the realization.
- Most methods' reuse scope is the whole run manifest.
- Task and run state is updated in place.
- The runtime manifest includes the release, so a runtime cannot be named across releases
  (`semantic/runtime_bindings.py:107-112`).
