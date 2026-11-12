"""Independent characterization meaning and deliberately invalid retained graphs."""

import copy
from pathlib import Path
from typing import Any, cast

import pytest

from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.characterization import (
    annotation_reference,
    characterization_inputs,
    decode_layer,
    encode_layer,
    occurrence_id,
    project_reading,
    validate_layer,
    validate_reading_choices,
    validate_view,
)
from corpus_structure.semantic.product_reference import ProductReference


@pytest.fixture(scope="module")
def prepared():
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    return prepare_release(
        characterization_inputs(SourceBundle("core", (SourceArtifact("core", core.read_bytes()),)))
    )


def layer_payload(prepared) -> dict[str, Any]:
    base = {"task_id": 7, "product_key": "document", "content_digest": "a" * 64}
    projection = "b" * 64
    selector = {"projection": projection, "native_pointer": "#/texts/0", "page": 3}
    scope = {
        "source_view_ids": [11],
        "source_views": [
            {
                "source_view_id": 11,
                "key": "section-source-v1",
                "base_document": base,
                "section_pointer": "#/groups/0",
                "membership": "descendants",
                "projection_digest": projection,
                "recipe_digest": "c" * 64,
            }
        ],
        "profile": "full",
        "selectors": [selector],
    }
    extents = [
        dict(
            projection=projection,
            source_view_id=11,
            native_pointer="#/texts/0",
            page=3,
            start=0,
            end=3,
            text="all",
            synthetic=False,
        )
    ]
    occurrence = {"local_id": occurrence_id(base, extents), "extents": extents}

    # This expected graph is literal test data: scope distinction is not produced by a constructor.
    def term(key, kind, value, children=()):
        return {
            "local_id": key,
            "family": "scope",
            "kind": kind,
            "vocabulary": "logic",
            "value": value,
            "status": "interpreted",
            "occurrences": [occurrence["local_id"]],
            "children": list(children),
        }

    def edge(role, target):
        return {"role": role, "target": target, "structural": True}

    return {
        "format": "characterization-layer-v1",
        "base_document": base,
        "release_id": prepared.release_id,
        "operation": {
            "key": "text.characterize",
            "version": "1",
            "runtime": "test-runtime",
            "model": "none",
            "grammar": "logic-1",
            "configuration": "cfg",
            "input": "source-1",
            "context": "section",
            "produced_families": ["scope"],
            "outcomes": ["complete", "partial", "failed"],
            "result_determinants": ["grammar", "input", "context"],
        },
        "source_scope": scope,
        "outcome": "complete",
        "occurrences": [occurrence],
        "terms": [
            term("p", "predicate", "P"),
            term("x", "participant", "x"),
            term("r", "predicate", "R"),
            term(
                "forall",
                "binder",
                "all",
                [edge("variable", "x"), edge("restrictor", "r"), edge("body", "p")],
            ),
            term("not_all", "operator", "not", [edge("target", "forall")]),
            term("not_p", "operator", "not", [edge("target", "p")]),
            term(
                "all_not",
                "binder",
                "all",
                [edge("variable", "x"), edge("restrictor", "r"), edge("body", "not_p")],
            ),
            term("or", "operator", "or", [edge("left", "p"), edge("right", "r")]),
        ],
        "coverage": [
            {
                "family": "scope",
                "operation": "text.characterize",
                "eligible": [selector],
                "examined": [selector],
                "availability": "available",
                "outcome": "complete",
                "profile": "full",
            }
        ],
    }


def test_release_generates_actual_shapes_and_keeps_scope_readings_distinct(prepared):
    report = validate_layer(prepared, layer_payload(prepared))
    assert set(prepared.adapter("AnnotationLayer").json_schema()["properties"]) >= {
        "terms",
        "choices",
        "coverage",
    }
    left = project_reading(report, "not_all")
    right = project_reading(report, "all_not")
    assert (
        next(t for t in left["terms"] if t["local_id"] == "not_all")["children"][0]["target"]
        == "forall"
    )
    assert (
        next(t for t in right["terms"] if t["local_id"] == "all_not")["children"][2]["target"]
        == "not_p"
    )
    assert len(project_reading(report, "or")["terms"]) == 3
    assert decode_layer(prepared, encode_layer(report)).content == report.content
    pin = report.reference(8)
    assert annotation_reference(pin, "p").values() == {"layer": pin.values(), "local_id": "p"}
    body = report.payload
    body["terms"].clear()
    assert report.payload["terms"]  # the validated wrapper cannot be mutated through a read


