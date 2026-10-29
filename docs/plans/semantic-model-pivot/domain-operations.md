# Domain operations and producer integration

**Status:** In progress · **Created:** 2026-10-29 · **Proposed.** [Coordinator](../semantic-model-pivot_2026-10-29.md) owns state. Consumes O04/O05 and the [semantic binding](semantic-model-and-releases.md), [publisher](postgresql-and-publication.md) and [Arrow kernels](interchange-and-analytics.md).

## Current execution contract (2026-10-29)

**In progress; not package completion.** Execution began at `1ce2c19` under
[ADR-0027](../../adr/0027-bound-domain-operations.md). Runs pin interpretation, source/configuration
and operation dependencies. Source preparation, recorded agent work and final domain publication
are distinct capabilities; a `source_ready` response does not establish finished consolidation.
Existing selected defaults remain until SP-09. Explicit semantic modes use the current project/run
CLI and MCP extraction tool names. Existing phase-0 scope and finding ownership are unchanged.

Grading and adjudication remain automated without human input. This scope neither regrades prior
results nor reclassifies actual automated-agent evidence. Native protocol fixtures establish their
mechanics; no new model-quality result is claimed by their execution.

The operator selected positive accepted source-supported asserted/defined assertions as initial
inference seeds. Grounded derivations can support further conclusions; suppositions and negative
assertions are retained without becoming seeds. Meaning-bearing context is exact initially.
Protected publication must validate admitted direct proofs and authorization grounded in source
evidence, not merely their foreign keys.

The current implementation retains HTML5 recovery, CSS role matching, ambiguity-aware Lark,
spaCy math-as-word sentence processing and regex scanning. Selected changes are lazy spaCy Docs,
RapidFuzz token sequences and pseudo-element selector refusal. Tokenizers, additional document
backends and LinkML-Datalog remain deferred. Source reports and canonical instances stay separate.
Keyed LinkML collections remain maps rather than acquiring ordered-list meaning. Scope and source
macro environments remain explicit, and scientific assessments do not become proposition identity.

Complete scope still requires connected current producers, source task/cut protection, declared
identity and domain rules, protected source-to-output publication and focused native acceptance.
The coordinator owns package state; receipts and exact remaining obligations will be reconciled
against the assembled implementation rather than inferred from individual worker completion.

## Contracts and current footprint

Current `ingest/methods.py`, `methods/math`, `methods/llm`, `orchestrate/context.py`, `runs.py`, `tasks.py`, `intervene/submission.py`, `consolidate/assemble.py`, `pass_.py` and `validate/*` make the migration cross-cutting. Preserve source parsing, evidence meaning, task fencing and explicit domain algorithms; replace model/key/table interpretation through the shared binding. A release becoming usable in a toy writer is not completion of these consumers.

A run binds semantic release, source inputs/configuration, data realization and applicable operation versions once. `RunView` and method readers carry that binding. Reuse depends on all result-affecting source, ontology/vocabulary/rule/identity and operation versions. No request asks for 'latest model' after starting. The orchestrator orders operations; it does not reconstruct semantic applicability or turn new class definitions into one task each by default.

Observations report what a source/method established; consolidation decides which compatible facts and assessments are published. The database publisher enforces storage/acceptance invariants, not scientific truth or selection policy. Derived conclusions remain distinguishable from source occurrences. Unknown coverage and parse failure are explicit results rather than empty valid batches.

<a id="SP-06"></a>
## SP-06 — Source and producer binding migration

**Input:** SP-03 publisher and SP-04 write/read journey. **Owner:** ingest/methods/orchestration and submission integration.

Migrate source/rendition/span persistence to the new system metadata without changing what a successful read establishes. Keep source bytes, normalized renditions, provider configuration and source locators distinct. Agent and deterministic extraction consume the same release's boundary schema, term memberships and source frame. A newly admitted class/property is immediately available without a new per-property extractor branch.

Move method registries, run creation, task assignment, work-packet preparation, validation, fencing, observation writing, sealing and run completion to the new release/data contracts. Migrate actual current CLI/MCP entry points alongside their producer contracts, coordinating user-facing result changes with SP-08. Preserve bounded cancellation, stale-attempt refusal and retry identities. New model definitions are proposed then admitted, not activated by extraction.

Remove dependencies on installed-only payload upcasters and old key scheme dispatch from migrated paths. Keep pure parsing/normalization functions and already correct bulk evidence writes. Ordinary domain validation uses the binding, not a second list of permitted predicates. Do not finish unrelated omitted methods/policy features simply because their plans remain open.

