"""Independent domain inputs over current rich contracts, without synthetic CPU evidence."""

from decimal import Decimal
from pathlib import Path

from corpus_structure.semantic.composed import data_operation_dependencies
from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
from corpus_structure.semantic.data_operation_identity import canonical_identity
from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.regeneration import acquire_pack
from corpus_structure.semantic.rich_fact_graph import RichFactGraph
from corpus_structure.semantic.rich_graph_validation import read_rich_graph
from corpus_structure.semantic.rich_knowledge_contracts import (
    DdoRichAuthoredBody,
    DdoRichAuthoredPacket,
    DdoRichAuthoredProposition,
    DdoRichAuthoredPropositions,
    DdoRichContext,
    DdoRichEntity,
)

ROOT = Path(__file__).resolve().parents[4]
NS = "https://corpus-structure.dev/semantic/data-operation-rich-knowledge/"


def domain_source(domain):
    """Prepare the actual domain and current rich operations; acquire no native standing."""
    from corpus_structure.semantic.math_context import acquire_analysis_context_profile
    from corpus_structure.semantic.record_policy_authority import record_policy_kind_declarations
    from corpus_structure.semantic.rich_invocations import rich_knowledge_operation_sources
    from corpus_structure.semantic.rich_knowledge_sources import (
        rich_knowledge_declarations,
        rich_knowledge_inputs,
    )
    from corpus_structure.semantic.types import ResolvedDependencies

    qualification = "StatisticsQualification" if domain == "statistics" else "ToyQualification"
    bundle, deps = rich_knowledge_inputs(
        acquire_pack(ROOT / "domains" / domain).bundle,
        ResolvedDependencies(),
        domain_rules=(ROOT / "domains" / domain / "schema/rules.yaml").read_bytes(),
        core_rules=(ROOT / "domains/core/schema/rules.yaml").read_bytes(),
        context_profile=acquire_analysis_context_profile(),
        qualification_class=qualification,
        statement_class="SourceStatement" if domain == "statistics" else "ToySourceStatement",
    )
    deps = data_operation_dependencies(
        deps,
        (*rich_knowledge_declarations(deps), record_policy_kind_declarations()),
        rich_knowledge_operation_sources(),
    )
    prepared = prepare_release(bundle, deps)
    return prepared, bound_data_operation_model(prepared), qualification


class DomainGraph:
    """Explicit authored meaning, distinct from source recognition and admitted computations."""

    def __init__(self, source, entities, *, context=None):
        self.prepared, self.model, self.qualification_class = source
        self.context = context or SubjectContext(
            "domain-controls",
            "domain-knowledge",
            None,
            b"{}",
            subject_definition="knowledge-universe",
        )
        self.classes = entities
        self.kinds = {
            item.owner: item.key for item in self.model.identities if item.domain == "kind"
        }
        self.lower = RichFactGraph(
            self.prepared,
            self.model,
            context=self.context,
            entities={
                key: frozenset({self.prepared.index.definitions[cls].iri})
                for key, cls in entities.items()
            },
            known_fact_ids=frozenset(),
        )
        self.results = {}
        self._state = None

    def add(self, key, subject, prop, value, *, qualification=None):
        result = self.lower.add_property_fact(
            subject_entity=subject,
            class_name=self.classes[subject],
            property_name=prop,
            value=value,
            qualification=qualification or {"modality": "asserted", "polarity": True},
            qualification_class=self.qualification_class,
        )
        self.results[key] = result
        self._state = None
        return result

    def propositions(self):
        members: dict[str, DdoRichAuthoredBody] = {}
        for identifier, cls in self.classes.items():
            contract = self.kinds[self.prepared.index.definitions[cls].iri]
            members[identifier] = DdoRichEntity(
                member_type="entity",
                entity_id=identifier,
                class_contracts=(contract,),
                identities=(
                    dict(class_contract=contract, fields=(), source_context=None, label=identifier),
                ),
                source_members=(),
            )
        for result in self.results.values():
            members[result.fact.fact_id] = result.fact
            identifier = canonical_identity(
                "rich-authored-proposition",
                [
                    self.context.identity_record,
                    result.fact.fact_id,
                    result.observed_qualification_value,
                    [],
                ],
            ).key
            members[identifier] = DdoRichAuthoredProposition(
                member_type="authored-proposition",
                proposition_id=identifier,
                fact_id=result.fact.fact_id,
                observed_qualification_value=result.observed_qualification_value,
                dependencies=(),
            )
        members.update((value.value_id, value) for value in self.lower.values)
        return DdoRichAuthoredPropositions(
            version="rich-authored-propositions-1",
            standing="authored-propositions",
            macros={},
            members=tuple(
                DdoRichAuthoredPacket(
                    member_id=key,
                    kind_contract=self.kinds[NS + type(body).__name__],
                    context=DdoRichContext(
                        subject=self.context.subject,
                        subject_definition=self.context.subject_definition,
                        original_source=None,
                        analyzed_scope={},
                    ),
                    body=body,
                )
                for key, body in sorted(members.items())
            ),
        )

    def state(self):
        if self._state is None:
            self._state = read_rich_graph(
                self.prepared,
                self.model,
                context=self.context,
                graph=self.propositions(),
                inputs=(),
                whole_inputs=(),
            )
        return self._state

    def object(self, key):
        state = self.state()
        fact = self.results[key].fact
        definition, prop, _ = state.property(fact.property_contract)
        return state.property_value(fact.object_value, definition, prop, item=prop.multivalued)

    def qualification(self, key):
        return self.state().value(self.results[key].observed_qualification_value)


