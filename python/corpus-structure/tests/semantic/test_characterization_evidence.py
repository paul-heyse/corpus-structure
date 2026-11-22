"""Independent invalid populations and support mutations for shared evidence guards."""

from copy import deepcopy
from typing import Any

import pytest

from corpus_structure.semantic.characterization import _validate_construction_support
from corpus_structure.semantic.characterization_evidence import (
    validate_formal_normalization,
    validate_formal_positions,
)
from corpus_structure.semantic.native_source_view import thaw_native
from semantic.characterization_evidence_support import (
    EVIDENCE_MUTATIONS as EVIDENCE_MUTATIONS,
)
from semantic.characterization_evidence_support import (
    SUPPORT_MUTATIONS as SUPPORT_MUTATIONS,
)
from semantic.characterization_evidence_support import (
    evidence_rows as evidence_rows,
)
from semantic.characterization_evidence_support import (
    mutate_evidence as mutate_evidence,
)
from semantic.characterization_evidence_support import (
    mutate_witness as mutate_witness,
)
from semantic.characterization_evidence_support import (
    witness_rows as witness_rows,
)


def _evidence_body() -> dict[str, Any]:
    occurrences = [
        dict(
            local_id=key,
            extents=[
                dict(
                    projection="p",
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
    indexes = {
        name: {row["local_id"]: row for row in body[name]}
        for name in ("annotations", "occurrences")
    }
    validate_formal_positions(indexes)
    validate_formal_normalization(indexes["annotations"])


@pytest.fixture(scope="module")
def navigation_product():
    from annotation_support import ControlledPipeline, selected_item
    from methods.navigation_fixture import source_primary_products

    from corpus_structure.ingest.annotations import AnnotationProfile
    from corpus_structure.semantic.sentence_partitions import construction_annotation_reference

    controlled = ControlledPipeline()
    text = "Table 5.1 (numbering namespace: Main)"
    request, _source, frame, _context = selected_item(
        controlled, text, start=0, block_id="#/texts/1"
    )
    # Controlled columns, without inference or a provider execution claim.
    from unittest.mock import patch

    from corpus_structure.ingest.annotations import annotate

    profile = AnnotationProfile(execution_profile=controlled.selection().native.fingerprint)
    with patch("corpus_structure.ingest.annotations.pipeline", return_value=controlled):
        (annotation,) = annotate((request,), profile)
    primary = source_primary_products(frame, (annotation,), profile=profile)
    native = primary.native
    assert native is not None
    token = next(row for row in native.inventory("token"))
    body = thaw_native(primary.construction.value)
    navigation = next(
        packet["body"]
        for packet in body["members"]
        if packet["body"].get("navigation", {}).get("source_labels")
    )
    reference = construction_annotation_reference(token["block_id"], "token", token["ordinal"])
    navigation["navigation"]["native_tokens"] = [dict(name="subject", index=0)]
    navigation["external_premises"] = []
    body["annotation_support"].extend(
        dict(owner=navigation["local_id"], use=use, position=0, target=reference)
        for use in ("navigation_token", "external_premise")
    )
    return primary, body, navigation["local_id"]


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
def test_navigation_source_and_native_premise_conservation(navigation_product, mutation):
    from corpus_structure.semantic.construction_products import validate_construction_product

    primary, original, local_id = navigation_product
    body = deepcopy(original)
    annotation = next(
        packet["body"] for packet in body["members"] if packet["member_id"] == local_id
    )
    navigation = annotation["navigation"]
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
        body["annotation_support"] = [
            row
            for row in body["annotation_support"]
            if (row["owner"], row["use"]) != (local_id, "external_premise")
        ]

    def validate():
        return validate_construction_product(
            primary.construction.prepared,
            primary.construction.model,
            body,
            primary.source,
            (primary.formal, primary.native),
            subject_context=primary.context,
        )

    if mutation is None:
        validate()
    else:
        with pytest.raises(ValueError):
            validate()


def test_valid_formal_evidence_and_synthetic_partition():
    body = _evidence_body()
    _validate(body)
    root = body["annotations"][0]["formal_input"]
    root["text"] += " "
    root["correspondence"].append(
        dict(input_start=3, input_end=4, relation="synthetic", source_occurrences=[], boundary=3)
    )
    _validate(body)


@pytest.mark.parametrize("mutation", EVIDENCE_MUTATIONS)
def test_invalid_formal_evidence_is_refused(mutation):
    body = _evidence_body()
    mutate_evidence(body, mutation)
    with pytest.raises(ValueError):
        _validate(body)


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