**Completion:** every current producer/observation writer and orchestration reader uses the new binding and storage; no producer bypasses source/evidence policy. Native source → observation → publication journey plus focused independent cases for invalid vocabulary, unavailable required ontology, stale attempt, wrong release, interrupted task and identical source under a changed meaning-bearing policy. Verify stale reuse is rejected even when document bytes are unchanged. Agent extraction, grading and adjudication are automated without human input. This migration does not regrade prior results or relabel actual automated-agent evidence.

### Typed process configuration with Pydantic Settings

SP-06 retains `settings.py`'s one root `BaseSettings`, nested validated plain models and entry-point construction. Preserve explicit constructor > `CORPUS_*` environment > declared defaults via `settings_customise_sources`; `CORPUS_DATABASE__URL` remains the nested route. No implicit dotenv, secrets-directory, cloud or second CLI source is added. `SettingsConfigDict`, `Field`, cross-field validators and `SecretStr` provide configuration validation; extend only settings actually needed by release artifact paths, the database and operation resource bounds.

Resolve settings once in CLI/MCP lifespans and pass the validated object; domain operations and registered method configurations do not read the environment. Preserve current method configuration semantics (explicit data/default overlay, whole top-level replacement), rather than importing BaseSettings' deep source merging into semantic policy. A setting may select a release at operation start but cannot override a class meaning, constraint, identity policy or existing bound run. Record result-affecting nonsecret resolved configuration with run dependencies; redact secrets and avoid persisting credentials. Keep unknown environment-name diagnostics: `extra=forbid` alone does not catch every unrelated prefixed variable.

Focused controls exercise precedence, nested env values, bad keys, cross-field errors, masking and an environment change after a run starts. A semantic policy change still requires an admitted release. Sources: [Pydantic Settings overview](../../libraries/pydantic-settings.md), [settings documentation](https://docs.pydantic.dev/latest/concepts/pydantic_settings/). Native exact-pin checks belong to SP-00/SP-06; documentation is not their pass receipt.

<a id="SP-07"></a>
## SP-07 — Consolidation, validation and inference

**Input:** SP-06 observations and SP-05 pool/kernels. **Owner:** domain operations/consolidation; semantic policy remains in declarations/functions owned by D5's successor.

Rework assembly around occurrence → fact/support → accepted selection/assessment. Preserve two identical items from one source and two sources supporting one fact. Source conflicts survive; confidence aggregation and canonical display payload do not replace occurrences. Reuse set kernels only when they preserve occurrence multiplicity and context. Resolve entities under declared keys/cannot-links; external ontology mappings never act as unconditional merges. Nested references, n-ary roles and unresolved endpoints survive every lowering.

Use shared structural validators for consumer enforcement. Numerical/symbolic comparison, confidence and domain-specific decisions remain ordinary explicit operations with defined inputs, applicability, uncertainty and outcomes. Model-driven behavior does not require rewriting every algorithm in a generic rule language. Required integrity rules call SP-03's protected route; an application validation boolean cannot skip enforcement.

Compile supported positive inference through SQLAlchemy Core joins/set operations and recursive CTEs over a declared eligible fact projection. Class/subproperty hierarchy, inverse/symmetric and positive transitivity follow SP-01. Negative assertions never become transitive premises merely because polarity matches. Require fact-authorizing modality/establishment and compatible attribution, validity, scope and identical condition context initially. No general negation-as-failure over incomplete coverage.

Terminate recursive closure by semantic conclusion identity, not source occurrence IDs, fresh derived IDs or enumerated proof paths. Store compact rule/premise/support links separately; preserve multiple independent supports without infinitely reproducing a cyclic proof. Changed rules/retracted supports produce a new evaluated realization, initially through scope recomputation rather than a generic incremental truth-maintenance system. Publish results and derivations atomically under the same binding.

**Completion:** current consolidation/domain-verifier consumers migrated; independent fixtures establish selected values, conflicts, premise links and inferred conclusions. Include cycle termination, two proofs for one fact, incompatible contexts, negative-premise non-inference, n-ary roles, undecided scientific equivalence and unresolved references. Query/explain must trace a derived conclusion back through the recorded rule and source occurrences in SP-08. No whole-corpus RDF conversion per ordinary operation.

## Mechanisms and execution fit

Use the [SQLAlchemy plan](postgresql-and-publication.md) for relational composition and snapshots. Pull narrow eligible relations before Python hydration; use DuckDB where set work benefits from local columnar execution, without duplicating policy. Global operations retain the required universe; output selection is not input scope. Qualitative skew/access-path assessment belongs with the affected query, not a mandatory benchmark.

Sources: [review O04](../../functional_reviews/semantic-postgresql-model_2026-10-29.md#O04), [target inference](../../functional_reviews/semantic-postgresql-model_2026-10-29_target-model.md#5-validation-and-inference-semantics), [SQLAlchemy selectable constructs](https://docs.sqlalchemy.org/en/21/core/selectable.html). LinkML-Datalog remains deferred under the coordinator's trigger.
