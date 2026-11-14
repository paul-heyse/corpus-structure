"""Independent invalid populations and support mutations for shared evidence guards."""

from copy import deepcopy

import pytest

from corpus_structure.semantic.characterization import _validate_construction_support
from corpus_structure.semantic.characterization_evidence import validate_evidence
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