def test_view_validation_releases_independent_root_reports(prepared, monkeypatch):
    import weakref

    import corpus_structure.semantic.characterization as characterization

    layers = {}
    for index in range(4):
        payload = layer_payload(prepared)
        payload["operation"]["input"] = f"source-{index}"
        report = validate_layer(prepared, payload)
        layers[report.reference(8 + index)] = report
    first = next(iter(layers.values())).payload
    validated = []
    validate = characterization.validate_layer_structure

    class TrackedReport(characterization.LayerReport):
        pass

    def observe(*args, **kwargs):
        assert all(reference() is None for reference in validated)
        report = TrackedReport(validate(*args, **kwargs).content)
        validated.append(weakref.ref(report))
        return report

    monkeypatch.setattr(characterization, "validate_layer_structure", observe)
    view = validate_view(
        prepared,
        dict(
            format="enriched-document-view-v1",
            base_document=first["base_document"],
            release_id=prepared.release_id,
            source_scope=first["source_scope"],
            layers=[pin.values() for pin in layers],
            profile="selected_layers",
            coverage=first["coverage"],
        ),
        layers,
    )
    assert len(view.payload["layers"]) == len(validated) == 4
    assert all(reference() is None for reference in validated)


def test_occurrences_independent_of_analysis_and_database_placement(prepared):
    payload = layer_payload(prepared)
    extents = payload["occurrences"][0]["extents"]
    first = occurrence_id(payload["base_document"], extents)
    other = copy.deepcopy(extents)
    other[0]["source_view_id"] = 99
    assert occurrence_id(payload["base_document"], other) == first
    other[0]["native_pointer"] = "#/texts/1"
    assert occurrence_id(payload["base_document"], other) != first


@pytest.mark.parametrize(
    "case",
    [
        "dangling",
        "cycle",
        "wrong_projection",
        "wrong_document",
        "unknown_field",
        "coerced_integer",
        "literal_length",
        "incomplete",
        "empty_output",
        "undeclared_outcome",
    ],
)
def test_invalid_products_refuse(prepared, case):
    body = layer_payload(prepared)
    if case == "dangling":
        body["terms"][3]["children"][0]["target"] = "missing"
    if case == "cycle":
        body["terms"][3]["children"][2]["target"] = "not_all"
    if case == "wrong_projection":
        body["occurrences"][0]["extents"][0]["projection"] = "d" * 64
    if case == "wrong_document":
        body["source_scope"]["source_views"][0]["base_document"] = {
            **body["base_document"],
            "task_id": 8,
        }
    if case == "unknown_field":
        body["invented"] = True
    if case == "coerced_integer":
        body["base_document"]["task_id"] = "7"
    if case == "literal_length":
        body["occurrences"][0]["extents"][0]["text"] = "different"
    if case == "incomplete":
        body["coverage"][0]["unexamined"] = body["coverage"][0]["eligible"]
    if case == "empty_output":
        body["coverage"][0]["outcome"] = "empty"
    if case == "undeclared_outcome":
        body["operation"]["outcomes"] = ["failed"]
    with pytest.raises(ValueError):
        validate_layer(prepared, body)


def test_discontinuity_cross_page_overlapping_memberships_and_native_scores(prepared):
    body = layer_payload(prepared)
    occurrence = copy.deepcopy(body["occurrences"][0])
    occurrence["extents"][0].update(page=4, native_pointer="#/texts/1", start=7, end=10)
    occurrence["local_id"] = occurrence_id(body["base_document"], occurrence["extents"])
    body["occurrences"].append(occurrence)
    a, b = [x["local_id"] for x in body["occurrences"]]
    body["annotations"] = [
        {
            "local_id": key,
            "family": "scope",
            "kind": "group",
            "vocabulary": "toy",
            "status": "native_evidence",
            "occurrences": [a, b],
            "scores": [
                {
                    "scheme": "native-score",
                    "value": {"kind": "float", "hexadecimal": "0x1.8000000000000p-1"},
                    "meaning": "unnormalized score",
                }
            ],
            "provenance": ["model-v1"],
        }
        for key in ("g", "h")
    ]
    body["memberships"] = [
        {
            "local_id": key,
            "family": "scope",
            "group": group,
            "member": "p",
            "role": "fragment",
            "scope": "source",
            "structural": False,
            "occurrences": [a, b],
        }
        for key, group in [("m1", "g"), ("m2", "h")]
    ]
    body["roles"] = [
        {
            "local_id": "role",
            "family": "scope",
            "owner": "g",
            "member": "p",
            "role": "subject",
            "scheme": "dependency",
            "occurrences": [b, a],
            "basis": {
                "kind": "native_prediction",
                "status": "recorded",
                "native_scheme": "parser-1",
                "native_label": "nsubj",
            },
        }
    ]
    result = validate_layer(prepared, body).payload
    assert result["roles"][0]["occurrences"] == [b, a]
    assert result["annotations"][0]["scores"][0]["value"] == {
        "kind": "float",
        "hexadecimal": "0x1.8000000000000p-1",
    }
    assert result["annotations"][0]["occurrences"] == [a, b]


def test_declared_attachment_policy_rejects_model_promotion_and_missing_premises(prepared):
    body = layer_payload(prepared)
    body["roles"] = [
        {
            "local_id": "role",
            "family": "scope",
            "owner": "forall",
            "member": "p",
            "role": "body",
            "scheme": "logic",
            "basis": {"kind": "contextual_proposal", "status": "witnessed"},
        }
    ]
    with pytest.raises(ValueError):
        validate_layer(prepared, body)
    body["roles"][0]["basis"] = {
        "kind": "released_construction",
        "status": "witnessed",
        "rule_id": "r1",
    }
    with pytest.raises(ValueError):
        validate_layer(prepared, body)
    basis: dict[str, Any] = body["roles"][0]["basis"]
    basis["premises"] = ["p"]
    with pytest.raises(ValueError, match="released attachment rule"):
        validate_layer(prepared, body)


