"""Current typed query semantics; decoder checks are real, native standing is separate."""

import pytest

from corpus_structure.semantic import prepare_release
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_identity import decode_semantic_value
from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.data_operation_support import ComputationalSupportReference
from corpus_structure.semantic.refusals import InvalidContinuation
from corpus_structure.semantic.rich_fact_graph import RichFactGraph
from corpus_structure.semantic.rich_graph_validation import RichWholeInput, read_retained_rich_graph
from corpus_structure.semantic.rich_knowledge_contracts import (
    DdoRichAdmission,
    DdoRichContext,
    DdoRichEntity,
    DdoRichOccurrence,
    DdoRichPacket,
    DdoRichSelectedMember,
    DdoRichSourceReadingAssertion,
)
from corpus_structure.semantic.rich_queries import (
    ClaimsQuery,
    ConstructionProfileQuery,
    EntityQuery,
    EvidenceQuery,
    FamiliesWhereQuery,
    FamilyProfileQuery,
    ParameterMappingQuery,
    RelationsQuery,
    RichQueryIndex,
    RichQueryRefused,
    SourceReadingsQuery,
    StatementQuery,
    query_rows,
    rows_after,
)
from corpus_structure.semantic.rich_statistics_queries import relation_projection
from semantic.data_operation_declaration_support import contract, declarations
from semantic.record_contracts_support import release_inputs

PREFIX = "https://corpus-structure.dev/semantic/data-operation-rich-knowledge/"


@pytest.fixture(scope="module")
def query_source():
    from corpus_structure.semantic.rich_knowledge_sources import (
        rich_knowledge_declarations,
        rich_knowledge_schema_inputs,
    )
    from corpus_structure.semantic.types import ResolvedDependencies

    bundle, dependencies = rich_knowledge_schema_inputs(
        release_inputs()[0],
        ResolvedDependencies(),
        qualification_class="StatisticsQualification",
        statement_class="SourceStatement",
    )
    prepared = prepare_release(bundle, dependencies)
    operation = contract(
        subject="knowledge-universe",
        subject_definition={
            "id": "knowledge-universe",
            "identifier_kind": "string",
            "scope": "project",
        },
    )
    return prepared, compile_data_operations(
        bundle, declarations=(*declarations(operation), *rich_knowledge_declarations(dependencies))
    )