def formula(expression, *bindings, kind="formula"):
    return dict(kind=kind, language="latex", expression=expression, bindings=bindings)


def inspection():
    return dict(
        kind="inspection",
        inspector="inspector",
        custodian="custodian",
        details=dict(
            condition="intact",
            measured_quantity=dict(
                kind="quantity", number=Decimal("12.3400"), unit="kg", basis="dry-mass"
            ),
        ),
    )


def t1(graph):
    positive = dict(
        kind="member",
        x=formula("b", dict(kind="family_param", symbol="b", entity="scale")),
        set=formula("(0, \\infty)", kind="set"),
    )
    graph.add(
        "construction",
        "LS",
        "construction_formula",
        formula(
            "a + b Z",
            dict(kind="free", symbol="a"),
            dict(kind="family_param", symbol="b", entity="scale"),
            dict(kind="variable", symbol="Z", entity="Z"),
        ),
        qualification=dict(
            modality="defined", polarity=True, base_variable="Z", condition=positive
        ),
    )
    graph.add("scale", "LS", "has_parameter", "scale")
    graph.add("scale-family", "scale", "family", "LS")
    graph.add("scale-name", "scale", "canonical_name", "scale")
    graph.add("scale-domain", "scale", "parameter_domain", formula("(0, \\infty)", kind="set"))


def t2(graph):
    for name in ("location", "scale", "mean", "standard_deviation"):
        graph.add("normal-" + name, "normal", "has_parameter", name)
        graph.add(name + "-family", name, "family", "normal")
        graph.add(name + "-name", name, "canonical_name", name)
    graph.add("location-is-mean", "location", "identical_parameter", "mean")
    graph.add("scale-is-sd", "scale", "identical_parameter", "standard_deviation")


def t4(graph):
    for name in ("mu", "sigma", "exp_mu_scale"):
        graph.add("lognormal-" + name, "lognormal", "has_parameter", name)
        graph.add(name + "-family", name, "family", "lognormal")
        graph.add(
            name + "-name", name, "canonical_name", "scale" if name == "exp_mu_scale" else name
        )
    graph.add("sigma-role", "sigma", "parameter_role", "shape")
    graph.add(
        "scale-derived",
        "exp_mu_scale",
        "derived_parameter",
        formula(
            "e^\\mu",
            dict(kind="constant", symbol="e"),
            dict(kind="family_param", symbol="\\mu", entity="mu"),
        ),
    )
    graph.add(
        "transformation",
        "lognormal",
        "transformation_of",
        "normal",
        qualification=dict(
            modality="defined",
            polarity=True,
            transform=formula(
                "e^Y",
                dict(kind="constant", symbol="e"),
                dict(kind="variable", symbol="Y", entity="Y"),
            ),
            param_mapping={
                "mu": dict(key="mu", value="mean"),
                "sigma": dict(key="sigma", value="standard_deviation"),
            },
        ),
    )