def test_analytical_alternatives_require_explicit_compatible_choices(prepared):
    body = layer_payload(prepared)
    body["choices"] = [
        {
            "local_id": "choice",
            "family": "scope",
            "compatibility": "unknown",
            "members": [{"local_id": "a", "root": "not_all"}, {"local_id": "b", "root": "all_not"}],
        }
    ]
    report = validate_layer(prepared, body)
    assert validate_reading_choices(report.payload, ("a",)) == ("a",)
    for selected in [("a", "b"), ("missing",)]:
        with pytest.raises(ValueError):
            validate_reading_choices(report.payload, selected)
    member: dict[str, Any] = body["choices"][0]["members"][0]
    member["required_choices"] = ["b"]
    with pytest.raises(ValueError, match="missing"):
        validate_reading_choices(body, ("a",))
    assert project_reading(report, "not_all", choices=("a",))["choices"] == ["a"]


def test_view_exact_closure_and_source_only_weaker(prepared):
    body = layer_payload(prepared)
    layer = validate_layer(prepared, body)
    pin = layer.reference(8)
    view = {
        "format": "enriched-document-view-v1",
        "base_document": body["base_document"],
        "release_id": prepared.release_id,
        "source_scope": body["source_scope"],
        "profile": "full",
        "layers": [pin.values()],
        "coverage": body["coverage"],
    }
    assert validate_view(prepared, view, {pin: layer}).base_document == ProductReference(
        **body["base_document"]
    )
    with pytest.raises(ValueError, match="missing"):
        validate_view(prepared, view, {})
    weak = {**view, "profile": "source_only", "layers": [], "coverage": []}
    assert validate_view(prepared, weak, {}).payload["profile"] == "source_only"
    with pytest.raises(ValueError, match="source_only"):
        validate_view(prepared, {**weak, "coverage": body["coverage"]}, {})


def test_explicit_unknown_and_successful_empty_are_distinct(prepared):
    body = layer_payload(prepared)
    body["terms"] = []
    body["coverage"][0]["outcome"] = "empty"
    assert validate_layer(prepared, body).payload["coverage"][0]["outcome"] == "empty"
    body["outcome"] = "partial"
    body["coverage"][0].update(
        availability="unknown", outcome="unknown", reason="not examined", examined=[]
    )
    assert validate_layer(prepared, body).payload["coverage"][0]["outcome"] == "unknown"


def test_cross_layer_premises_require_exact_same_base_and_reachable_local_id(prepared):
    original = layer_payload(prepared)
    dependency = validate_layer(prepared, original)
    pin = dependency.reference(8)
    derived = copy.deepcopy(original)
    derived["operation"]["version"] = "2"
    derived["dependencies"] = [pin.values()]
    derived["annotations"] = [
        {
            "local_id": "annotation",
            "family": "scope",
            "kind": "construction",
            "vocabulary": "other-domain",
            "status": "interpreted",
            "occurrences": [original["occurrences"][0]["local_id"]],
            "external_premises": [{"layer": pin.values(), "local_id": "p"}],
        }
    ]
    with pytest.raises(ValueError, match="dependency closure"):
        validate_layer(prepared, derived)
    assert (
        validate_layer(prepared, derived, dependencies={pin: dependency}).payload["annotations"][0][
            "vocabulary"
        ]
        == "other-domain"
    )
    derived["annotations"][0]["external_premises"][0]["local_id"] = "absent"
    with pytest.raises(ValueError, match="dangling external"):
        validate_layer(prepared, derived, dependencies={pin: dependency})
    derived["annotations"][0]["external_premises"][0]["local_id"] = "p"
    other = copy.deepcopy(original)
    other["base_document"] = {**other["base_document"], "task_id": 9}
    other["source_scope"]["source_views"][0]["base_document"] = other["base_document"]
    old_id = other["occurrences"][0]["local_id"]
    new_id = occurrence_id(other["base_document"], other["occurrences"][0]["extents"])
    other["occurrences"][0]["local_id"] = new_id
    for term in other["terms"]:
        term["occurrences"] = [new_id if i == old_id else i for i in term["occurrences"]]
    wrong = validate_layer(prepared, other)
    wrong_pin = wrong.reference(8)
    derived["dependencies"] = [wrong_pin.values()]
    derived["annotations"][0]["external_premises"][0]["layer"] = wrong_pin.values()
    with pytest.raises(ValueError, match="wrong-source"):
        validate_layer(prepared, derived, dependencies={wrong_pin: wrong})


