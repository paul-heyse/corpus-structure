"""Independent graph, policy and choice criteria on current nominal products."""

import copy
from pathlib import Path
from typing import Any

import pytest

from corpus_structure.semantic.characterization import (
    attachment_policies,
    characterization_inputs,
    occurrence_id,
    project_reading,
    validate_attachment_basis,
    validate_reading_choices,
)
from corpus_structure.semantic.data_product_reference import member_reference
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.types import SourceArtifact, SourceBundle
from semantic.characterization_support import (
    current_inventory,
    current_product,
    literal_inventory,
    product_value,
    selected_graph,
    validate_product,
)
from semantic.characterization_support import (
    graph_source as graph_source,
)
from semantic.characterization_support import (
    prepared as prepared,
)


def test_current_scope_readings_preserve_distinct_bindings_and_immutable_inventory(graph_source):
    product = current_product(graph_source)
    inventory = current_inventory(graph_source, product)
    left = project_reading(inventory, "not_all")
    right = project_reading(inventory, "all_not")
    assert (
        next(row for row in left["terms"] if row["local_id"] == "not_all")["children"][0]["target"]
        == "forall"
    )
    assert (
        next(row for row in right["terms"] if row["local_id"] == "all_not")["children"][2]["target"]
        == "not_p"
    )
    assert len(project_reading(inventory, "or")["terms"]) == 3
    assert member_reference(product.reference, "p").values() == dict(
        product_id=product.semantic_id, member_id="p"
    )
    body = inventory.payload
    body["terms"].clear()
    assert inventory.payload["terms"]


def test_occurrences_depend_on_original_addresses_and_not_analytical_graph(graph_source):
    body = literal_inventory(graph_source)
    extents = body["occurrences"][0]["extents"]
    original = occurrence_id(graph_source.source.value["source"], extents)
    body["terms"].reverse()
    assert current_product(graph_source, body).inventory()["occurrences"][0]["local_id"] == original
    repeated = copy.deepcopy(extents)
    repeated[0]["native_pointer"] = "#/texts/1"
    assert occurrence_id(graph_source.source.value["source"], repeated) != original


@pytest.mark.parametrize(
    "case",
    [
        "dangling",
        "cycle",
        "wrong_projection",
        "unknown_field",
        "coerced_integer",
        "literal_length",
        "binder",
        "nonstructural",
        "incomplete",
        "empty_output",
        "wrong_document",
    ],
)
def test_invalid_current_products_refuse(graph_source, case):
    body = literal_inventory(graph_source)
    if case == "dangling":
        body["terms"][3]["children"][0]["target"] = "missing"
    elif case == "cycle":
        body["terms"][3]["children"][2]["target"] = "not_all"
    elif case == "wrong_projection":
        body["occurrences"][0]["extents"][0]["projection"] = "d" * 64
    elif case == "coerced_integer":
        body["occurrences"][0]["extents"][0]["start"] = "0"
    elif case == "literal_length":
        body["occurrences"][0]["extents"][0]["text"] = "different"
    elif case == "binder":
        body["terms"][3]["children"] = []
    elif case == "nonstructural":
        body["terms"][4]["children"][0]["structural"] = False
    elif case == "incomplete":
        body["coverage"][0]["unexamined"] = body["coverage"][0]["eligible"]
    elif case == "empty_output":
        body["coverage"][0]["outcome"] = "empty"
    value = product_value(graph_source, body)
    if case == "unknown_field":
        value["invented"] = True
    elif case == "wrong_document":
        value["source"]["document"] = "unadmitted:another-original-document"
    with pytest.raises(ValueError):
        validate_product(graph_source, value)