class Graph:
    """Independent source fixture lowers actual range contracts, never a fake prepared model."""

    def __init__(self, source, entities):
        self.prepared, self.model = source
        self.context = SubjectContext(
            "query-project", "query-universe", None, b"{}", subject_definition="knowledge-universe"
        )
        self.ids = {item.owner: item.key for item in self.model.identities if item.domain == "kind"}
        self.classes = {
            key: (value,) if isinstance(value, str) else value for key, value in entities.items()
        }
        self.entities = {key: value[0] for key, value in self.classes.items()}
        self.lower = RichFactGraph(
            self.prepared,
            self.model,
            context=self.context,
            entities={
                key: frozenset(self.prepared.index.definitions[cls].iri for cls in classes)
                for key, classes in self.classes.items()
            },
            known_fact_ids=frozenset(),
        )
        self.bodies = {}
        self.facts = {}
        self.selected = set()
        self.occurrences = set()
        self.readings = set()
        self.unretained_observations = set()
        # Controlled source provenance for pure decoder/query tests. This is not
        # an admitted native receipt and no native standing is claimed by these tests.
        self.origin = DdoRichSelectedMember(
            product_id="source-fixture",
            member_id="actual-proposal",
            kind_contract="opaque:historical-proposal",
            support_references=(
                ComputationalSupportReference(
                    derivation_id="source-episode", admission_use_id="source-use"
                ),
            ),
        )

    def add(
        self,
        key,
        subject,
        prop,
        value,
        *,
        qualification=None,
        selected=True,
        statement_product="source-A",
        statement_member="statement-1",
        role=None,
        structural=False,
    ):
        result = self.lower.add_property_fact(
            subject_entity=subject,
            class_name=self.entities[subject],
            property_name=prop,
            value=value,
            qualification=qualification or {"modality": "asserted", "polarity": True},
            qualification_class="StatisticsQualification",
        )
        self.facts[key] = result.fact.fact_id
        self.bodies[result.fact.fact_id] = result.fact
        if selected:
            self.selected.add(result.fact.fact_id)
        if structural:
            self.unretained_observations.add(result.observed_qualification_value)
        else:
            occurrence = DdoRichOccurrence(
                member_type="source-occurrence",
                occurrence_id="occurrence:" + key,
                fact_id=result.fact.fact_id,
                original=self.origin,
                statement=self.origin.model_copy(
                    update={"product_id": statement_product, "member_id": statement_member}
                ),
                observed_qualification_value=result.observed_qualification_value,
                dependencies=(),
                establishment="stated",
                statement_kind="definition" if role else None,
                statement_role=role,
                evidence_count=1,
            )
            self.bodies[occurrence.occurrence_id] = occurrence
            if selected:
                self.occurrences.add(occurrence.occurrence_id)
        return result.fact.fact_id

    def index(self):
        bodies = dict(self.bodies)
        for key in self.entities:
            class_ids = tuple(
                sorted(
                    self.ids[self.prepared.index.definitions[name].iri]
                    for name in self.classes[key]
                )
            )
            bodies[key] = DdoRichEntity(
                member_type="entity",
                entity_id=key,
                class_contracts=class_ids,
                identities=tuple(
                    {"class_contract": cls_id, "fields": (), "label": key, "source_context": None}
                    for cls_id in class_ids
                ),
                source_members=(self.origin,),
            )
        bodies.update(
            (value.value_id, value)
            for value in self.lower.values
            if value.value_id not in self.unretained_observations
        )
        packets = tuple(
            DdoRichPacket(
                member_id=key,
                kind_contract=self.ids[PREFIX + type(body).__name__],
                context=DdoRichContext(
                    subject=self.context.subject,
                    subject_definition=self.context.subject_definition,
                    original_source=None,
                    analyzed_scope={},
                ),
                body=body,
            )
            for key, body in sorted(bodies.items())
        )
        admission = DdoRichAdmission(
            version="rich-admission-1",
            standing="accepted",
            eligibility_policy_digest="a" * 64,
            selected_fact_ids=tuple(sorted(self.selected)),
            selected_occurrence_ids=tuple(sorted(self.occurrences)),
            selected_reading_ids=tuple(sorted(self.readings)),
            scientific_representatives=tuple(
                dict(
                    fact_id=key,
                    representative_fact_id=key,
                    component_id=key,
                    policy="min-fact-id-1",
                )
                for key in sorted(self.selected)
            ),
            members=packets,
            consolidation=self.origin.model_copy(update={"member_id": None}),
            policy_authorizations=(),
            reading_decisions=(),
        )
        ref = self.origin.model_copy(
            update={
                "product_id": "selected-knowledge",
                "member_id": None,
                "kind_contract": self.ids[PREFIX + "DdoRichAdmission"],
            }
        )
        proof = RichWholeInput(ref, admission)
        self.root_input = proof
        state = read_retained_rich_graph(
            self.prepared,
            self.model,
            context=self.context,
            retained=proof,
            inputs=(ref,),
            whole_inputs=(proof,),
        )
        return RichQueryIndex(state)


def rows(index, query):
    return [item.value for item in query_rows(index, query)]


def ids(values):
    return {item["fact"]["fact_id"] for item in values}


@pytest.fixture
def statistics(query_source):
    graph = Graph(
        query_source,
        {
            "normal": "DistributionFamily",
            "standard": "DistributionFamily",
            "construction": "FamilyConstruction",
            "other": "DistributionFamily",
            "scale": "FamilyParameter",
            "X": "RandomVariable",
            "Y": "RandomVariable",
        },
    )
    graph.add("family", "scale", "family", "normal")
    graph.add("name", "scale", "canonical_name", "scale")
    graph.add("role", "scale", "parameter_role", "scale")
    graph.add("parameter", "normal", "has_parameter", "scale")
    graph.add(
        "member",
        "normal",
        "member_of_construction",
        "construction",
        qualification={
            "modality": "asserted",
            "polarity": True,
            "base": "standard",
            "base_variable": "X",
        },
    )
    graph.add(
        "construction-formula",
        "construction",
        "construction_formula",
        {
            "kind": "formula",
            "language": "latex",
            "expression": "X",
            "bindings": ({"kind": "variable", "symbol": "X", "entity": "X"},),
        },
        qualification={"modality": "asserted", "polarity": True, "base_variable": "X"},
    )
    graph.add("other-member", "other", "member_of_construction", "construction")
    graph.add("relation", "standard", "special_case_of", "normal")
    graph.add(
        "premise",
        "X",
        "has_distribution",
        "normal",
        selected=False,
        qualification={"modality": "supposed", "polarity": True},
    )
    graph.add("other-premise", "X", "symbol", "X", selected=False)
    condition = {
        "kind": "all",
        "terms": (
            {"kind": "claim", "ref": graph.facts["premise"]},
            {"kind": "claim", "ref": graph.facts["other-premise"]},
        ),
    }
    graph.add(
        "conclusion",
        "Y",
        "has_distribution",
        "normal",
        qualification={"modality": "asserted", "polarity": True, "condition": condition},
    )
    graph.add(
        "definition",
        "Y",
        "defined_as",
        {
            "kind": "formula",
            "language": "latex",
            "expression": "X+1",
            "bindings": ({"kind": "variable", "symbol": "X", "entity": "X"},),
        },
        role="definiens",
    )
    graph.add(
        "foreign-definition",
        "Y",
        "symbol",
        "foreign",
        statement_product="source-B",
        role="definiens",
    )
    return graph, graph.index()


