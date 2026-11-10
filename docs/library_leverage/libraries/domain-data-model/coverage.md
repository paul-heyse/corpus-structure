# Complete overview coverage and discovery routing

**Read coverage recorded 2026-11-10.** Three researchers read every line of the nine supplied
documents during planning, including sources, corrections and advanced addenda. Execution reused
those unchanged documents and deepened selected current consumers and installed contracts.
This establishes reading coverage, not uniform applicability or runtime qualification.

The tables group consecutive substantive sections without dropping lower-priority territory.
Each route names its research interpretation. **Adopted** means current source realizes a
capability; **underuse candidate** means a concrete broader use deserves investigation;
**conditional** means a consumer or supported contract is still missing. These are discovery
judgments with Proposed benefits, not defect dispositions. Main and addendum section numbering
are separate. Source line ranges refer to the inspected revision in the [baseline](briefing.md).

## Semantic declarations, ontology and vocabulary sources

| Source and complete territory | Route and interpretation |
| --- | --- |
| [LinkML](../../../libraries/data_model/linkml.md), 1–3127; main §§1–3: architecture, primitives, inheritance/induction, identity, embedding/references, mappings, dynamic enums, rules, arrays | DDM-01/02/05: substantial schema adoption, conditional richer relationships/values; identity remains model owned |
| Main §§4–5: validation plugins, normalization/inference, Python/runtime forms, SchemaView/Builder, modular imports, lint and metadata | DDM-01/03/11: native preparation already adopted; helper equivalence and reuse need bounded contracts |
| Main §§6–8: documentation/API/language/graph generators, conversion, flattening, relational intermediate model, SQLAlchemy/storage, profiles | Semantic-declarations wider territory; code/docs interop conditional on real consumers; existing derived Core/native route retained |
| Main §§9–12: Map, Term Validator/OAK, Automator, Schemasheets, Store, extraction/ETL, instance-to-OWL, releases/limits/sources | DDM-05/06 and semantic-declarations stopping conditions; companion presence is not adoption; prior Map/Datalog limits retained |
| Addendum §§1–5: logical relationships/disjointness, attributed edges, measurements, presence/collections/extras, enum composition/bindings | DDM-02/05/12: useful semantic territory, much outside current admitted profile; source and enforcement changes must compose |
| Addendum §§6–9: Rust/PyO3, YARRRML, effective models/imports, aliases/prefixes/subsets/deprecation | DDM-01; cross-language/export features conditional; source-relative names and closed imports preserved |
| Addendum §§10–12: specialized generators, Datalog, grammars, JS runtime, renderer/scaffolding and synthesis | Semantic-declarations wider territory; conditional workflow consumers, no general runtime selected |
| [OAK](../../../libraries/data_model/oaklib.md), 1–804; §§1–5: architecture/adapters, Semantic-SQL, metadata/identity, search/term expressions, graph/native OWL | DDM-05/06/11; local adapters adopted, search/entailment/native OWL distinct; SQLite route is not PostgreSQL authority |
| §§6–9: mapping normalization, lexmatch/grounding, associations/enrichment, classical similarity/Semsimian | DDM-06: candidate formation conditional; mapping kinds and information-content premises retained |
| §§10–13: validation, KGCL diff/merge, subset/conversion/visualization, taxon/usages/statistics/annotated RDF/SKOS | DDM-06: update-impact research conditional; domain-specific enrichment and visualization lack selected consumers |
| §§14–16: plugins/companions, LLM assistance, operational/version limits and synthesis | Vocabulary stopping conditions; installed adapter capabilities must be checked, rolling embedding docs do not establish 0.7.4 APIs |
| [Valuesets](../../../libraries/data_model/valuesets.md), 1–1093; main §§1–4: catalog/model, source composition, RichEnum metadata/identity | DDM-05: selected source imports promising; ordinary production use not established by test support |
| Main §§5–8: numeric classifier, dynamic materialization, mappings/SSSOM/evaluator, generators/slots/sync | DDM-05/12: classification may overlap; mappings are not identity; dynamic Python generation loses source semantics |
| Main §§9–12: governance, performance/fidelity, source map/synthesis | DDM-05/06: draft suitability and maintained public API are research premises |
| Addendum §§1–5: PV hierarchy/composition, query descriptions, Python generation, slots/mixins/cardinality heuristics | DDM-05: richer source metadata useful conditionally, unsupported PV inheritance/profile must be addressed |
| Addendum §§6–11: reports, reconciliation, maintenance, quantities/units, hierarchy/OWL, eager imports/MCP/distribution | DDM-06/12 and vocabulary wider territory; selective imports preferred for investigation, no automated sync/OWL publication selected |

