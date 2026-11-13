# Owned operation and immediate consumer reconciliation

**Interface-checked / Assessed, 2026-11-12.** This closes the bounded DDO-00 inventory inquiry,
not adapter migration or universal Python behavioral analysis. [V2](raw/inventory-v2.json)
retains exact source hashes, all 101 declared protocol operations and their implementation/call
metadata, 34 phase0 and 17 M1 registry entries, inherited identity/configuration/dispatch owners,
all three local pack configurations, six descriptor construction sites and both source-dependency
keys. There are no unresolved entries in either acquired registry root. The original partial
[record](records/ddo.operation-inventory.json) and its outputs remain unchanged.

The acquisition universe is the two supported repository registry roots, repository pack
configurations, released execution catalog, explicit descriptor constructors and the distinct
interpretation-authoring entry point. Unconfigured external plugins are not silently asserted
present or absent. Registry clones used during characterization retain their selected root;
they do not create new semantic authoring authorities. Lexical method candidates remain diagnostic
evidence, not the supported-operation population or a replacement production registry.

## Immediate publication and read consumers

Paths below name actual source owners. The V2 effective entries preserve the exact implementation
and inherited dispatch per family; a common caller is listed once rather than copied for every
method. DDO-07/08 replaces these callers and their selected implementations together. The DDO-00
inventory does not imply that current methods have been admitted by the new compiler.

| Population / entry point | Actual immediate consumers and effects | Migration disposition |
|---|---|---|
| [phase0 registry](../../../../python/corpus-structure/src/corpus_structure/orchestrate/phase0.py) and [M1 registry](../../../../python/corpus-structure/src/corpus_structure/orchestrate/m1.py), including inherited methods | [run_source_methods](../../../../python/corpus-structure/src/corpus_structure/orchestrate/semantic.py) resolves configurations, claims source work and invokes selected `select` / `input_digest` / `run` or `plan`; [ready coordination](../../../../python/corpus-structure/src/corpus_structure/orchestrate/ready.py) owns ready execution / resource close. [operations](../../../../python/corpus-structure/src/corpus_structure/semantic/operations.py) owns `prepare_unit_completion`, `complete_unit_result`, immutable source/result custody and `BoundReader`. | DDO-07 capture/primary and DDO-08 downstream adapters; DDO-03 ports and DDO-04 native publication are prerequisites. Retire manual method/config/dependency authority with these consumers. |
| Six direct descriptors, expanded below | [PM2 stage preparation](../../../../python/corpus-structure/src/corpus_structure/orchestrate/pm2_stage.py), `queue_agent`, [native source requests](../../../../python/corpus-structure/src/corpus_structure/semantic/native_requests.py) and [visual requests](../../../../python/corpus-structure/src/corpus_structure/semantic/visual_requests.py) construct ordinary source tasks/configurations and retain exact request/source/profile pins. They flow through existing protected task/publication boundaries. | DDO-07/08 declares each selected operation/capability; DDO-05/06 replaces request scheduling/recovery. No private descriptor exception remains after adoption. |
| [author_interpretations](../../../../python/corpus-structure/src/corpus_structure/serve/interpretation_authoring.py), called by [CLI interpretations](../../../../python/corpus-structure/src/corpus_structure/cli/interpretations.py) | Its finite `kind` mapping selects `TerminologyInterpretationMethod`, `MeasurementInterpretationMethod` or `AuthorSourceRecordsMethod` (all already in phase0), constructs a per-call registry/config, invokes `run_source_methods`, then `seal_cut` and [consolidate_cut](../../../../python/corpus-structure/src/corpus_structure/semantic/domain_operations.py). It returns an unselected private review result, never activates a default. | DDO-08 retains explicit authored selection and exact source/field custody; DDO-09 modeled consolidation; DDO-10 CLI/reads. This distinct entry point must migrate even though its classes overlap phase0. |
| All 101 catalog protocol operations | Each inventory entry retains the actual `implementation.owner`, `symbol`, `placement`, inputs/results/effects/capabilities and authored call metadata. [generated call bindings](../../../../python/corpus-structure/src/corpus_structure/semantic/operation_call_generation.py), [execution contracts](../../../../python/corpus-structure/src/corpus_structure/semantic/contracts.py) and [native operations](../../../../python/corpus-structure/src/corpus_structure/semantic/operations.py) consume that catalog. | DDO-01–04 extends the shared compiler/native authority; DDO-07/08 replaces affected production adapters. Existing code ownership does not prove a supported target implementation or complete inferred call graph. |
| Published private contributions and materialized results | [contributions](../../../../python/corpus-structure/src/corpus_structure/serve/contributions.py) reads and exports exact selected contribution populations; [review bundles](../../../../python/corpus-structure/src/corpus_structure/serve/review_bundle.py) captures and verifies retained source/schema/support closure; [domain operations](../../../../python/corpus-structure/src/corpus_structure/semantic/domain_operations.py) performs public consolidation under policy. | DDO-09 currentness/consolidation and DDO-10 pinned serving/export/evaluation; DDO-11 preserves original sealed interpretation and source/reference custody. Do not treat a dependency as active analysis or a private retained result as accepted knowledge. |