def test_discontinuity_cross_page_overlapping_memberships_and_native_scores():
    case = selected_graph(
        "all    all",
        pieces=[
            dict(kind="native_text", item_ref="#/texts/0", source_field="text", start=0, end=3),
            dict(kind="synthetic_separator", start=3, end=7),
            dict(kind="native_text", item_ref="#/texts/1", source_field="text", start=7, end=10),
        ],
        items=[
            dict(
                self_ref="#/texts/0", label="text", text="all", orig="all", prov=[dict(page_no=3)]
            ),
            dict(
                self_ref="#/texts/1", label="text", text="all", orig="all", prov=[dict(page_no=4)]
            ),
        ],
    )
    body = literal_inventory(case)
    body["occurrences"][0]["extents"][0]["page"] = 3
    body["occurrences"][0]["local_id"] = occurrence_id(
        case.source.value["source"], body["occurrences"][0]["extents"]
    )
    for term in body["terms"]:
        term["occurrences"] = [body["occurrences"][0]["local_id"]]
    other = copy.deepcopy(body["occurrences"][0])
    other["extents"][0].update(page=4, native_pointer="#/texts/1", start=7, end=10)
    other["local_id"] = occurrence_id(case.source.value["source"], other["extents"])
    body["occurrences"].append(other)
    a, b = [row["local_id"] for row in body["occurrences"]]
    body["annotations"] = [
        dict(
            local_id=key,
            family="scope",
            kind="group",
            vocabulary="literal-native",
            status="native_evidence",
            occurrences=[a, b],
            provenance=["literal-model"],
            scores=[
                dict(
                    scheme="native-score",
                    meaning="unnormalized score",
                    value=dict(kind="float", hexadecimal="0x1.8000000000000p-1"),
                )
            ],
        )
        for key in ("g", "h")
    ]
    body["memberships"] = [
        dict(
            local_id=key,
            family="scope",
            group=group,
            member="p",
            role="fragment",
            scope="source",
            structural=False,
            occurrences=[a, b],
        )
        for key, group in (("m1", "g"), ("m2", "h"))
    ]
    body["roles"] = [
        dict(
            local_id="role",
            family="scope",
            owner="g",
            member="p",
            role="subject",
            scheme="dependency",
            occurrences=[b, a],
            basis=dict(
                kind="native_prediction",
                status="recorded",
                native_scheme="literal-parser",
                native_label="nsubj",
            ),
        )
    ]
    result = current_product(case, body).inventory()
    assert result["roles"][0]["occurrences"] == (b, a)
    assert result["annotations"][0]["scores"][0]["value"] == dict(
        kind="float", hexadecimal="0x1.8000000000000p-1"
    )
    assert result["annotations"][0]["occurrences"] == (a, b)


def test_declared_attachment_policy_rejects_model_promotion_and_missing_premises(graph_source):
    body = literal_inventory(graph_source)
    role: dict[str, Any] = dict(
        local_id="role",
        family="scope",
        owner="forall",
        member="p",
        role="body",
        scheme="logic",
        occurrences=[],
        basis=dict(kind="contextual_proposal", status="witnessed"),
    )
    body["roles"] = [role]
    with pytest.raises(ValueError):
        current_product(graph_source, body)
    basis: dict[str, Any] = dict(kind="released_construction", status="witnessed", rule_id="r1")
    role["basis"] = basis
    with pytest.raises(ValueError):
        current_product(graph_source, body)
    basis["premises"] = ["p"]
    with pytest.raises(ValueError, match="released attachment rule"):
        current_product(graph_source, body)


def test_analytical_alternatives_require_explicit_compatible_choices(graph_source):
    body = literal_inventory(graph_source)
    body["choices"] = [
        dict(
            local_id="choice",
            family="scope",
            compatibility="unknown",
            members=[dict(local_id="a", root="not_all"), dict(local_id="b", root="all_not")],
        )
    ]
    inventory = current_inventory(graph_source, current_product(graph_source, body))
    assert validate_reading_choices(inventory.payload, ("a",)) == ("a",)
    for selected in (("a", "b"), ("missing",)):
        with pytest.raises(ValueError):
            validate_reading_choices(inventory.payload, selected)
    member: dict[str, Any] = body["choices"][0]["members"][0]
    member["required_choices"] = ["b"]
    with pytest.raises(ValueError, match="missing"):
        validate_reading_choices(body, ("a",))