def test_six_statistics_queries_retain_parameter_mapping_full_premises_and_statement_scope(
    statistics,
):
    graph, index = statistics
    expected = {graph.facts[name] for name in ("family", "name", "role", "parameter", "member")}
    assert ids(rows(index, FamilyProfileQuery(name="family_profile", family="NORMAL"))) == expected
    mapping = rows(
        index,
        ParameterMappingQuery(
            name="parameter_mapping", family="normal", construction="construction"
        ),
    )
    assert graph.facts["member"] in ids(mapping) and graph.facts["other-member"] not in ids(mapping)
    member = next(item for item in mapping if item["fact"]["fact_id"] == graph.facts["member"])
    assert decode_semantic_value(member["occurrences"][0]["qualification"])["base"] == "standard"
    assert {
        item["family"]["entity"]["entity_id"]
        for item in rows(
            index,
            FamiliesWhereQuery(
                name="families_where", predicate="stat:parameter_role", value="scale"
            ),
        )
    } == {"normal"}
    construction = rows(
        index,
        ConstructionProfileQuery(
            name="construction_profile",
            construction="construction",
            include_suppositions=True,
            population="retained",
        ),
    )
    assert graph.facts["premise"] in ids(construction)
    transformed = rows(index, FamilyProfileQuery(name="transformations_of", family="normal"))
    assert len(transformed) == 1
    assert ids(transformed[0]["premises"]) == {graph.facts["premise"], graph.facts["other-premise"]}
    assert ids(transformed[0]["definiens"]) == {graph.facts["definition"]}
    assert transformed[0]["premises"][0]["selected"] is False
    relation = rows(index, RelationsQuery(name="relations_between", a="standard", b="normal"))
    assert [row["fact_ids"] for row in relation] == [[graph.facts["relation"]]]


def test_generic_queries_preserve_selection_typed_values_and_original_evidence(statistics):
    graph, index = statistics
    assert graph.facts["premise"] not in ids(rows(index, ClaimsQuery(name="claims")))
    assert graph.facts["premise"] in ids(
        rows(index, ClaimsQuery(name="claims", population="retained", include_suppositions=True))
    )
    entities = rows(index, EntityQuery(name="entity", class_name="DistributionFamily"))
    assert {item["entity"]["entity_id"] for item in entities} == {"normal", "standard", "other"}
    assert all(item["standing"] == "resolved-identity" for item in entities)
    statement = rows(
        index, StatementQuery(name="statement", product_id="source-A", member_id="statement-1")
    )
    assert graph.facts["foreign-definition"] not in ids(statement[0]["claims"])
    evidence = rows(index, EvidenceQuery(name="evidence", fact_id=graph.facts["member"]))
    assert evidence[0]["occurrence"]["original"]["product_id"] == "source-fixture"
    assert evidence[0]["source_body_retrieval"] == "not_run"


