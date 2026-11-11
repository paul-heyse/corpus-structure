"""Independent invalid populations and support mutations for shared evidence guards."""

from copy import deepcopy

import pytest

from corpus_structure.semantic.characterization import _validate_construction_support
from corpus_structure.semantic.characterization_evidence import validate_evidence


def evidence_rows(occurrences):
    parent = occurrences[0]["local_id"]
    surface = "".join(e["text"] for e in occurrences[0]["extents"])
    run = dict(
        local_id="native-run",
        provider="fixture",
        profile="native",
        model="fixture",
        model_version="1",
        runtime_version="1",
        configuration="fixture",
        configuration_codec="spacy-config-v1",
        configuration_digest="a" * 64,
        layout_recipe="fixture",
        layout_digest="b" * 64,
        text_digest="c" * 64,
    )
    annotations = [
        dict(local_id="container", kind="native.block"),
        dict(
            local_id="token",
            kind="native.token",
            occurrences=[parent],
            native_token=dict(
                index=0,
                container="container",
                native_run="native-run",
                text=surface,
                whitespace="",
                space=False,
                source_role="prose",
                native_head=0,
                head_index_base=0,
            ),
        ),
        dict(
            local_id="formal-input",
            kind="formal.input",
            occurrences=[parent],
            formal_input=dict(
                parent_occurrence=parent,
                representation="normalized_latex",
                text=surface,
                original_text=surface,
                normalization_recipe="fixture-normalization-1",
                grammar="fixture",
                start_symbol="formula",
                macro_identity="none",
                syntax_outcome="complete",
                interpretation_outcome="not_requested",
                correspondence=[
                    dict(
                        input_start=0,
                        input_end=len(surface),
                        relation="exact",
                        source_occurrences=[parent],
                    )
                ],
            ),
        ),
        dict(
            local_id="symbol",
            kind="formal.symbol",
            formal=dict(
                input_id="formal-input", node_kind="rule", rule="symbol", start=0, end=len(surface)
            ),
        ),
        dict(
            local_id="formal-token",
            kind="formal.token",
            formal=dict(
                input_id="formal-input",
                node_kind="token",
                rule="NUMBER",
                start=0,
                end=1,
                symbol_parent="symbol",
                normalized=dict(kind="decimal", domain_status="valid", value="1.25e-2"),
            ),
        ),
    ]
    for row in annotations:
        row.update(family="syntax", vocabulary="fixture", status="native_evidence")
    return dict(native_runs=[run], annotations=annotations)


EVIDENCE_MUTATIONS = (
    "missing_token",
    "missing_token_source",
    "wrong_token_text",
    "foreign_container",
    "foreign_sentence",
    "duplicate_index",
    "missing_head_scheme",
    "foreign_head",
    "missing_symbol",
    "foreign_symbol_parent",
    "symbol_parent_cycle",
    "symbol_outside_parent",
    "nonfinite_decimal",
    "invalid_decimal",
    "missing_recipe",
    "wrong_original",
    "partition_gap",
    "partition_overlap",
    "partition_tail",
    "foreign_source",
    "synthetic_boundary",
)