def test_referring_edges_can_cycle_without_a_structural_cycle(prepared):
    body = layer_payload(prepared)
    body["roles"] = [
        {
            "local_id": key,
            "family": "scope",
            "owner": owner,
            "member": member,
            "role": "discourse_reference",
            "scheme": "discourse",
            "basis": {
                "kind": "native_prediction",
                "status": "recorded",
                "native_scheme": "discourse",
                "native_label": "reference",
            },
        }
        for key, owner, member in [("forward", "p", "r"), ("backward", "r", "p")]
    ]
    assert len(validate_layer(prepared, body).payload["roles"]) == 2


def test_semantic_child_cycle_cannot_hide_as_nonstructural(prepared):
    body = layer_payload(prepared)
    body["terms"][4]["children"] = [{"role": "target", "target": "not_all", "structural": False}]
    with pytest.raises(ValueError, match="children must be structural"):
        validate_layer(prepared, body)


def test_released_rule_dispatch_compiles_from_actual_declaration():
    import yaml

    model_root = Path(__file__).parents[2] / "src/corpus_structure/model/semantic"
    model = yaml.safe_load((model_root / "characterization.yaml").read_bytes())
    model["classes"]["ToyReleasedAttachment"] = {
        "is_a": "CharacterizationConstructionBasis",
        "attributes": {
            "rule_id": {"required": True, "equals_string": "toy:body-v1"},
            "premises": {
                "range": "string",
                "multivalued": True,
                "required": True,
                "minimum_cardinality": 2,
            },
        },
    }
    released = prepare_release(
        characterization_inputs(
            SourceBundle(
                "core", (SourceArtifact("core", (model_root / "core.yaml").read_bytes()),)
            ),
            model_content=yaml.safe_dump(model).encode(),
        )
    )
    body = layer_payload(released)
    body["roles"] = [
        {
            "local_id": "attachment",
            "family": "scope",
            "owner": "forall",
            "member": "p",
            "role": "body",
            "scheme": "toy",
            "basis": {
                "kind": "released_construction",
                "status": "witnessed",
                "rule_id": "toy:body-v1",
                "premises": ["p", "r"],
            },
        }
    ]
    assert validate_layer(released, body).payload["roles"][0]["basis"]["rule_id"] == "toy:body-v1"
    body["roles"][0]["basis"]["premises"] = ["p"]
    with pytest.raises(ValueError):
        validate_layer(released, body)
    body["roles"][0]["basis"].update(premises=["p", "r"], rule_id="not-released")
    with pytest.raises(ValueError, match="released attachment rule"):
        validate_layer(released, body)


def test_view_composes_different_source_subsets_without_promoting_coverage(prepared):
    one = layer_payload(prepared)
    two = copy.deepcopy(one)
    two["source_scope"]["source_view_ids"] = [12]
    pin = two["source_scope"]["source_views"][0]
    pin.update(source_view_id=12, key="section-two", projection_digest="d" * 64)
    two["source_scope"]["selectors"][0]["projection"] = "d" * 64
    for row in two["coverage"]:
        for key in ("eligible", "examined"):
            row[key][0]["projection"] = "d" * 64
    extent = two["occurrences"][0]["extents"][0]
    extent.update(source_view_id=12, projection="d" * 64, native_pointer="#/texts/2")
    occurrence = occurrence_id(two["base_document"], two["occurrences"][0]["extents"])
    two["occurrences"][0]["local_id"] = occurrence
    for term in two["terms"]:
        term["occurrences"] = [occurrence]
    l1, l2 = validate_layer(prepared, one), validate_layer(prepared, two)
    p1, p2 = l1.reference(8), l2.reference(9)
    scope = {
        "source_view_ids": [11, 12],
        "source_views": [
            *one["source_scope"]["source_views"],
            *two["source_scope"]["source_views"],
        ],
        "profile": "composed",
        "selectors": [*one["source_scope"]["selectors"], *two["source_scope"]["selectors"]],
    }
    view = {
        "format": "enriched-document-view-v1",
        "base_document": one["base_document"],
        "release_id": prepared.release_id,
        "source_scope": scope,
        "profile": "composed",
        "layers": [p1.values(), p2.values()],
        "coverage": [*one["coverage"], *two["coverage"]],
    }
    assert len(validate_view(prepared, view, {p1: l1, p2: l2}).payload["coverage"]) == 2
    view["coverage"][0]["profile"] = "invented-full"
    with pytest.raises(ValueError, match="not supported"):
        validate_view(prepared, view, {p1: l1, p2: l2})


@pytest.mark.parametrize("value", [-0.0, 1e-100, 1e100, 2**90, None])
def test_exact_native_scores_never_depend_on_json_number_rendering(prepared, value):
    import math

    from corpus_structure.semantic.observations import source_python, source_value

    body = layer_payload(prepared)
    body["terms"][0]["scores"] = [
        {
            "scheme": "native",
            "meaning": "native score, without reinterpretation",
            "value": source_value(value),
        }
    ]
    restored = decode_layer(prepared, encode_layer(validate_layer(prepared, body))).payload
    score = source_python(restored["terms"][0]["scores"][0]["value"])
    assert type(score) is type(value) and score == value
    if value == 0.0:
        assert math.copysign(1, score) == math.copysign(1, value)