def test_explicit_unknown_and_successful_empty_are_distinct(graph_source):
    body = literal_inventory(graph_source)
    body["terms"] = []
    body["coverage"][0]["outcome"] = "empty"
    product = current_product(graph_source, body)
    assert product.value["coverage"][0]["outcome"] == "empty"
    body["coverage"][0].update(eligible=[], examined=[])
    assert current_product(graph_source, body).inventory()["occurrences"]
    body["outcome"] = "partial"
    body["coverage"][0].update(
        availability="unknown",
        outcome="unknown",
        reason="not examined",
        examined=[],
        unexamined=body["coverage"][0]["eligible"],
    )
    assert (
        current_product(graph_source, body).value["coverage"][0]["outcome"]
        == "unknown"
    )


def test_cross_product_premises_require_exact_dependencies_and_reachable_member(graph_source):
    dependency = current_product(graph_source)
    body = literal_inventory(graph_source)
    body["annotations"] = [
        dict(
            local_id="annotation",
            family="scope",
            kind="construction",
            vocabulary="other-domain",
            status="interpreted",
            occurrences=[body["occurrences"][0]["local_id"]],
            external_premises=[member_reference(dependency.reference, "p").values()],
        )
    ]
    value = product_value(graph_source, body, (dependency,))
    with pytest.raises(ValueError, match="dependencies"):
        validate_product(graph_source, value)
    derived = validate_product(graph_source, value, (dependency,))
    assert derived.inventory()["annotations"][0]["vocabulary"] == "other-domain"
    body["annotations"][0]["external_premises"][0]["member_id"] = "absent"
    with pytest.raises(ValueError, match="dangling"):
        current_product(graph_source, body, (dependency,))


def test_referring_edges_can_cycle_without_a_structural_cycle(graph_source):
    body = literal_inventory(graph_source)
    body["roles"] = [
        dict(
            local_id=key,
            family="scope",
            owner=owner,
            member=member,
            role="discourse_reference",
            scheme="discourse",
            occurrences=[],
            basis=dict(
                kind="native_prediction",
                status="recorded",
                native_scheme="discourse",
                native_label="reference",
            ),
        )
        for key, owner, member in (("forward", "p", "r"), ("backward", "r", "p"))
    ]
    assert len(current_product(graph_source, body).inventory()["roles"]) == 2


def test_released_rule_dispatch_compiles_from_actual_declaration():
    import yaml

    root = Path(__file__).parents[2] / "src/corpus_structure/model/semantic"
    model = yaml.safe_load((root / "characterization.yaml").read_bytes())
    model["classes"]["ToyReleasedAttachment"] = dict(
        is_a="CharacterizationConstructionBasis",
        attributes=dict(
            rule_id=dict(required=True, equals_string="toy:body-v1"),
            premises=dict(range="string", multivalued=True, required=True, minimum_cardinality=2),
        ),
    )
    released = prepare_release(
        characterization_inputs(
            SourceBundle("core", (SourceArtifact("core", (root / "core.yaml").read_bytes()),)),
            model_content=yaml.safe_dump(model).encode(),
        )
    )
    policies = attachment_policies(released)
    basis = dict(
        kind="released_construction", status="witnessed", rule_id="toy:body-v1", premises=["p", "r"]
    )

    def validate(value):
        return validate_attachment_basis(
            value,
            policies,
            lambda name, payload: released.validate_json(name, canonical_bytes(payload)),
        )

    validate(basis)
    with pytest.raises(ValueError):
        validate({**basis, "premises": ["p"]})
    with pytest.raises(ValueError, match="released attachment rule"):
        validate({**basis, "rule_id": "not-released"})


