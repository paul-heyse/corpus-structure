# Declared data operations — operations and sequencing baseline

Supporting document for the
[declared data operations review](../design_review_declared-data-operations_2026-11-12.md),
which owns the findings and every remedy. This page records how operations are defined, wired
and ordered at product source `8c0f4f951`.

**Evidence.** Interface-checked by source inspection, 2026-11-12, through a delegated read-only
mapping. The review's author re-read the `Method` protocol, `OperationContract`, the
`convert_pdf` contract, the characterization inputs map and the task hash construction. The
rest was not re-read. Items marked *inferred* were not confirmed by the mapping either.
Nothing was run.

**Path convention.** Paths without a prefix are relative to
`python/corpus-structure/src/corpus_structure/`.


**Audit reconciliation2026-11-12.** This remains an implementation/authority baseline,
not the target specification. The [corrected target](target-contracts-and-storage.md) and
[principal §§4–11](../design_review_declared-data-operations_2026-11-12.md#4-corrected-target-state)
supersede original proposed mechanisms; the [companion](../audits/design_review_declared-data-operations_2026-11-12_audit.md)
records every recommendation disposition. Original dated counts and unrefreshed observations
remain historical, not new execution evidence.


## Layout

All pipeline code is Python. `crates/corpus-structure/src/lib.rs` is a placeholder.

| Package | What it holds |
|---|---|
| `semantic/` | Release and execution contracts, storage, publication |
| `methods/` | Processing methods and model-provider adapters |
| `orchestrate/` | Run sequencing |
| `core/` | `Method` protocol, vocabularies, the ready-work driver |
| `ingest/` | PDF and sentence ingestion |
| `evaluate/`, `serve/`, `intervene/`, `cli/`, `schema/` | Evaluation, read side, MCP server, the `ci` command, schema tooling |

Declared contracts live in `model/semantic/*.yaml`, mainly `execution-model.yaml`. SQL kernels
live in `semantic/sql/`. Legacy service definitions remain under `services/`; ADR-0091 selects one root Python3.14 GPU host for the current learned NLP providers. Domain
packs under `domains/` hold `methods.yaml` and policies.

## Operation inventory

### Registered methods

Registries: `orchestrate/phase0.py:121-157` and `orchestrate/m1.py:161-182`.

| Method | Module | Unit | Consumes → produces | Wraps |
|---|---|---|---|---|
| `ingest.pdf` | `ingest/pdf_methods.py:102` | document | Original PDF → native PDF records and source views | Docling, pypdfium2 |
| `ingest.pdf_integrated` | `ingest/pdf_recognition_methods.py:169` | document | Native product → integrated recognition and source views | Nemotron-parse service, Chandra |
| `enrich.pdf_math` | `ingest/pdf_methods.py:655` | document | Native PDF and source view → enriched versions | Docling formula enrichment |
| `segment.sentences` | `ingest/methods.py:44` | source view | Source view → sentence observations | spaCy |
| `profile.segments` | `ingest/methods.py:73` | source view | Source view → measurements | — |
| `extract.math`, `normalize.formula`, `resolve.symbol_scope` | `methods/math/methods.py:132-205` | source view | Source view → math reports | lark, sympy, spaCy |
| `text.native_evidence` | `methods/native_evidence.py:297` | document | Source views → characterization layer | spaCy, optional HanLP |
| `text.formal_evidence` | `methods/formal_evidence.py:77` | document | Source views → layer | lark |
| `text.constructions` | `methods/construction_characterization.py:98` | document | Native and formal layers → layer | spaCy |
| `text.contextual_characterization` | `methods/contextual_characterization.py:339` | document | Prior layers → layer | Maverick, DiPO |
| `text.model_characterization` | `methods/model_characterization.py:164` | document | Prior layers → layer | PM2 d1, GLiNER |
| `text.evaluate_context` | `methods/contextual_interpretation.py:91` | document | Constructions and contextual and model layers → layer | — |
| `text.compose_view` | `methods/characterization.py:72` | document | Layer set → enriched document view | — |
| `structure.compare`, `.dossier`, `.condition_qualification` | `methods/structural_products.py:1322/1437/1676` | run | Retained contributions → structural product | lark |
| `structure.scoped_relations` | `methods/scoped_relations.py:1584` | source view | Source view → contributions | lark, spaCy |
| `structure.artifact_identity` | `methods/artifact_identity.py:442` | run | Contributions → identity product | splink, duckdb, rapidfuzz |
| `structure.definition_components`, `.definitions`, `.definition_declaration_components`, `.clause_classification` | `methods/definition_applicability.py:892/1362`, `methods/definition_declaration.py:68`, `methods/clause_classification.py:313` | run | Sources and components → definition products | GLiNER2 |
| `locate.definition_terms`, `interpret.terminology`, `.measurement`, `.source_records` | `methods/definition_terms.py:55`, `methods/interpretations.py:51/123/136` | source view | — | — |
| `retrieve.contextual` | `methods/contextual_candidates.py:723` | source view | Source view → candidate lists | sentence-transformers, pgvector |
| `extract.m1_annotations`, `extract.m1_candidates`, `resolve.m1_readings` | `methods/m1_annotations.py:81`, `methods/m1_source.py:304`, `methods/m1_readings.py:130` | source view | — | spaCy, GLiNER2 |
| `agent.opus`, `agent.general` | `methods/llm/agent_opus.py:93/134` | source view | Packet → task awaiting an external agent | Agent through MCP |
| `consolidate.claims`, `validate.rules` | `orchestrate/domain_methods.py:61/91` | run | Descriptor only; `consolidate_cut` does the work | — |

### Operations outside the `Method` protocol

| Operation | Where | Note |
|---|---|---|
| PM2 parsers `extract.pm2_{hanlp,maverick,dipo}` | `orchestrate/pm2_stage.py:410`, `run_parsers` at `:747` | Tasks created directly with the stage hard-coded |
| `extract.pm2_d1`, `extract.pm2_gliner_classification` | `orchestrate/pm2_stage.py:632/674` | |
| `native.source_request` | `semantic/native_requests.py:370` | Render and archive requests |
| Visual evidence requests | `semantic/visual_requests.py:129` | Reuses the name `native.source_request` with a different configuration class |
| Agent queueing | `orchestrate/semantic.py:1597` | |
| PDF private build | `orchestrate/pdf_streaming.py` | Its own state machine, entered from inside `ingest.pdf` |
| Finalize and consolidation | `orchestrate/commands.py:295` → `semantic/domain_operations.py:2334` | Fixed call order |
| Release build | `semantic/prepare.py:544`, `semantic/releases.py:385/611` | |

## Operation and contract abstractions

**`Method[C]`** (`core/method.py:981-1011`) declares name, version, family, unit type, tier,
`Config`, resources, and `select`, `input_digest` and `run`. It declares no input or output
object types. Optional `plan`, `original_recipe` and `close` are found with `getattr`
(`orchestrate/semantic.py:198, 1403`).

**`OperationContract`** (`semantic/contracts.py:694-716`) carries id, inputs, results,
applicability, universe, effects, outcomes, outcome domain, dependencies, precision,
implementation, transitions, projections and result dimensions. It is compiled from
`execution-model.yaml` and bound to each release.

- 101 contracts, all with an implementation; 74 with applicability; 16 with transitions.
- `dependencies` is never an operation-to-operation edge. It is one of two fixed lists of
  identity inputs such as `semantic_release`, `execution_model`, `input_binding`,
  `implementation_version`.
- `inputs` and `results` are used for compile-time reference checks
  (`semantic/contracts.py:1691-1723`) and explanation. Nothing schedules from them.
- Language and extraction methods appear only as 148 result-dimension entries under
  `configure_method`.

**`explain_operation`** (`semantic/operation_reporting.py:162`) reports every applicability
invariant as unresolved with the reason "No qualified live evaluator" (`:193-202`).
`inspect_contract` (`semantic/contract_inspection.py:20`) validates class and property inputs
and delegates operations to `explain_operation`.

**Provider layer.** `NativeHost`, `NativeProfile` and `ProviderExecution` carry frozen
identities per provider. Dispatch is by string comparison on the provider name
(`methods/native_host_adapters.py:27-56`, `methods/characterization_resources.py:450-750`).

## Sequencing and eligibility

1. **`Graph` and `Step`** (`orchestrate/runner.py:49-68`). `Step.upstream` is read by two tests
   and by no production code. Order is iteration over stages and steps
   (`orchestrate/semantic.py:663-664`). Adjacent pairs run together when their names match a
   hard-coded pair (`:1835-1865`).
2. **Task prerequisites from configuration.** A `Config` declares `source_dependencies` as one
   of three literals. `orchestrate/semantic.py:806-910` branches on them, and
   `register_ready_dependencies` (`:1236-1300`) writes `ops.task_dependency` rows after the
   parents settle. A database check limits the edge kind to the same three values.
3. **Database eligibility.** `ops.claim_tasks` (`semantic/sql/execution_projection.sql:72-88`)
   claims a pending task, or a running one with an expired lease, when no prerequisite is
   outside done, empty or reused. `SourceClaimFrontier.admit` (`orchestrate/ready.py:90-121`)
   admits by capacity and special-cases `text.compose_view`.
4. **Characterization.** Stage order is a literal sequence
   (`orchestrate/characterization.py:527-623`) with a hand-maintained inputs map (`:357-379`)
   and per-method parameter cases (`:401-430`). Each stage call creates a one-stage run.
5. **Analysis demands** declare prerequisites in the model (`execution-model.yaml:14729`), and
   `semantic/analysis_contracts.py:275-290` checks them against a second, hard-coded table.

The retained task graph snapshots under the BEP/TC evidence folder hold no dependency edges for
the book demand, because characterization order is carried by separate runs. Their helper
notes that a missing edge is not proof of independence.

## Coupling hot spots

- **Method-name literals.** In package Python, for example `retrieve.contextual` in 7 files and
  `text.native_evidence` in 7. In live SQL, `retrieve.contextual` with a pinned operation
  version (`semantic/sql/source_contributions.sql:1812`) and
  `structure.definition_components/10` (`semantic/sql/structural_products.sql:1589/1706`).
- **Hand-maintained method sets.** `PRIMARY_PRODUCERS` (`orchestrate/characterization.py:28`),
  the library-to-method map (`orchestrate/semantic.py:470-514`), graph edits by name
  (`orchestrate/source_operation.py:120-134`), provider selection per method
  (`methods/characterization_resources.py:1151-1290`).
- **Parallel lists.** Adding a method means a class and a registry tuple, `methods.yaml`
  configurations, result-dimension entries in the execution model, effect support entries where
  it has a contract, and often SQL kernels.
- **Duplicated vocabularies.** Stage, task status, unit type, family and tier in
  `core/vocab.py` repeat domains in the execution model and SQL checks.
- **Tests that restate order.** 28 test files reference graphs, stages or method tuples, with
  71 inline `Graph` or `Step` constructions.

## Pieces to generalize

| Existing piece | What it already supplies |
|---|---|
| `OperationContract`, `ImplementationBinding`, lifecycles and the compile-time checker | Typed input and result concepts, applicability, release binding |
| `Method` and `MethodRegistry` | A uniform adapter shape and configuration resolution |
| `ops.task`, `ops.claim_tasks` | A database queue with readiness, leases and attempt fences |
| Characterization layer dependencies and product pins | A product-level dependency closure |
| `AnalysisDemand` prerequisites | A small declared dependency structure compiled from the model |
| `core/work.py` | A driver for ready work under capacity limits, independent of how order is decided |
| Generated database-call layer (`semantic/_operation_calls.py`) | A precedent for generating typed ports from declarations |
