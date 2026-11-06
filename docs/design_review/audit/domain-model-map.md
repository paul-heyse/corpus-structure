# Current domain model map

**Implemented source inspected, 2026-11-05.** [Baseline and limits](README.md#baseline).
This diagnostic map describes the model found in source; architectural owners retain authority.
Paths below omit `python/corpus-structure/src/corpus_structure/` unless stated otherwise.

<a id="current-model"></a>

## Meaning, behavior and realization

| Context | Authoritative distinctions and executing realization | Limit |
|---|---|---|
| Semantic definitions | LinkML definitions and induced slots feed prepared types, property roles, vocabulary subsets and reference positions; `semantic/prepare.py:585–814`, `types.py:313–385` | Multiple representations remain legitimate; complete translation fidelity is not inferred from matching shapes. |
| Qualified relationships | `model/semantic/contracts.yaml:355–416,878–979` declares endpoints, roles, direction, cardinality/identity scope, qualifications and references; `semantic/contracts.py:1279–1542` validates composition | Not every graph projection or invariant body was independently matched. |
| Actions | OperationContract (`contracts.yaml:648–720`) binds inputs, results, applicability, dependencies, effects, outcomes and transitions; compiled implementation and generated/native call bindings consume these | Application domain functions legitimately realize algorithms. No general model interpreter is required. |
| States and transitions | Lifecycle/transition declarations (`contracts.yaml:417–535`) and populated execution-model inputs govern finite transitions; native guards enforce task/attempt/holder and terminal publication | A state name alone is insufficient evidence; actual guards were inspected, not executed. |
| Policy and invariants | Compiled failure bindings plus actual native guard identities; typed SemanticReason (`semantic/refusals.py:26–83`); executable policy applicability | DA-027 remains bounded assurance scope, not evidence that declarations are decorative. |
| Identity and representation | Layered occurrence/fact identities, explicit provisional identity decisions and qualified runtime folding (`domain_operations.py:1219–1313`; `unicode_identity.py:99–160`) | No universal historical-runtime support promise; ordinary visibility of every decision was not exhaustively examined. |
| Progressive contribution | `observations.yaml:173–260` separates operation population, contribution semantics, endpoints, field/score state and private standing; `contributions.py:47–189` governs bindings, source pieces, identity and endpoint closure | Generic retained roles are not automatically admitted knowledge semantics; see the question below. |
| Local interpretation and admission | Source quotation/occurrence and independently adjudicated contextual denotation have separate policy owners (`local_admission.py`, `local_semantic_admission.py`) | Source location, meaning, canonical identity and scientific support remain separate claims. |
| Structural products | Definition applicability, comparison and dossier contracts retain original source custody, participant roles and declared selection; `sql/structural_publication.sql:77–207` revalidates actual eligible effects | Lexical agreement is not equivalence; dossier membership is not full-source completeness. |
| Publication and recovery | Shared immutable batches, SERIALIZABLE settlement, exact receipt recovery, attempt fencing and runtime bindings (`publication.py:755–941`; `sql/runtime_bindings.sql:2–100`) | Source inspection does not attest current deployed roles or replay behavior. |
| Serving and assessment | QueryRow standing, bounded evidence/coverage/explanation/walks, source-first/output-first frozen cases and explicit population completeness | The inspected test expectations are independent examples, not executed qualification or a universal oracle. |

The model therefore covers consequential relationships, possible actions and states as well as
objects. Its authority is distributed among released declarations, compilation, coherent domain
functions and native enforcement. An assessment must follow the applicable contract and scope;
rich schemas alone do not establish model adequacy.

## Representative journeys and credible changes

Source → contribution → local interpretation → optional admission was traced independently of
complete record assembly. Operation inventory includes empty/failed questions, and a local
contribution can survive later failure. Serving and evaluation keep retrieval population,
assessment population, source coverage and scientific quality distinct.

Operation → admitted execution → claim custody → terminal settlement was traced through native
projection and Python execution. Only the current method's batch is claimed; renewal includes
preparation and settlement. Task identity, twin selection and native reuse share one dependency
projection. These correct DA-053/054 without establishing optimal execution fit.

A renamed display property or released role now reaches consumers through effective bindings
rather than the cited name sets. A runtime/budget repair can retain semantic release identity
while carrying an exact executable runtime binding. Archived reads retain producing provenance;
current operational repair does not retag old results.

### Generic contribution roles: bounded adequacy question

`ContributionEndpoint.role` and contribution disposition are open strings; `contributions.py`
checks identity, local endpoint closure and minimal relation/composite structure. This is a
weaker generic contract than a domain-specific relationship definition. Whether a particular
new role requires stronger declarations depends on the semantic claim its consumers make.
Free strings alone do not establish a violation. Existing semantic consumers and their guards
must be examined before treating this as merely opaque transport or as ungoverned meaning.
The independent challenge inspected current consumers: `methods/contribution_adapter.py:725–915`
owns table/definition attachment vocabulary, eligible grouping, anchored primary, allowed roles
and source/geometry constraints; `evaluate/operation_assessment.py:230–292` compares frozen roles
and anchors without repairing misspellings. `semantic/sql/source_contributions.sql:450–492`
binds contextual denotation to an actual retained selected decision, statement and dependencies;
`semantic/sql/record_publication.sql:891–940` additionally requires the exact question/version,
rubric/context and independent supported case. `serve/contributions.py:68–100` distinguishes
private interpretation from admitted witnesses. The generic envelope is sufficient for private
retention under these inspected narrower owners. Complete semantics for arbitrary future
contribution vocabularies were not established; no new DA identity is assigned to that limit.

## Library inquiry and capability boundaries

All 15 guides under [data_model](../../libraries/data_model) were oriented by capability and
semantic limits, followed by targeted source inspection. Dependency presence is distinct from
feature adoption. The pinned product manifest is `python/corpus-structure/pyproject.toml`.

| Guides | Current relevance and bounded conclusion |
|---|---|
| LinkML; extension libraries | Direct LinkML/runtime1.12.1 and term-validator0.4.5. Effective induced definitions and generated boundaries are used. Actual operation/lifecycle enforcement is application/native realization, not implicit LinkML behavior. |
| Pydantic; JSON Schema | Direct2.14.1/4.26.0. Typed boundaries use strict/frozen/extra-forbid construction (`semantic/boundary.py:244–269`). Conditional rules use native JSON Schema fragments with explicit unsupported-field refusal (`conditional_rules.py:56–126,168–220`); native lowering separately owns persisted enforcement. |
| pydantic-settings | Direct2.16.1. Configuration source/default semantics are a boundary; they do not supply independent domain-policy authority. No new settings defect established. |
| RDFLib; pySHACL | Direct7.6.0/0.40.1. `ontology.py:723–742` explicitly selects conformance-only behavior: no inference, advanced rules, imports or mutation, and separates invalid shapes from runtime failure. Conformance is not external truth. |
| PyOxigraph; Oxrdflib | PyOxigraph0.5.13 is transitive; Oxrdflib absent. Backend capability does not establish application adoption, relationship preservation or transactional substitution. No new store selected. |
| valuesets; OAK | Direct0.4.2/0.7.4. `ontology.py` acquires explicit local snapshots and prepares vocabulary membership/meaning. Lexical matching, ontology entailment and equivalence remain different judgments. |
| linkml-map; linkml-datalog | Absent dependencies. Useful lenses for preservation versus derivation, asserted versus inferred facts and rule provenance; absence alone is not a diagnosis or adoption obligation. |
| schema-automator | Absent. Inferred keys, enums, cardinalities and relationships are hypotheses about observed data, not complete permitted-domain authority. |
| msgspec/attrs/cattrs | cattrs26.2.1 direct, attrs26.1.0 transitive, msgspec absent. Conversion/structuring is distinct from semantic interpretation and invariant enforcement; no concrete new loss established. |

Context7 lookup on 2026-11-05 used official LinkML SchemaView/generator documentation and
pySHACL validation/rules documentation. Current online generator examples include behavior
beyond the pinned version; no such feature was assumed available or required. Local addenda
also include newer pySHACL/Pydantic material. Exact source and actual settings govern conclusions.
Primary references: [LinkML SchemaView](https://linkml.io/linkml/developers/schemaview.html),
[LinkML conditional rules](https://linkml.io/linkml/howtos/skip-logic.html),
[pySHACL](https://github.com/RDFLib/pySHACL).

## Workload and assurance limits

Prepared indexes, cached adapters/archives, shared owned reads and bounded result inventories are
preservation strengths. Cumulative native assurance protects real trust and consistency premises;
DA-033 retains the unresolved avoidability question. No benchmark, numerical improvement,
complete non-statistics transfer result or whole-corpus semantic quality is inferred.