@pytest.mark.parametrize("value", [-0.0, 1e-100, 1e100, 2**90, None])
def test_exact_native_scores_never_depend_on_json_number_rendering(graph_source, value):
    import math

    from corpus_structure.semantic.observations import source_python, source_value

    body = literal_inventory(graph_source)
    body["terms"][0]["scores"] = [
        dict(scheme="native", meaning="native score", value=source_value(value))
    ]
    restored = current_product(graph_source, body).inventory()
    score = source_python(restored["terms"][0]["scores"][0]["value"])
    assert type(score) is type(value) and score == value
    if value == 0.0:
        assert math.copysign(1, score) == math.copysign(1, value)


@pytest.mark.parametrize(
    "value", [dict(kind="float", hexadecimal="nan"), dict(kind="float", hexadecimal="0x1.8p-1")]
)
def test_score_codec_rejects_nonfinite_or_noncanonical_value(graph_source, value):
    body = literal_inventory(graph_source)
    body["terms"][0]["scores"] = [dict(scheme="native", meaning="score", value=value)]
    with pytest.raises(ValueError):
        current_product(graph_source, body)


def test_synthetic_boundary_is_distinct_from_empty_literal_source(graph_source):
    body = literal_inventory(graph_source)
    extent = body["occurrences"][0]["extents"][0]
    extent.update(start=0, end=0, text="", synthetic=True)
    body["occurrences"][0]["local_id"] = occurrence_id(
        graph_source.source.value["source"], [extent]
    )
    for term in body["terms"]:
        term["occurrences"] = [body["occurrences"][0]["local_id"]]
    assert (
        current_product(graph_source, body).inventory()["occurrences"][0]["extents"][0]["synthetic"]
        is True
    )
    extent["synthetic"] = False
    body["occurrences"][0]["local_id"] = occurrence_id(
        graph_source.source.value["source"], [extent]
    )
    for term in body["terms"]:
        term["occurrences"] = [body["occurrences"][0]["local_id"]]
    with pytest.raises(ValueError, match="changes original positioned source"):
        current_product(graph_source, body)


def test_packed_choice_site_keeps_parent_shared_and_unresolved_explicit(graph_source):
    body = literal_inventory(graph_source)
    body["terms"].append(
        dict(
            local_id="packed",
            family="scope",
            kind="predicate",
            vocabulary="literal-logic",
            value="packed",
            status="interpreted",
            occurrences=[],
            children=[dict(role="body", choice_group="site", structural=True)],
        )
    )
    body["choices"] = [
        dict(
            local_id="site",
            family="scope",
            compatibility="exclusive",
            members=[dict(local_id="left", root="not_all"), dict(local_id="right", root="all_not")],
        )
    ]
    inventory = current_inventory(graph_source, current_product(graph_source, body))
    unresolved = project_reading(inventory, "packed")
    assert unresolved["outcome"] == "partial"
    assert unresolved["unresolved_sites"] == [
        dict(owner="packed", role="body", choice_group="site")
    ]
    assert [term["local_id"] for term in unresolved["terms"]] == ["packed"]
    selected = project_reading(inventory, "packed", choices=["left"])
    assert selected["outcome"] == "complete"
    assert "not_all" in {term["local_id"] for term in selected["terms"]}
    assert "all_not" not in {term["local_id"] for term in selected["terms"]}
    with pytest.raises(ValueError, match="incompatible"):
        project_reading(inventory, "packed", choices=["left", "right"])
    body["choices"][0]["members"][0]["root"] = "packed"
    with pytest.raises(ValueError, match="cycle"):
        current_product(graph_source, body)