## Executable models, representations and process acquisition

| Source and complete territory | Route and interpretation |
| --- | --- |
| [Pydantic](../../../libraries/data_model/pydantic.md), 1–1210: schema model/surfaces, constraints/presence, unions/recursion, validation/errors | DDM-03/13/14: substantial generated adoption; recipe and nested composition are concrete underuse candidates |
| Same original reference: serialization/schema, aliases/configuration, core/plugin extension, partial JSON, execution/ecosystem/version limits/sources | DDM-04/09 and boundary wider territory; directional fidelity and retained native ownership constrain reuse |
| Addendum 1211–2438: version/security, extras/lazy/tolerant contracts, polymorphism, serialization, encoded/secrets/import/domain types | DDM-03/04; provisional acceptance cannot stand in for complete admission; 2.14.2 facts separate from 2.14.1 |
| Same addendum: advanced schema, regex/ASCII/alias/temporal/binary policy, lifecycle/equality, callable/dataclass validation, diagnostics/privacy/core operations | DDM-03/09/13 and conditional extensions; use high-level composition before custom core machinery |
| [pydantic-settings](../../../libraries/data_model/pydantic-settings.md), 1–1133: models, precedence/merge, env parsing, dotenv/files/secrets/cloud, CLI | DDM-10: snapshots and two sources adopted; additional providers/CLI conditional on operator need |
| Same original reference: custom source/state, cache/reload/async, diagnostics/provenance, compatibility/synthesis/sources | DDM-10: source explanation conditional; cache lifecycle already supplied at entry points |
| Addendum 1134–1997: eager source execution, nested defaults, instance policy, provider versions/failures, CLI composition | DDM-10: precedence is not lazy effects; source-specific introspection requires correct instance context |
| Same addendum: unresolved source diagnostics, dotenv/Windows, nested secrets, project TOML and synthesis | DDM-10 conditional platform/provider territory; no extra acquisition policy selected |
| [msgspec/attrs/cattrs](../../../libraries/data_model/msgspec_attrs_and_cattrs.md), 1–53: orientation | DDM-04: distinct validation, object and representation responsibilities; no one-library-everywhere target |
| 54–316: msgspec codecs/Struct/constraints/tags/presence/Raw/conversion/schema/extensions | DDM-04: unused, uninstalled alternative for a concrete transport boundary; buffer/binary capabilities conditional |
| 317–496: attrs lifecycle/assignment/value semantics/reflection/integration | DDM-03/04: transitive availability; object-lifecycle use conditional on actual custom behavior removed |
| 497–771: cattrs generated hooks, types/overrides/unions/errors/policy/codecs/delegation | DDM-04: adopted exact reconstruction with broader archive representation candidate; preserve nested hook semantics |
| 772–845: composition/interoperability; 846–915: guarantees/identity/performance | DDM-03/04: compare complete construction and directional contracts, not interchangeable type annotations |
| 916–1006: versions/maturity/sources/synthesis | Baseline and boundary limits; no msgspec installation or blanket performance claim |

## Graph operations, conformance and portable validation