@pytest.mark.parametrize(
    "value", [{"kind": "float", "hexadecimal": "nan"}, {"kind": "float", "hexadecimal": "0x1.8p-1"}]
)
def test_score_codec_rejects_nonfinite_or_noncanonical_value(prepared, value):
    body = layer_payload(prepared)
    body["terms"][0]["scores"] = [{"scheme": "native", "meaning": "score", "value": value}]
    with pytest.raises(ValueError):
        validate_layer(prepared, body)


def test_synthetic_boundary_is_distinct_from_empty_literal_source(prepared):
    body = layer_payload(prepared)
    extent = body["occurrences"][0]["extents"][0]
    old_id = body["occurrences"][0]["local_id"]
    extent.update(start=0, end=0, text="synthetic boundary", synthetic=True)
    new_id = occurrence_id(body["base_document"], [extent])
    body["occurrences"][0]["local_id"] = new_id
    for term in body["terms"]:
        term["occurrences"] = [
            new_id if identity == old_id else identity for identity in term["occurrences"]
        ]
    assert (
        validate_layer(prepared, body).payload["occurrences"][0]["extents"][0]["synthetic"] is True
    )
    extent.update(text="", synthetic=False)
    body["occurrences"][0]["local_id"] = occurrence_id(body["base_document"], [extent])
    with pytest.raises(ValueError, match="nonempty extent"):
        validate_layer(prepared, body)


def test_entire_characterization_family_is_private_boundary_not_native_graph(prepared):
    import yaml

    from corpus_structure.semantic.publication import native_constraints
    from corpus_structure.semantic.record_contracts import record_product_classes

    model = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/characterization.yaml"
    declared = set(yaml.safe_load(model.read_bytes())["classes"])
    products = record_product_classes(prepared.definitions)
    assert declared <= products
    private_iris = {
        definition.iri for definition in prepared.definitions if definition.name in declared
    }
    assert not private_iris.intersection(class_iri for class_iri, _ in native_constraints(prepared))
    assert "AnnotationLayer" in prepared.index.definitions
    assert "terms" in prepared.adapter("AnnotationLayer").json_schema()["properties"]


def test_knowledge_graph_cannot_range_into_characterization_boundary():
    import yaml

    from corpus_structure.semantic.types import PreparationError

    root = Path(__file__).parents[2] / "src/corpus_structure/model/semantic"
    model = yaml.safe_load((root / "characterization.yaml").read_bytes())
    model["classes"]["GraphEntityWithPrivateCharacterization"] = {
        "is_a": "Entity",
        "attributes": {"private_annotation": {"range": "CharacterizationTerm", "inlined": True}},
    }
    bundle = characterization_inputs(
        SourceBundle("core", (SourceArtifact("core", (root / "core.yaml").read_bytes()),)),
        model_content=yaml.safe_dump(model).encode(),
    )
    with pytest.raises(
        PreparationError, match="knowledge graph property cannot range into a private"
    ):
        prepare_release(bundle)


@pytest.mark.parametrize("field", ["characterization_layer", "characterization_view"])
def test_observation_binding_refuses_characterization_terminal_product(prepared, field):
    from corpus_structure.core.method import UnitRef, UnitResult
    from corpus_structure.core.vocab import ObservationOutcome, TaskUnitType
    from corpus_structure.semantic.observations import bind_result

    body = layer_payload(prepared)
    layer = validate_layer(prepared, body)
    view = validate_view(
        prepared,
        {
            "format": "enriched-document-view-v1",
            "base_document": body["base_document"],
            "release_id": prepared.release_id,
            "source_scope": body["source_scope"],
            "profile": "source_only",
            "layers": [],
            "coverage": [],
        },
        {},
    )
    products: dict[str, Any] = {field: layer if field == "characterization_layer" else view}
    result = UnitResult(
        ref=UnitRef(TaskUnitType.RUN, 1, "run:1"),
        outcome=ObservationOutcome.PRODUCED,
        **products,
    )
    with pytest.raises(ValueError, match="protected characterization completion"):
        bind_result(
            prepared,
            source="source",
            method="characterize",
            operation_version="1",
            configuration_hash="configuration",
            input_hash="input",
            invocation_key="invoke",
            result=result,
        )