def mutate_evidence(body, mutation):
    rows = {a["local_id"]: a for a in body["annotations"]}
    token, formal = rows["token"]["native_token"], rows["formal-token"]["formal"]
    root = rows["formal-input"]["formal_input"]
    if mutation == "missing_token":
        rows["token"].pop("native_token")
    elif mutation == "missing_token_source":
        rows["token"].pop("occurrences")
    elif mutation == "wrong_token_text":
        token["text"] = "invented"
    elif mutation == "foreign_container":
        token["container"] = "formal-input"
    elif mutation == "foreign_sentence":
        token["sentence"] = "container"
    elif mutation == "duplicate_index":
        duplicate = deepcopy(rows["token"])
        duplicate["local_id"] = "duplicate-token"
        body["annotations"].append(duplicate)
    elif mutation == "missing_head_scheme":
        token.pop("head_index_base")
    elif mutation == "foreign_head":
        token["native_head"] = 99
    elif mutation == "missing_symbol":
        rows["symbol"].pop("formal")
    elif mutation == "foreign_symbol_parent":
        formal["symbol_parent"] = "container"
    elif mutation == "symbol_parent_cycle":
        rows["symbol"]["formal"]["symbol_parent"] = "symbol"
    elif mutation == "symbol_outside_parent":
        rows["symbol"]["formal"]["start"] = 1
    elif mutation == "nonfinite_decimal":
        formal["normalized"]["value"] = "NaN"
    elif mutation == "invalid_decimal":
        formal["normalized"]["value"] = "a-number"
    elif mutation == "missing_recipe":
        root.pop("normalization_recipe")
    elif mutation == "wrong_original":
        root["original_text"] = "different"
    elif mutation == "partition_gap":
        root["correspondence"][0]["input_start"] = 1
    elif mutation == "partition_overlap":
        root["correspondence"].append(deepcopy(root["correspondence"][0]))
    elif mutation == "partition_tail":
        root["correspondence"][0]["input_end"] -= 1
    elif mutation == "foreign_source":
        root["correspondence"][0].update(
            relation="normalized", source_occurrences=[body["occurrences"][1]["local_id"]]
        )
    elif mutation == "synthetic_boundary":
        root["correspondence"][0].update(relation="synthetic", source_occurrences=[], boundary=99)
    else:
        raise AssertionError(mutation)


def _evidence_body():
    occurrences = [
        dict(
            local_id=key,
            extents=[
                dict(
                    projection="p",
                    source_view_id=1,
                    native_pointer=pointer,
                    start=start,
                    end=start + 3,
                    text="x=1",
                    synthetic=False,
                )
            ],
        )
        for key, pointer, start in (("source", "#/texts/0", 0), ("foreign", "#/texts/1", 4))
    ]
    return dict(occurrences=occurrences, **evidence_rows(occurrences))


def _validate(body):
    validate_evidence(
        body,
        {
            name: {row["local_id"]: row for row in body[name]}
            for name in ("annotations", "occurrences")
        },
    )


@pytest.mark.parametrize(
    "mutation",
    (
        None,
        "missing_payload",
        "duplicate_role",
        "foreign_source",
        "missing_top_source",
        "label_text",
        "missing_premise",
    ),
)
def test_navigation_source_and_native_premise_conservation(mutation):
    body = _evidence_body()
    native = dict(
        layer=dict(task_id=1, product_key="annotation_layer", content_digest="a" * 64),
        local_id="native-token",
    )
    navigation = dict(
        codec="source-navigation-v1",
        kind="artifact_mention",
        pointer="#/texts/0",
        status="complete",
        roles=[dict(role="subject", occurrences=["source"])],
        source_labels=[dict(kind="numbering_namespace", value="x=1", occurrences=["source"])],
        native_tokens=[dict(name="subject", index=0, native_node=native)],
    )
    annotation = dict(
        local_id="navigation",
        kind="construction.navigation",
        family="construction.navigation",
        occurrences=["source"],
        external_premises=[native],
        navigation=navigation,
    )
    body["annotations"].append(annotation)
    if mutation == "missing_payload":
        annotation.pop("navigation")
    elif mutation == "duplicate_role":
        navigation["roles"].append(deepcopy(navigation["roles"][0]))
    elif mutation == "foreign_source":
        navigation["roles"][0]["occurrences"] = ["missing-source"]
    elif mutation == "missing_top_source":
        annotation["occurrences"] = []
    elif mutation == "label_text":
        navigation["source_labels"][0]["value"] = "invented"
    elif mutation == "missing_premise":
        annotation["external_premises"] = []
    if mutation is None:
        _validate(body)
    else:
        with pytest.raises(ValueError, match="navigation"):
            _validate(body)


