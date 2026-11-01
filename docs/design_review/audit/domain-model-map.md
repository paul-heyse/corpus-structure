# Domain model map

This page describes the go-forward domain model as found at the [audited baseline](README.md#baseline)
(`ad4593f`, 2026-10-29). For each meaning it records:
- who owns it;
- how it is represented in each context;
- which definitions claim authority over it;
- which translations connect the contexts;
- how much of it is realized.

It is descriptive. Deviations are diagnosed on the topic pages and linked by `DA-nnn`.

**Status labels:**
- **implemented:** code at the baseline (existence only, unless a test or probe is named);
- **partial:** implemented, but not governing everything it claims;
- **target:** accepted design;
- **gap:** the meaning has no owner.

Paths are relative to `python/corpus-structure/src/corpus_structure/` unless they start with
`domains/`, `sources/` or `semantic_alembic/`.

The pre-pivot map (authored/stored/keyed-candidate contexts and the `ent:`/`clm:` key scheme) is
superseded and recoverable from Git.

## Authority chain in one picture

```
authored pack (domains/<p>/semantic.yaml + operation files)  ─┐
installed trusted modules (model/semantic/core, agent, ...)  ─┼─> source bundle ─> prepare_release ─> PreparedRelease
trusted execution model (execution-model.yaml, contracts)    ─┘                                         │
trusted physical model (physical.yaml) ─> MetaData (via legacy schema.relational) ─┐                    │ persist (owner)
                                                                                    v                    v
                              frozen semantic_alembic revisions (hand SQL) ─> sem.* release rows, data.* core, ops.*, kb.*, eval.*
                                                                                    │
                    domain operations (Python) ─> protected staging ─> native publish_contract_batch (recomputes identity)
                                                                                    │
                       read kernel / serve / MCP / evaluation  <─ load_release (re-derives the release) + snapshot
```

Release preparation is pure and explicit-input. Once archived, the release is immutable and
byte-exact. Instances live in PostgreSQL. The weak links are where a later context re-decides a
meaning instead of consuming the release:
- native guards that bind by name ([DA-026](semantic-model-and-authority.md#da-026));
- runs that read live pack files ([DA-028](semantic-model-and-authority.md#da-028));
- equivalence ([DA-034](semantic-model-and-authority.md#da-034));
- coverage ([DA-035](served-claims.md#da-035)).

## Contexts

| Context | What it is | Names and identity | Where defined | Status |
|---|---|---|---|---|
| Authored pack | Pack LinkML plus operation files: methods, policies, slices, guideline, `queries.py`, legacy-format `schema/rules.yaml`, `eval/split.yaml`; source profiles | Prefixed CURIEs (`stat:`, `toy:`) | `domains/*`, `sources/*.yaml` | implemented |
| Trusted semantic modules | core, agent, observations, reference, analytics, metrics | Installed, archived per release | `model/semantic/*.yaml`; `semantic/regeneration.py`, `proposals.py`, `observations.py` | implemented |
| Trusted execution model | Catalog of concepts, relationships, invariants, lifecycles, operations and projections, compiled against `contracts.yaml` | `execution:<sha>`; compared with the current model at activation | `model/semantic/execution-model.yaml`, `semantic/contracts.py` | partial ([DA-027](semantic-model-and-authority.md#da-027)) |
| Trusted physical model | Fixed tables leading to SQLAlchemy MetaData | `physical:<sha of file>` | `model/semantic/physical.yaml`, `semantic/metadata.py` (edge: legacy `schema.relational`) | implemented ([DA-031](native-integrity.md#da-031)) |
| Source bundle | Explicit bytes and dependencies | Artifact names and digests | `semantic/types.py`, `semantic/regeneration.prepare_packs` | implemented |
| Prepared release | Definitions, vocabularies, adapters, registry rows, artifacts | `release:<sha manifest>`, which includes library and compiler versions | `semantic/prepare.py`, `semantic/types.py` | implemented ([DA-009](semantic-model-and-authority.md#da-009), [DA-042](execution-fit.md#da-042)) |
| Archived release and `sem.*` rows | Immutable archive; class, property, vocabulary and registry rows | `release_id` | `semantic/releases.py` (`_projection_rows`, `persist_release`, `load_release`) | implemented ([DA-029](native-integrity.md#da-029)) |
| Project, realization, selection pointer | Active release and selected completed result under a generation CAS; a realization bound to one release, with a data revision | `project_id`, `realization_id` | `semantic/runtime.py`, `semantic/releases.activate_release`, `data.project`, `data.realization` | implemented |
| Run binding | `OperationBinding` plus a dependency manifest of live inputs | `ops.run.id`, binding digest | `semantic/operations.py`, `orchestrate/semantic.py` | partial ([DA-028](semantic-model-and-authority.md#da-028)) |
| Source custody and reports | Documents, renditions, segments; `SourceObservationBatch` | `observation:<sha>`, kb keys from legacy `core.evidence` | `model/semantic/observations.yaml`, `semantic/observations.py` | implemented ([DA-012](structure-and-invariants.md#da-012)) |
| Agent proposal | Authored batch, then stored batch with located evidence | Packet-local ids, `unit_ref`, the `outside` sentinel | `model/semantic/agent.yaml`, `semantic/proposals.py`, `intervene/semantic_server.py` | implemented ([DA-026](semantic-model-and-authority.md#da-026)) |
| Claim candidate and consolidation | Candidates; source and fact items; rule view; scientific decisions | Local refs become entity, fact and occurrence keys | `semantic/domain_operations.py`, `semantic/consolidation.py` | implemented ([DA-004](semantic-model-and-authority.md#da-004), [DA-005](semantic-model-and-authority.md#da-005)) |
| Protected staging | `pg_temp.sp_*`, filled from transport rows, then `publish_contract_batch` | Exact receipt bytes | `semantic/publication.py`, `semantic/arrow_publication.py`, `semantic_0027_transport.sql` | implemented ([DA-033](execution-fit.md#da-033)) |
| Physical core `data.*` | Occurrence, fact, support, selection, membership, typed value and role, evidence, assessment, derivation, alternative group, coverage, inputs, exclusions | Scoped by release and realization | `physical.yaml`, frozen revisions, native guards | implemented |
| Served answer | Read kernel; serve queries, journeys and explanation; pack plug-ins; MCP | Snapshot binding, continuation token | `semantic/query.py`, `serve/*`, `cli/query.py`, `domains/*/queries.py` | implemented ([DA-038](served-claims.md#da-038)) |
| Analytical scope and Arrow | Captured and candidate packets, `AnalysisScope`, analytical profile | `projection:<sha>` | `semantic/analytics.py`, `model/semantic/analytics.yaml`, `semantic/arrow_publication.py` | implemented |
| References and evaluation | Reference set, unit, pass, frame and evaluation, distinct from the knowledge `EvaluationResult` | Surrogate ids plus digests; payloads mostly opaque JSON | `model/semantic/reference.yaml`, `eval.*`, `evaluate/semantic*.py` | implemented ([DA-037](served-claims.md#da-037)) |
| Graph validation | Qualified projection with hand-written SHACL; derived OWL/SHACL archived but not read at runtime | — | `semantic/ontology.py` | implemented |

## Concepts

| Concept | Meaning owner | Authorities as found | Status |
|---|---|---|---|
| Statement, statement kind | `core.SourceStatement`, `StatementKind` (a pack may narrow them) | The pack subclass is bound through a raw-YAML scan and the agent range. Native code tests a literal name. Mathematical vocabulary sits in core ([DA-046](semantic-model-and-authority.md#da-046)) | partial |
| Operation binding (statement class, qualification class, role vocabularies, eligibility) | None declared | Regeneration scan, agent range rewrite, Python name lookup; native literals | gap ([DA-026](semantic-model-and-authority.md#da-026)) |
| Qualification, modality | `core.Qualification`, `ClaimModality`, pack subclass | Property `cs:key_role` against predicate `cs:identity_qualifiers` ([DA-001](semantic-model-and-authority.md#da-001)); the catalog copy disagrees ([DA-027](semantic-model-and-authority.md#da-027)); subsets partly inert ([DA-003](semantic-model-and-authority.md#da-003)) | partial |
| Statement role, evidence role | `core` enums | Agent hand copies; native literal vocabulary ids; literal roles in operations ([DA-002](semantic-model-and-authority.md#da-002), [DA-003](semantic-model-and-authority.md#da-003)) | partial |
| Establishment | `core.Establishment` | Physical CHECK; consolidation literals; untyped `ClassMembership`; the boundary admits `derived`, which assembly refuses ([DA-040](structure-and-invariants.md#da-040)) | partial |
| Entity, identity, membership | Pack classes, `unique_keys`, `cs:case`, `cs:scope`, exclusions | `entity_keys` over release, realization and class IRI; legacy `core.keys.normalize_label` for labels; serving uses its own label names ([DA-003](semantic-model-and-authority.md#da-003)) | implemented |
| Entity reference | `agent.yaml` (string) against typed `IdentityEndpoint{kind}` | Two encodings; a local-first fallback at five or more sites ([DA-007](semantic-model-and-authority.md#da-007)) | implemented |
| Value | `core` Value hierarchy | Physical `typed_value.kind` CHECK (17 kinds); writer (10); reader (13); native `value_meaning` ([DA-002](semantic-model-and-authority.md#da-002)) | implemented |
| Fact, occurrence | ADR-0024, §B1 | `semantic/identity.py`, native `fact_identity`, plus a third recipe in `inference.py` ([DA-009](semantic-model-and-authority.md#da-009)); the core record classes are unused ([DA-027](semantic-model-and-authority.md#da-027)) | implemented |
| Scientific equivalence | ADR-0027 (one operation) | Legacy `ValueComparator` (domain path) against `semantic_alignment.equivalent` (evaluation) ([DA-034](semantic-model-and-authority.md#da-034)) | partial |
| Support, selection, assessment, alternative group, inputs, exclusion | Target §2.2 | Physical, transport and native only. Selection status is filter-only ([DA-036](served-claims.md#da-036)); representatives are chosen by ordering ([DA-044](structure-and-invariants.md#da-044)) | implemented, no model owner |
| Derivation, inference rule | Release `inference_rule` rows | `semantic/inference.py`; native seeds with literal eligibility | implemented |
| Coverage | Execution catalog translation; `core.yaml` and `observations.yaml` enums | Producer and consumer vocabularies differ ([DA-035](served-claims.md#da-035)); five restatements ([DA-002](semantic-model-and-authority.md#da-002)) | partial |
| Observation, measurement, task unit | `observations.yaml`, `metrics.yaml`, legacy `core.vocab` | `family`, `outcome`, `stage`, `unit_type` untyped or legacy ([DA-012](structure-and-invariants.md#da-012)) | partial |
| Run and task lifecycle | Catalog lifecycles | Native `ops.execution_edge` VALUES (hand-lowered), physical CHECK, legacy `RunStatus`/`TaskStatus`; no recorded run outcome ([DA-041](structure-and-invariants.md#da-041)) | partial |
| Executable operation inputs | The release archive (`operation/*`, `source-profile/*`) | Runs and plug-ins read the working tree; evaluation reads the archive ([DA-028](semantic-model-and-authority.md#da-028)) | partial |
| Escalation policy | Pack `policies.yaml` (legacy vocabulary, `rulelang`) | Propose chain only ([DA-016](structure-and-invariants.md#da-016)) | partial |
| Method contract | Legacy `core.method` | `semantic.operations.BoundReader` ([DA-045](boundaries-and-composition.md#da-045)) | implemented, legacy-owned |
| Release, realization, project | ADR-0024/0025/0030 | `sem.release`, `data.project` CAS | implemented |
| Release compatibility | None declared | Python exact stack equality in `load_release`; one admitted execution model natively ([DA-049](semantic-model-and-authority.md#da-049)) | gap |
| Pack composition | `regeneration.prepare_packs` | Namespaced operation inputs that no consumer reads ([DA-048](semantic-model-and-authority.md#da-048)) | partial |
| Producer and attribution | Method configuration (`ops.method_config.params.model`) | Not established at execution; evidence names the method ([DA-051](served-claims.md#da-051)); proposal production bound to the name `agent.opus` ([DA-052](boundaries-and-composition.md#da-052)) | partial |
| Reference and evaluation | ADR-0030, `reference.yaml` | Splits diverge ([DA-002](semantic-model-and-authority.md#da-002)); universe conditioned on extraction success ([DA-037](served-claims.md#da-037)) | implemented |
| Source coordinates | Legacy `core.locators` grammar | Native `ops.source_locator_segment` second grammar; two evidence-locator encodings ([DA-014](structure-and-invariants.md#da-014)) | implemented |
| Principals | ADR-0025/0030, `scripts/pg_semantic_roles.sh` | Literal role names; purpose derived by username substitution ([DA-030](native-integrity.md#da-030)) | implemented |

## Translations

| From → to | Owner | Contract state |
|---|---|---|
| Pack and trusted modules → bundle | `regeneration.prepare_packs`, `proposals.proposal_inputs`, `observations.observation_inputs`, `analytics.analytical_inputs` | Binding inferred procedurally ([DA-026](semantic-model-and-authority.md#da-026)) |
| Bundle → prepared release | `prepare.prepare_release` | Owned, with explicit typed diagnostics |
| Release → Pydantic, JSON Schema, OWL/SHACL, registry rows | `prepare.py`, `ontology.build_graph_artifacts` | Derived. Annotations stay raw JSON ([DA-004](semantic-model-and-authority.md#da-004)) |
| Release → `sem.*` rows | `releases._projection_rows`, `publication.native_constraints` | Derived; no binding rows |
| Archive → release | `releases.load_release` | Re-derivation under the current stack ([DA-042](execution-fit.md#da-042)) |
| Physical LinkML → MetaData → DDL | `semantic/metadata.py`; frozen revisions | 0001 derived; later DDL hand-written, equal body for body at head ([DA-031](native-integrity.md#da-031)) |
| Catalog → native guards | Hand-lowered frozen SQL; digest descriptors | No parity check ([DA-027](semantic-model-and-authority.md#da-027), [DA-032](native-integrity.md#da-032)) |
| Unit result → source report | `observations.bind_result` | Legacy type edge ([DA-012](structure-and-invariants.md#da-012)) |
| Agent authored → stored → candidates → rows → staging | `proposals.locate_proposal`, `domain_operations._project_cut`, `consolidation.assemble` | Inline and procedural over dicts ([DA-005](semantic-model-and-authority.md#da-005)) |
| Candidates → rule view | `ReleasedRulesPolicy` with legacy view types | Lossy ([DA-005](semantic-model-and-authority.md#da-005)) |
| Source coverage → semantic coverage | `outcomes.PreparedCoverageLowerer` | Owned, through the catalog |
| Task protocol → coverage | inline in `domain_operations` | Prose reasons ([DA-013](structure-and-invariants.md#da-013)) |
| `data.*` → Arrow | `analytics.compile_projection` | Contract checked for id and lifetime |
| `data.*` → served rows | `query.ReadSession`, `serve.read.Reader` | Bound to the archived release; plug-in code live ([DA-028](semantic-model-and-authority.md#da-028)); paged kernel route bypassed ([DA-038](served-claims.md#da-038)); explanation outside the pinned journey ([DA-050](served-claims.md#da-050)) |
| Prediction + reference → grade | `evaluate/semantic.reference_evaluate` | Owned, with an evaluator-specific prediction translation ([DA-005](semantic-model-and-authority.md#da-005), [DA-037](served-claims.md#da-037)) |

## Strengths to keep

These bound later remedies.
- **Preparation.** Pure, explicit-input release preparation that refuses unsupported constructs
  and annotations with typed diagnostics (invalid, unsupported, unresolved, unchecked).
- **Releases.** Immutable, byte-exact releases keyed by resolved vocabulary snapshots. Dynamic
  definitions are registry rows over fixed tables, with no per-class DDL.
- **Identity.** Occurrence and fact identities are separate, and `fact_key` refuses evidence,
  confidence or supports inside a qualification. Native code recomputes every identity instead of
  trusting the caller (ADR-0025).
- **Category roles done right.** `enum_members(subset=)` resolves inherited member properties from
  the archive. `claim_bearing` and `premise_forming` are consumed this way.
- **Strict boundary models.** Frozen models with `extra=forbid`, strict validation, and no inf/NaN
  on generated models.
- **Protected staging.** Definer-owned transaction-local relations with verified ownership and
  shape, column-level writer INSERT, and a pinned `search_path`. All 53 SECURITY DEFINER functions
  are owned by the NOLOGIN publisher and none is executable by PUBLIC (probe, 2026-10-29).
- **Native run and task state machines.** Attempts, leases, holder fencing, `SKIP LOCKED` claims,
  replay-safe completion and an immutable held first result. They are bound to the execution model
  through `native_guards`.
- **Descriptor attestation.** Body, ABI, owner, configuration, ACL and triggers are attested at
  activation. Activation is a parent-plus-generation CAS, and a completed realization row is
  immutable.
- **Exact numerics.** Decimal lexicals are retained, canonical meaning is computed separately,
  `compare_decimal` compares strings, and Unicode 16 casefold parity is checked at deployment. The
  differential value-meaning vectors are an independent oracle.
- **Snapshot discipline in serving.** A read-only REPEATABLE READ snapshot; strict continuation
  tokens bound to release, realization, revision, projection and parameters; a conservative
  `unknown` default; a batched keyset read path.
- **References.** Immutable bytes with digests, versioned frames that refuse ambiguous relocation,
  a release-equality gate, a separate evaluator principal, policy read from the archive, and
  undecided mathematical outcomes kept.
- **Provider isolation for automated extraction.** Process group with kill on timeout, a stripped
  environment, strict MCP configuration and no tools.

<a id="current-model"></a>

## Current engagement model — 2026-11-01

**Implemented, source-inspected at `1cb8e620`, with verification limits in the audit README.**
The preceding diagram is the October 29 account. Current release opening uses archived products;
execution binding is mandatory (`contracts.py:713`), result dimensions are validated
(`operation_results.py:61`), and native task/run guards consume release-projected transitions
(`semantic/sql/execution_guards.sql:1–96`). `analytics.py:498–507,637–700` derives Arrow fields
from shared physical metadata; `pdf_payloads.py:45–90,230–347` preserves supplied fields and
numeric variants in schema-derived IPC. `ontology.py:496–770` provides qualified graph closure
and separate conformance execution. These mechanisms are preservation constraints for the review.
CLI pack-query loading remains a live-file boundary (DA-028). This model update does not
certify all native guards, deployments, providers or consumers.