def test_upstream_choice_citation_does_not_select_it(graph_source):
    body = literal_inventory(graph_source)
    body["choices"] = [
        dict(
            local_id="upstream",
            family="scope",
            compatibility="exclusive",
            members=[dict(local_id="left", root="not_all"), dict(local_id="right", root="all_not")],
        )
    ]
    upstream = current_product(graph_source, body)
    pin = upstream.reference
    downstream = literal_inventory(graph_source)
    downstream["terms"][0]["external_premises"] = [member_reference(pin, "left").values()]
    downstream["terms"][0]["required_external_choices"] = [member_reference(pin, "left").values()]
    product = current_product(graph_source, downstream, (upstream,))
    inventory = current_inventory(graph_source, product)
    dependencies = {pin: current_inventory(graph_source, upstream)}
    with pytest.raises(ValueError, match="unselected qualified"):
        project_reading(inventory, "p", dependencies=dependencies)
    reading = project_reading(
        inventory, "p", dependencies=dependencies, external_choices=[member_reference(pin, "left")]
    )
    assert reading["external_choices"] == [member_reference(pin, "left").values()]
    with pytest.raises(ValueError, match="incompatible"):
        project_reading(
            inventory,
            "p",
            dependencies=dependencies,
            external_choices=[member_reference(pin, "left"), member_reference(pin, "right")],
        )