def test_new_rule_release_reuses_exact_old_native_layer_without_relabeling(prepared):
    import yaml

    from corpus_structure.semantic.characterization import LayerReport, decode_view
    from corpus_structure.semantic.identity import canonical_bytes

    root = Path(__file__).parents[2] / "src/corpus_structure/model/semantic"
    model = yaml.safe_load((root / "characterization.yaml").read_bytes())
    model["classes"]["ToyRuleUsingRetainedNative"] = {
        "is_a": "CharacterizationConstructionBasis",
        "attributes": {
            "rule_id": {"required": True, "equals_string": "toy:retained-native-v1"},
            "external_premises": {
                "range": "CharacterizationQualifiedReference",
                "inlined": True,
                "multivalued": True,
                "required": True,
                "minimum_cardinality": 1,
            },
        },
    }
    current = prepare_release(
        characterization_inputs(
            SourceBundle("core", (SourceArtifact("core", (root / "core.yaml").read_bytes()),)),
            model_content=yaml.safe_dump(model).encode(),
        )
    )
    assert current.release_id != prepared.release_id
    native_body = layer_payload(prepared)
    native_body["annotations"] = [
        {
            "local_id": "retained-parse",
            "family": "scope",
            "kind": "native_dependency",
            "vocabulary": "native-parser",
            "status": "native_evidence",
            "native_scheme": "parser-v1",
            "native_label": "nsubj",
            "occurrences": [native_body["occurrences"][0]["local_id"]],
            "provenance": ["original-model-invocation"],
        }
    ]
    native = validate_layer(prepared, native_body)
    native_pin = native.reference(8)
    original_bytes = native.content
    construction_body = layer_payload(current)
    construction_body["dependencies"] = [native_pin.values()]
    construction_body["operation"]["required_layers"] = [native_pin.values()]
    construction_body["roles"] = [
        {
            "local_id": "body-attachment",
            "family": "scope",
            "owner": "forall",
            "member": "p",
            "role": "body",
            "scheme": "toy",
            "basis": {
                "kind": "released_construction",
                "status": "witnessed",
                "rule_id": "toy:retained-native-v1",
                "external_premises": [
                    {
                        "layer": native_pin.values(),
                        "local_id": "retained-parse",
                    }
                ],
            },
        }
    ]
    with pytest.raises(ValueError, match="own archived semantic release"):
        validate_layer(current, construction_body, dependencies={native_pin: native})
    construction = validate_layer(
        current,
        construction_body,
        dependencies={native_pin: native},
        releases={prepared.release_id: prepared},
    )
    construction_pin = construction.reference(9)
    layers = {native_pin: native, construction_pin: construction}
    view_body = {
        "format": "enriched-document-view-v1",
        "base_document": native_body["base_document"],
        "release_id": current.release_id,
        "source_scope": native_body["source_scope"],
        "profile": "scope",
        "layers": [native_pin.values(), construction_pin.values()],
        "coverage": native_body["coverage"],
    }
    releases = {prepared.release_id: prepared}
    view = validate_view(current, view_body, layers, releases=releases)
    assert decode_view(current, view.content, layers, releases=releases).content == view.content
    assert native.content == original_bytes
    assert native.reference(8) == native_pin
    assert native.payload["release_id"] == prepared.release_id
    assert native.payload["annotations"][0]["provenance"] == ["original-model-invocation"]
    assert construction.payload["roles"][0]["basis"]["rule_id"] == "toy:retained-native-v1"
    with pytest.raises(ValueError, match="own archived semantic release"):
        validate_view(current, view_body, layers)
    with pytest.raises(ValueError, match="another semantic release"):
        validate_layer(
            prepared,
            construction.payload,
            dependencies=layers,
            releases={current.release_id: current},
        )
    malformed_pin = ProductReference(native_pin.task_id, "wrong-layer-key", native.content_digest)
    malformed_dependency = construction.payload
    malformed_dependency["dependencies"] = [malformed_pin.values()]
    with pytest.raises(ValueError, match="exact dependency closure"):
        validate_layer(
            current,
            malformed_dependency,
            dependencies={malformed_pin: native},
            releases=releases,
        )
    malformed_view = {**view_body, "layers": [malformed_pin.values()]}
    with pytest.raises(ValueError, match="malformed pin"):
        validate_view(current, malformed_view, {malformed_pin: native}, releases=releases)
    # A newer release's rule never gains authority inside an older layer.
    old_with_future_rule = native.payload
    old_with_future_rule["roles"] = [
        {
            "local_id": "future-rule-in-old-layer",
            "family": "scope",
            "owner": "forall",
            "member": "p",
            "role": "body",
            "scheme": "toy",
            "basis": {
                "kind": "released_construction",
                "status": "witnessed",
                "rule_id": "toy:retained-native-v1",
                "premises": ["p"],
            },
        }
    ]
    with pytest.raises(ValueError, match="released attachment rule"):
        validate_layer(prepared, old_with_future_rule, releases={current.release_id: current})
    # A matching digest cannot turn another base document into a valid dependency.
    wrong_body = native.payload
    wrong_body["base_document"]["task_id"] = 99
    wrong = LayerReport(canonical_bytes(wrong_body))
    wrong_pin = wrong.reference(10)
    bad = construction.payload
    bad["dependencies"] = [wrong_pin.values()]
    bad["operation"]["required_layers"] = [wrong_pin.values()]
    bad["roles"][0]["basis"]["external_premises"][0]["layer"] = wrong_pin.values()
    with pytest.raises(ValueError, match="wrong-source"):
        validate_layer(current, bad, dependencies={wrong_pin: wrong}, releases=releases)
    # The shared v1 engine does not reinterpret an unsupported archived format.
    incompatible_body = native.payload
    incompatible_body["format"] = "characterization-layer-v2"
    incompatible = LayerReport(canonical_bytes(incompatible_body))
    incompatible_pin = incompatible.reference(11)
    bad = construction.payload
    bad["dependencies"] = [incompatible_pin.values()]
    with pytest.raises(ValueError, match="unsupported characterization layer contract"):
        validate_layer(
            current, bad, dependencies={incompatible_pin: incompatible}, releases=releases
        )