def test_walks_keep_parallel_edges_cycles_intermediate_vertices_and_exact_budgets(query_source):
    graph = Graph(query_source, {name: "DistributionFamily" for name in ("A", "B", "X")})
    e1 = graph.add("e1", "A", "special_case_of", "B")
    e2 = graph.add("e2", "B", "special_case_of", "A")
    graph.add(
        "unrelated",
        "A",
        "mean_value",
        {"kind": "formula", "language": "latex", "expression": "1", "bindings": ()},
    )
    index = graph.index()
    result = rows(index, RelationsQuery(name="relations_between", a="A", b="B", depth=4))
    assert [item["fact_ids"] for item in result] == [[e1], [e1, e2, e1]]
    projection = relation_projection(index, RelationsQuery(name="relations_between", a="A", b="B"))
    assert projection.is_multigraph() and set(projection.nodes) == {"A", "B", "X"}
    with pytest.raises(RichQueryRefused, match="adjacency"):
        rows(index, RelationsQuery(name="relations_between", a="A", b="B", max_edges=2))
    with pytest.raises(RichQueryRefused, match="state bytes"):
        rows(index, RelationsQuery(name="relations_between", a="A", b="B", max_state_bytes=1))
    # Parallel edges have different predicates/IDs; no relationship relabelling.
    parallel = graph.add("parallel", "A", "transformation_of", "B")
    loop = graph.add("loop", "A", "limit_of", "A")
    index = graph.index()
    result = rows(index, RelationsQuery(name="relations_between", a="A", b="B", depth=2))
    expected = sorted(([e1], [parallel]), key=lambda path: path[0]) + sorted(
        ([loop, e1], [loop, parallel]), key=lambda path: path[1]
    )
    assert [item["fact_ids"] for item in result] == expected
    with pytest.raises(RichQueryRefused, match="frontier"):
        rows(index, RelationsQuery(name="relations_between", a="A", b="B", max_frontier=1))
    intermediate = Graph(query_source, {name: "DistributionFamily" for name in ("A", "B", "X")})
    first = intermediate.add("first", "A", "special_case_of", "X")
    second = intermediate.add("second", "X", "limit_of", "B")
    assert [
        item["fact_ids"]
        for item in rows(
            intermediate.index(), RelationsQuery(name="relations_between", a="A", b="B")
        )
    ] == [[first, second]]


def test_query_continuation_requires_actual_matching_witness_and_replay_spends_work(statistics):
    _, index = statistics
    query = ClaimsQuery(name="claims")
    ordered = list(query_rows(index, query))
    assert list(rows_after(query_rows(index, query), ordered[0].position)) == ordered[1:]
    with pytest.raises(InvalidContinuation):
        list(rows_after(query_rows(index, query), "fabricated-position"))


def test_structural_selected_fact_needs_no_invented_source_occurrence(query_source):
    graph = Graph(query_source, {"A": "DistributionFamily", "B": "DistributionFamily"})
    fact = graph.add("structural", "A", "special_case_of", "B", structural=True)
    result = rows(graph.index(), ClaimsQuery(name="claims"))
    assert ids(result) == {fact}
    assert result[0]["occurrences"] == [] and result[0]["selected"] is True


def test_source_reading_query_keeps_complete_typed_fields_without_domain_truth(query_source):
    from corpus_structure.semantic.rich_record_readings import rich_reading_value
    from semantic.test_rich_record_readings import inspected_reading

    graph = Graph(query_source, {})
    record, coordinates = inspected_reading("definition")
    value = rich_reading_value(graph.prepared, graph.model, record, coordinate_texts=coordinates)
    value_id = graph.lower.lower_record(
        value.class_name, {"id": record["record_id"], **value.fields}
    )
    resolution = graph.origin.model_copy(
        update={"product_id": "source-resolution", "member_id": None}
    )
    assertion = DdoRichSourceReadingAssertion(
        member_type="source-reading-assertion",
        reading_id="reading:actual",
        record_id=record["record_id"],
        source_interpretation_id=record["interpretation_id"],
        interpretation_id=record["interpretation_id"],
        original=graph.origin,
        resolution=resolution,
        resolved=resolution.model_copy(update={"member_id": "resolved-record"}),
        reading_value=value_id,
    )
    graph.bodies[assertion.reading_id] = assertion
    graph.readings.add(assertion.reading_id)
    index = graph.index()
    result = rows(index, SourceReadingsQuery(name="source_readings"))
    assert len(result) == 1 and result[0]["scientific_truth"] == "not-established"
    actual = decode_semantic_value(result[0]["reading"])
    assert set(actual) == {"id", *(field["role"] for field in record["fields"])}
    assert actual["id"] == record["record_id"]
    assert result[0]["assertion"]["original"]["product_id"] == "source-fixture"
    assert rows(index, ClaimsQuery(name="claims")) == []


def test_entity_query_preserves_all_actual_class_memberships_without_a_scalar_type_alias(
    query_source,
):
    graph = Graph(query_source, {"shared": ("DistributionFamily", "FamilyConstruction")})
    index = graph.index()
    family = rows(index, EntityQuery(name="entity", class_name="DistributionFamily"))
    construction = rows(index, EntityQuery(name="entity", class_name="FamilyConstruction"))
    assert family == construction
    assert set(family[0]["classes"]) == {
        query_source[0].index.definitions[name].iri
        for name in ("DistributionFamily", "FamilyConstruction")
    }
    assert family[0]["selected_fact_ids"] == []