def test_reading_checks_selected_member_support_even_when_root_is_direct(graph_source):
    body = literal_inventory(graph_source)
    body["terms"].append(
        dict(
            local_id="packed",
            family="scope",
            kind="predicate",
            vocabulary="literal-logic",
            value="packed",
            status="interpreted",
            occurrences=[],
            children=[dict(role="body", choice_group="nested", structural=True)],
        )
    )
    body["choices"] = [
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
    upstream = current_product(graph_source, body)
    pin = upstream.reference
    downstream = literal_inventory(graph_source)
    downstream["choices"] = [
        dict(
            local_id="local",
            family="scope",
            compatibility="exclusive",
            members=[
                dict(
                    local_id="direct",
                    root="p",
                    required_external_choices=[member_reference(pin, "upstream").values()],
                )
            ],
        )
    ]
    product = current_product(graph_source, downstream, (upstream,))
    inventory = current_inventory(graph_source, product)
    dependencies = {pin: current_inventory(graph_source, upstream)}
    with pytest.raises(ValueError, match="unselected qualified"):
        project_reading(inventory, "p", choices=["direct"], dependencies=dependencies)
    partial = project_reading(
        inventory,
        "p",
        choices=["direct"],
        dependencies=dependencies,
        external_choices=[member_reference(pin, "upstream")],
    )
    assert partial["outcome"] == "partial"
    assert partial["unresolved_sites"] == [
        dict(layer=pin.values(), owner="packed", role="body", choice_group="nested")
    ]
    complete = project_reading(
        inventory,
        "p",
        choices=["direct"],
        dependencies=dependencies,
        external_choices=[member_reference(pin, "upstream"), member_reference(pin, "nested-left")],
    )
    assert complete["outcome"] == "complete"
    unrelated_facts = literal_inventory(graph_source)
    unrelated_facts["terms"][0]["value"] = "unrelated"
    unrelated_product = current_product(graph_source, unrelated_facts)
    unrelated = unrelated_product.reference
    with pytest.raises(ValueError, match=r"outside.*dependency closure"):
        project_reading(
            inventory,
            "p",
            choices=["direct"],
            dependencies={
                **dependencies,
                unrelated: current_inventory(graph_source, unrelated_product),
            },
            external_choices=[
                member_reference(pin, "upstream"),
                member_reference(unrelated, "nested-left"),
            ],
        )


def test_reading_dependency_must_have_the_same_original_source_and_scope(graph_source):
    foreign = selected_graph("all x")
    upstream = current_product(foreign)
    body = literal_inventory(graph_source)
    product = current_product(graph_source, body, (upstream,))
    with pytest.raises(ValueError, match="different source"):
        project_reading(
            current_inventory(graph_source, product),
            "p",
            dependencies={upstream.reference: current_inventory(foreign, upstream)},
        )


def test_entire_characterization_family_is_private_boundary_not_native_graph(prepared):
    import yaml

    from corpus_structure.semantic.property_constraints import native_constraints
    from corpus_structure.semantic.record_contracts import record_product_classes

    model = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/characterization.yaml"
    declared = set(yaml.safe_load(model.read_bytes())["classes"])
    products = record_product_classes(prepared.definitions)
    assert declared <= products
    private_iris = {
        definition.iri for definition in prepared.definitions if definition.name in declared
    }
    assert not private_iris.intersection(class_iri for class_iri, _ in native_constraints(prepared))
    assert (
        "terms" not in prepared.adapter("DdoPrimaryConstructionProduct").json_schema()["properties"]
    )
    assert (
        "members" in prepared.adapter("DdoPrimaryConstructionProduct").json_schema()["properties"]
    )


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


@pytest.mark.parametrize("eligible", [{}, dict(start=0, end=10)])
def test_complete_coverage_requires_the_eligible_union_but_accepts_partitions(eligible):
    case = selected_graph("allxxxxxxx")
    body = literal_inventory(case)
    projection = case.source.value["source"]["projection"]
    row = body["coverage"][0]
    row["eligible"] = [dict(projection=projection, **eligible)]
    row["examined"] = [dict(projection=projection, start=0, end=5)]
    with pytest.raises(ValueError, match="eligible source scope unexamined"):
        current_product(case, body)
    row["examined"].append(dict(projection=projection, start=5, end=10))
    assert current_product(case, body).value["outcome"] == "complete"


def test_complete_coverage_uses_original_pointer_ancestry_and_page_membership():
    case = selected_graph(
        "allxxxxxxx",
        pieces=[
            dict(kind="native_text", item_ref="#/texts/0", source_field="text", start=0, end=3),
            dict(kind="native_text", item_ref="#/texts/1", source_field="text", start=3, end=10),
        ],
        items=[
            dict(
                self_ref="#/texts/0",
                label="text",
                text="all",
                parent={"$ref": "#/groups/0"},
                prov=[dict(page_no=1)],
            ),
            dict(
                self_ref="#/texts/1",
                label="text",
                text="xxxxxxx",
                parent={"$ref": "#/groups/0"},
                prov=[dict(page_no=2)],
            ),
        ],
    )
    body = literal_inventory(case)
    projection = case.source.value["source"]["projection"]
    row = body["coverage"][0]
    row["eligible"] = [dict(projection=projection, native_pointer="#/groups/0")]
    row["examined"] = [dict(projection=projection, page=1)]
    with pytest.raises(ValueError, match="eligible source scope unexamined"):
        current_product(case, body)
    row["examined"].append(dict(projection=projection, page=2))
    assert current_product(case, body).inventory()["terms"]
    row["eligible"] = [dict(projection=projection, page=1)]
    row["examined"] = [dict(projection=projection, native_pointer="#/texts/0")]
    assert current_product(case, body).inventory()["terms"]


@pytest.mark.parametrize("corruption", ["duplicate", "uncovered_fact_family"])
def test_family_coverage_has_one_row_and_accounts_for_every_analytical_family(
    graph_source, corruption
):
    body = literal_inventory(graph_source)
    if corruption == "duplicate":
        body["coverage"].append(dict(body["coverage"][0]))
        match = "repeats family coverage"
    else:
        body["coverage"][0]["family"] = "another_family"
        match = "analytical family lacks declared coverage"
    with pytest.raises(ValueError, match=match):
        current_product(graph_source, body)


@pytest.mark.parametrize("site", ["term", "basis"])
@pytest.mark.parametrize("member", ["p", "annotation", "group", "occurrence", None])
def test_required_external_choices_are_actual_packed_alternatives(graph_source, site, member):
    body = literal_inventory(graph_source)
    body["annotations"] = [
        dict(
            local_id="annotation",
            family="scope",
            kind="construction",
            vocabulary="literal",
            status="interpreted",
            occurrences=[body["occurrences"][0]["local_id"]],
        )
    ]
    body["choices"] = [
        dict(
            local_id="group",
            family="scope",
            compatibility="exclusive",
            members=[dict(local_id="left", root="not_all"), dict(local_id="right", root="all_not")],
        )
    ]
    upstream = current_product(graph_source, body)
    downstream = literal_inventory(graph_source)
    if member == "occurrence":
        member = body["occurrences"][0]["local_id"]
    ref = dict(
        product_id=upstream.semantic_id, **(dict(member_id=member) if member is not None else {})
    )
    if site == "term":
        downstream["terms"][0]["required_external_choices"] = [ref]
    else:
        downstream["roles"] = [
            dict(
                local_id="role",
                family="scope",
                owner="p",
                member="r",
                role="reference",
                scheme="literal",
                occurrences=[],
                basis=dict(
                    kind="native_prediction",
                    status="recorded",
                    native_scheme="literal",
                    native_label="reference",
                    required_external_choices=[ref],
                ),
            )
        ]
    with pytest.raises(ValueError):
        current_product(graph_source, downstream, (upstream,))
    ref["member_id"] = "left"
    assert current_product(graph_source, downstream, (upstream,)).inventory()["terms"]


def test_current_occurrences_cannot_escape_the_exact_frozen_source_range():
    case = selected_graph("allxxxxxxx", selectors=[dict(start=0, end=5)])
    body = literal_inventory(case)
    assert current_product(case, body).inventory()["occurrences"]
    extent = body["occurrences"][0]["extents"][0]
    extent.update(start=6, end=8, text="xx")
    old = body["occurrences"][0]["local_id"]
    key = occurrence_id(case.source.value["source"], [extent])
    body["occurrences"][0]["local_id"] = key
    for term in body["terms"]:
        term["occurrences"] = [key if value == old else value for value in term["occurrences"]]
    with pytest.raises(ValueError, match="original positioned source"):
        current_product(case, body)


def test_complete_coverage_conserves_unprojected_native_atom_identity():
    case = selected_graph(
        "all",
        items=[
            dict(self_ref="#/texts/0", label="text", text="all"),
            dict(
                self_ref="#/formula/0", label="formula", text="", orig="x=1", prov=[dict(page_no=1)]
            ),
            dict(
                self_ref="#/formula/1", label="formula", text="", orig="y=2", prov=[dict(page_no=2)]
            ),
        ],
    )
    body = literal_inventory(case)
    projection = case.source.value["source"]["projection"]
    row = body["coverage"][0]
    row["eligible"] = [dict(projection=projection, native_pointer="#/formula/0")]
    row["examined"] = [dict(projection=projection, native_pointer="#/formula/1")]
    with pytest.raises(ValueError, match="eligible source scope unexamined"):
        current_product(case, body)
    row["examined"] = [dict(projection=projection, page=1)]
    assert current_product(case, body).inventory()["terms"]


def test_unknown_pointer_ancestry_cannot_prove_eligible_scope_was_examined():
    case = selected_graph(
        "allxxx",
        pieces=[
            dict(kind="native_text", item_ref="#/texts/0", source_field="text", start=0, end=3),
            dict(kind="native_text", item_ref="#/texts/1", source_field="text", start=3, end=6),
        ],
        items=[
            dict(self_ref="#/texts/0", label="text", text="all", parent={"$ref": "#/groups/0"}),
            dict(self_ref="#/texts/1", label="text", text="xxx", parent={"$ref": "#/unavailable"}),
        ],
    )
    body = literal_inventory(case)
    projection = case.source.value["source"]["projection"]
    row = body["coverage"][0]
    row["eligible"] = [dict(projection=projection, native_pointer="#/groups/0")]
    row["examined"] = [dict(projection=projection, native_pointer="#/texts/0")]
    with pytest.raises(ValueError, match="eligible source scope unexamined"):
        current_product(case, body)
    row["examined"] = [dict(projection=projection)]
    assert current_product(case, body).inventory()["terms"]