def test_valid_native_formal_evidence_and_synthetic_partition():
    body = _evidence_body()
    _validate(body)
    root = body["annotations"][2]["formal_input"]
    root["text"] += " "
    root["correspondence"].append(
        dict(input_start=3, input_end=4, relation="synthetic", source_occurrences=[], boundary=3)
    )
    _validate(body)
    body["annotations"][1]["native_token"].update(native_head=0, head_index_base=1)
    _validate(body)  # The native one-based root sentinel has no token target.


@pytest.mark.parametrize("mutation", EVIDENCE_MUTATIONS)
def test_invalid_native_formal_evidence_is_refused(mutation):
    body = _evidence_body()
    mutate_evidence(body, mutation)
    with pytest.raises(ValueError):
        _validate(body)


def witness_rows(body):
    occurrence = body["occurrences"][0]["local_id"]
    body["annotations"].extend(
        [
            dict(
                local_id="construction",
                kind="construction",
                family="syntax",
                vocabulary="fixture",
                status="interpreted",
                rule_id="tc.predication.verbal.v1",
                premises=["production"],
                required_choices=["reading"],
            ),
            dict(
                local_id="production",
                kind="grammar.production",
                family="syntax",
                vocabulary="fixture",
                status="native_evidence",
                native_label="prose__verbal_predication",
                premises=["participant"],
            ),
        ]
    )
    member = next(t for t in body["terms"] if t["local_id"] == "participant")
    member["occurrences"] = [occurrence]
    body["memberships"].append(
        dict(
            local_id="binding",
            group="construction",
            member="participant",
            family="syntax",
            role="predicate",
            order=0,
            structural=False,
            scope="construction",
            occurrences=[occurrence],
            required_choices=["reading"],
        )
    )
    body["roles"] = [
        dict(
            local_id="witness",
            owner="construction",
            member="participant",
            family="syntax",
            role="predicate",
            scheme="fixture",
            occurrences=[occurrence],
            required_choices=["reading"],
            basis=dict(
                kind="released_construction",
                status="witnessed",
                rule_id="tc.predication.verbal.v1",
                construction="construction",
                binding="binding",
                production="production",
                premises=["construction", "binding", "production"],
                choice_refs=["reading"],
            ),
        )
    ]
    return body


SUPPORT_MUTATIONS = (
    "foreign_occurrence",
    "dropped_choices",
    "dropped_basis_choices",
    "dropped_external_choices",
)


def mutate_witness(body, mutation):
    role = body["roles"][0]
    if mutation == "foreign_occurrence":
        role["occurrences"] = [body["occurrences"][1]["local_id"]]
    elif mutation == "dropped_choices":
        role["required_choices"] = []
        role["basis"]["choice_refs"] = []
    elif mutation == "dropped_basis_choices":
        role["basis"]["choice_refs"] = []
    elif mutation == "dropped_external_choices":
        next(row for row in body["annotations"] if row["local_id"] == "construction")[
            "required_external_choices"
        ] = [
            dict(
                layer=dict(task_id=1, product_key="upstream", content_digest="a" * 64),
                local_id="upstream-choice",
            )
        ]
    else:
        raise AssertionError(mutation)


def _validate_witness(body):
    nodes = {
        row["local_id"]: row
        for name in ("annotations", "memberships", "terms")
        for row in body[name]
    }
    _validate_construction_support(
        body["roles"][0],
        nodes,
        dict(
            codec="construction-membership-v1",
            production="prose__verbal_predication",
            roles=["predicate"],
        ),
    )


def test_witness_preserves_exact_member_source_and_choices():
    body = witness_rows(
        dict(
            occurrences=[dict(local_id="source")],
            annotations=[],
            memberships=[],
            terms=[dict(local_id="participant")],
        )
    )
    _validate_witness(body)


@pytest.mark.parametrize("mutation", SUPPORT_MUTATIONS)
def test_witness_refuses_lost_source_or_choice_support(mutation):
    body = witness_rows(
        dict(
            occurrences=[dict(local_id="source"), dict(local_id="foreign")],
            annotations=[],
            memberships=[],
            terms=[dict(local_id="participant")],
        )
    )
    mutate_witness(body, mutation)
    with pytest.raises(ValueError):
        _validate_witness(body)