def test_packed_choice_site_keeps_parent_shared_and_unresolved_explicit(prepared):
    payload = layer_payload(prepared)
    payload["terms"].append(
        dict(
            local_id="packed",
            family="scope",
            kind="predicate",
            vocabulary="logic",
            value="packed",
            status="interpreted",
            children=[dict(role="body", choice_group="site", structural=True)],
        )
    )
    payload["choices"] = [
        dict(
            local_id="site",
            family="scope",
            compatibility="exclusive",
            members=[dict(local_id="left", root="not_all"), dict(local_id="right", root="all_not")],
        )
    ]
    report = validate_layer(prepared, payload)
    unresolved = project_reading(report, "packed")
    assert unresolved["outcome"] == "partial"
    assert unresolved["unresolved_sites"] == [
        dict(owner="packed", role="body", choice_group="site")
    ]
    assert [t["local_id"] for t in unresolved["terms"]] == ["packed"]
    selected = project_reading(report, "packed", choices=["left"])
    assert selected["outcome"] == "complete"
    assert "not_all" in {t["local_id"] for t in selected["terms"]}
    assert "all_not" not in {t["local_id"] for t in selected["terms"]}
    with pytest.raises(ValueError, match="incompatible"):
        project_reading(report, "packed", choices=["left", "right"])
    payload["choices"][0]["members"][0]["root"] = "packed"
    with pytest.raises(ValueError, match="cycle"):
        validate_layer(prepared, payload)


def test_upstream_choice_citation_does_not_select_it(prepared):
    from corpus_structure.semantic.characterization import AnnotationReference

    upstream = layer_payload(prepared)
    upstream["choices"] = [
        dict(
            local_id="upstream",
            family="scope",
            compatibility="exclusive",
            members=[dict(local_id="left", root="not_all"), dict(local_id="right", root="all_not")],
        )
    ]
    report = validate_layer(prepared, upstream)
    pin = report.reference(99)
    downstream = layer_payload(prepared)
    downstream["dependencies"] = [pin.values()]
    downstream["terms"][0]["external_premises"] = [dict(layer=pin.values(), local_id="left")]
    downstream["terms"][0]["required_external_choices"] = [
        dict(layer=pin.values(), local_id="left")
    ]
    result = validate_layer(prepared, downstream, dependencies={pin: report})
    root = downstream["terms"][0]["local_id"]
    with pytest.raises(ValueError, match="unselected qualified"):
        project_reading(result, root, dependencies={pin: report})
    reading = project_reading(
        result,
        root,
        dependencies={pin: report},
        external_choices=[AnnotationReference(pin, "left")],
    )
    assert reading["external_choices"] == [dict(layer=pin.values(), local_id="left")]
    with pytest.raises(ValueError, match="incompatible"):
        project_reading(
            result,
            root,
            dependencies={pin: report},
            external_choices=[AnnotationReference(pin, "left"), AnnotationReference(pin, "right")],
        )


def test_formal_recognized_coordinates_do_not_claim_literal_correspondence(prepared):
    payload = layer_payload(prepared)
    parent = payload["occurrences"][0]["local_id"]
    payload["annotations"] = [
        dict(
            local_id="input",
            family="scope",
            kind="formal.input",
            vocabulary="formal",
            status="native_evidence",
            occurrences=[parent],
            formal_input=dict(
                parent_occurrence=parent,
                representation="recognized_latex",
                text=r"\alpha",
                original_text="all",
                grammar="fixture",
                start_symbol="expression",
                macro_identity="none",
                syntax_outcome="complete",
                interpretation_outcome="not_requested",
                correspondence=[
                    dict(
                        input_start=0,
                        input_end=6,
                        relation="contained_in_atom",
                        source_occurrences=[parent],
                    )
                ],
            ),
        ),
        dict(
            local_id="symbol",
            family="scope",
            kind="formal.token",
            vocabulary="formal",
            status="native_evidence",
            occurrences=[parent],
            formal=dict(input_id="input", node_kind="token", rule="SYMBOL", start=0, end=6),
        ),
    ]
    validate_layer(prepared, payload)
    cast(dict[str, Any], payload["annotations"][0]["formal_input"])["correspondence"][0][
        "relation"
    ] = "exact"
    with pytest.raises(ValueError, match="differs from literal"):
        validate_layer(prepared, payload)