| Source and complete territory | Route and interpretation |
| --- | --- |
| [RDFLib](../../../libraries/data_model/rdflib.md), 1–176: architecture/terms/vocabularies; 177–470: graphs/datasets/algebra/traversal/lists/CBD/comparison | DDM-02/07/08: qualified graph already adopted; shared paths/comparison conditional; closure cannot be inferred from CBD |
| 471–783: SPARQL/extensibility/interchange; 784–1240: stores/RDF4J/GraphDB/plugins/utilities | DDM-07 and graph wider territory: prepared query/projection candidates require a consumer; alternate stores are not selected authority |
| 1241–1654: reasoning/validation ecosystem, boundaries/versions/synthesis/sources | DDM-07: derivation distinct from conformance, no implicit inference adopted |
| Addendum 1655–1936: patches, SPARQL pipeline, store contracts/events | Graph wider territory: conditional query/update use; patch markers and events do not establish committed custody |
| 1937–2167: evaluator settings, JSON-LD/HTML, SHACL path translation | DDM-07/08: native path translation unused; explicitly admit supported grammar |
| 2168–2505: infixowl/Describer, namespaces/identifier utilities/native paths | DDM-02/06/07: interoperability conditional; no second vocabulary/relationship authority |
| 2506–2758: hierarchies/lists/comparison/terms, version corrections/synthesis | DDM-07/08 and graph limits: exact semantic comparison differs from byte canonical identity |
| [pySHACL](../../../libraries/data_model/pyshacl.md), 1–146: execution/specification; 147–295: Core/paths/SPARQL | DDM-07: conformance and selected SPARQL already adopted; recurring components conditional |
| 296–670: AF/rules/inference/JS | Graph wider territory: separate optional derivation consumer; no rule/entailment profile change |
| 671–1096: backends/datasets/remote, controls/reports/deployment | DDM-07/08: reports retained, richer view candidate; selection does not compute affected closure; datasets validate as union |
| 1097–1281: boundaries/version changes/combinations/sources | Graph limits and baseline: backend equivalence and execution assumptions need qualification |
| Addendum 1282–1403: 0.40.2/support corrections; 1404–1668: discovery/deactivation/query context/reusable components | DDM-07: installed0.40.1 source checked for specific component behavior; later fixes remain candidate-version facts |
| 1669–1823: functions/rules/ontology mixing; 1824–2051: HTTP/exported engine/assets/CLI/semantic limits | Graph wider territory: no general truth maintenance, result annotations/entailment unsupported; services lack a selected consumer |
| [jsonschema](../../../libraries/data_model/jsonschema.md), 1–245: execution/dialects/composition/recursion; 246–438: registry/resolution/diagnostics | DDM-09: local prepared validators adopted; compositional resources and richer error views conditional |
| 439–715: extensions/formats/data-model boundaries; 716–862: ecosystem/combinations/compatibility/sources | DDM-09: native extensions only for an actual missing contract; generated inputs need independent expectations |
| Addendum 863–986: default retrieval/error selection/schema-format checking | DDM-09: each consumer's closure policy matters; absence of formats is not automatically a defect |
| 987–1241: Boolean/ref siblings/compound identity/dialects/numeric/equality/legacy semantics | DDM-09/04: profile and exact input semantics preserved, no silent schema dialect widening |
| 1242–1386: multiplicity/standardized-output limits/error categories | DDM-09: preserve original errors where needed; ErrorTree is not lossless |
| 1387–1602: protocol/vocabularies/unknown dialect/development distinctions/synthesis | DDM-09: supported vocabulary enforcement must be explicit; current-main availability is not installed support |

## Evidence strength and continuation

The overviews retain their October20–29 and November1 research dates. New local source and
selected installed implementation inspection is dated November10. Later addenda and conditional
families retain their documentary evidence strength; no probe established cross-library runtime
equivalence. Narrow searches found candidates and dormant paths, not global proof of absence.

All DDM leads route through the [summary](briefing.md#integrated-research-priorities) to substantive
mechanisms, actual consumers, broader use, defeat conditions and next questions. Complete
applicability/selection belongs to later stages. Keeping conditional territory here enables
future inquiry without inflating the current shortlist into an implementation commitment.