## Six descriptor identity owners

Runtime-selected values below are explicitly selected by the named typed owner. Capturing their
AST spelling alone would not resolve their meaning; no attempt is made to execute them during
metadata acquisition.

| Site | Identity / finite selector owner |
|---|---|
| `pm2_stage._work` | `extract.pm2_{provider}` over `PARSER_QUESTIONS` in [pm2_products](../../../../python/corpus-structure/src/corpus_structure/methods/pm2_products.py): HanLP, Maverick, DiPO. `ParserScope.operation_version` selects version1/2 from the selected parser/layout profile; config class is `ParserProfile` or `HanlpSeamProfile`. Source extent, canonical token map and startup/profile remain exact. |
| `pm2_stage._interpretation_work` | `extract.pm2_d1`, version from the typed `InterpretationScope.version`, `InterpretationProfile`; selected released family/question and supplied candidates determine the request. Runtime-selected scope is owned by that frozen typed scope, never guessed from a producer timestamp. |
| `pm2_stage._classification_work` | Method/version from [pm2_gliner_classification](../../../../python/corpus-structure/src/corpus_structure/methods/pm2_gliner_classification.py) constants, `ClassificationProfile`. Selected family/question, mapping and released inference policy feed the exact request. |
| `orchestrate.semantic.queue_agent` | `producer_binding(method_name, configuration)` in [LLM producer](../../../../python/corpus-structure/src/corpus_structure/methods/llm/producer.py) owns method/version/execution-kind/unit. It validates requested unit and frozen configuration; `AgentOpusConfig` is the config contract. This runtime selection remains explicit; no invented finite external-producer list. |
| `native_requests.request_source_view` | `native.source_request`, version6 and document unit for archived-cut rendering, otherwise version5 and source-view unit; `NativeRequestConfig`. The explicit archived-cut/source request branch owns this choice. |
| `visual_requests._METHOD` | Fixed `native.source_request/5`, deterministic document unit and `VisualRequestConfig`. Visual selection and exact product pins are input scope, not an implicit method identity. |

`source_dependencies` and `source_dependency_method` jointly choose actual upstream producer edges
in `orchestrate.semantic`; both keys are now inventoried. `getattr(..., "plan")` and
`getattr(..., "close")` are explicit capability dispatch consumers to replace with DDO-03/08
typed capabilities. They are not independent model authorities merely because Python dispatch
currently performs the lookup.

**Assessment:** the owned metadata inventory and immediate migration dispositions are complete
within the stated acquisition universe. Actual contracts, closed source profiles, generated
ports, native admission and adapter removal retain their own package acceptance. No provider,
database write, protected answer or runtime method invocation was needed for this inventory.