def test_primary_read_uses_frozen_layers_and_refuses_unexamined_native_source(prepared):
    from types import SimpleNamespace

    from corpus_structure.semantic.characterization import select_primary_layers

    body = layer_payload(prepared)
    report = validate_layer(prepared, body)
    view = SimpleNamespace(
        ref=SimpleNamespace(id=11, projection_digest="b" * 64),
        text="all",
        pieces=[dict(kind="native_text", item_ref="#/texts/0", start=0, end=3)],
    )
    pin = report.reference(9)
    assert select_primary_layers({pin: report}, view, families=["scope"]) == {pin: report}
    with pytest.raises(ValueError, match="missing or incomplete"):
        select_primary_layers({}, view, families=["scope"])
    body["coverage"][0]["eligible"] = [dict(projection="b" * 64, start=0, end=1)]
    body["coverage"][0]["examined"] = body["coverage"][0]["eligible"]
    partial = validate_layer(prepared, body)
    with pytest.raises(ValueError, match="unexamined"):
        select_primary_layers({partial.reference(10): partial}, view, families=["scope"])


def test_reading_checks_selected_member_support_even_when_root_is_direct(prepared):
    from corpus_structure.semantic.characterization import AnnotationReference

    ancestor = layer_payload(prepared)
    ancestor["terms"].append(
        dict(
            local_id="packed",
            family="scope",
            kind="predicate",
            vocabulary="logic",
            value="packed",
            status="interpreted",
            children=[dict(role="body", choice_group="nested", structural=True)],
        )
    )
    ancestor["choices"] = [
        dict(
            local_id="nested",
            family="scope",
            compatibility="exclusive",
            members=[dict(local_id="nested-left", root="not_all")],
        ),
        dict(
            local_id="outer",
            family="scope",
            compatibility="exclusive",
            members=[dict(local_id="upstream", root="packed")],
        ),
    ]
    upstream = validate_layer(prepared, ancestor)
    pin = upstream.reference(101)
    body = layer_payload(prepared)
    body["dependencies"] = [pin.values()]
    body["choices"] = [
        dict(
            local_id="local",
            family="scope",
            compatibility="exclusive",
            members=[
                dict(
                    local_id="direct",
                    root="p",
                    required_external_choices=[dict(layer=pin.values(), local_id="upstream")],
                )
            ],
        )
    ]
    report = validate_layer(prepared, body, dependencies={pin: upstream})
    with pytest.raises(ValueError, match="unselected qualified"):
        project_reading(report, "p", choices=["direct"], dependencies={pin: upstream})
    partial = project_reading(
        report,
        "p",
        choices=["direct"],
        dependencies={pin: upstream},
        external_choices=[AnnotationReference(pin, "upstream")],
    )
    assert partial["outcome"] == "partial"
    assert partial["unresolved_sites"] == [
        dict(layer=pin.values(), owner="packed", role="body", choice_group="nested")
    ]
    complete = project_reading(
        report,
        "p",
        choices=["direct"],
        dependencies={pin: upstream},
        external_choices=[
            AnnotationReference(pin, "upstream"),
            AnnotationReference(pin, "nested-left"),
        ],
    )
    assert complete["outcome"] == "complete"
    unrelated = upstream.reference(102)
    with pytest.raises(ValueError, match=r"outside.*dependency closure"):
        project_reading(
            report,
            "p",
            choices=["direct"],
            dependencies={pin: upstream, unrelated: upstream},
            external_choices=[
                AnnotationReference(pin, "upstream"),
                AnnotationReference(unrelated, "nested-left"),
            ],
        )


def test_regional_validation_reuses_exact_dependency_proofs_but_validates_each_new_root(
    prepared, monkeypatch
):
    from types import SimpleNamespace

    import corpus_structure.semantic.characterization as owner
    from corpus_structure.semantic.cpu_execution import CPUExecutionScope
    from corpus_structure.semantic.execution_preparation import RegionalPreparation

    calls = []
    original = owner._shape

    def shape(*args):
        calls.append(args[1])
        return original(*args)

    monkeypatch.setattr(owner, "_shape", shape)
    cpu = CPUExecutionScope(prepared)
    with RegionalPreparation(SimpleNamespace(cpu=cpu)) as regional:
        first = regional.validate_layer(
            prepared,
            layer_payload(prepared),
            dependencies={},
            releases={prepared.release_id: prepared},
        )
        first_pin = first.reference(12)
        second_payload = layer_payload(prepared)
        second_payload["dependencies"] = [first_pin.values()]
        second = regional.validate_layer(
            prepared,
            second_payload,
            dependencies={first_pin: first},
            releases={prepared.release_id: prepared},
        )
        assert len(calls) == 2  # Both new roots validate; the exact dependency is already proven.
        assert second.payload["dependencies"] == [first_pin.values()]
        with pytest.raises(TypeError):
            regional._decoded[first.content_digest]["base_document"]["task_id"] = 22
        wrong = copy.deepcopy(first.payload)
        wrong["outcome"] = "failed"
        with pytest.raises(ValueError, match="exact dependency closure"):
            regional.validate_layer(
                prepared,
                second_payload,
                dependencies={first_pin: owner.LayerReport(owner.canonical_bytes(wrong))},
                releases={prepared.release_id: prepared},
            )
        assert cpu.budget.used_bytes > 0
    assert cpu.budget.used_bytes == 0
    cpu.close()
