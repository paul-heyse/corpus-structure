"""Typed role decoding preserves facts; it supplies no native authentication."""

from copy import deepcopy
from decimal import Decimal

import pytest

from corpus_structure.semantic.data_operation_cpu_basis import (
    CPUInputRole,
    cpu_basis_values,
    cpu_input_basis,
)
from corpus_structure.semantic.data_operation_identity import decode_semantic_value, semantic_value
from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.data_operation_support import (
    AuthoredFactSupportReference,
    ComputationalSupportReference,
    OriginalSourceSupportReference,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.selected_support import ProducerOutputOccurrence


def basis():
    context = SubjectContext(
        "project", "selected", None, b"{}", subject_definition="knowledge-universe"
    )
    original = SubjectContext(
        "project",
        "source",
        "actual-original",
        b'{"start":0}',
        subject_definition="original-source-view",
    )
    source = CPUInputRole(
        "source",
        0,
        1,
        "source-product",
        "source-member",
        "source-kind",
        original,
        dict(
            precise=Decimal("0.1234567890123456789"),
            negative_zero=-0.0,
            unrelated={"kind": "invalid"},
        ),
        (
            ComputationalSupportReference(
                derivation_id="unadmitted:original-episode", admission_use_id="unadmitted:use"
            ),
            OriginalSourceSupportReference(
                admission_id="unadmitted:original", source_reference="unadmitted:document"
            ),
            AuthoredFactSupportReference(
                admission_id="unadmitted:assertion", source_reference="unadmitted:author"
            ),
        ),
        producer_output=ProducerOutputOccurrence(
            member_id=None, role="result", position=0, multiplicity=1
        ),
    )
    member = CPUInputRole(
        "members",
        None,
        1,
        "member-product",
        None,
        "member-kind",
        context,
        {"value": 7},
        (),
        producer_output=None,
    )
    return cpu_input_basis(
        "actual-logical-recipe",
        context,
        (source, member),
        parameters=canonical_bytes(semantic_value({"selection": "exact"})),
        replicate="logical-replicate",
    )


def test_decoder_preserves_full_original_headers_values_contexts_and_support():
    selected = basis()
    before = canonical_bytes(selected)
    grouped, context = cpu_basis_values(
        selected, scalar_roles=("source",), set_roles=("members", "empty")
    )
    source = grouped["source"][0]
    assert context.original_source is None
    assert source.context.original_source == "actual-original"
    assert source.product_id == "source-product" and source.member_id == "source-member"
    assert source.position == 0 and source.multiplicity == 1
    assert source.body["precise"] == Decimal("0.1234567890123456789")
    assert source.body["negative_zero"].hex() == "-0x0.0p+0"
    assert source.body["unrelated"] == {"kind": "invalid"}
    assert {value.kind for value in source.support} == {
        "authored",
        "computation",
        "original-source",
    }
    authored = next(
        value for value in source.support if isinstance(value, AuthoredFactSupportReference)
    )
    assert (authored.admission_id, authored.source_reference) == (
        "unadmitted:assertion",
        "unadmitted:author",
    )
    original = next(
        value for value in source.support if isinstance(value, OriginalSourceSupportReference)
    )
    assert (original.admission_id, original.source_reference) == (
        "unadmitted:original",
        "unadmitted:document",
    )
    computation = next(
        value for value in source.support if isinstance(value, ComputationalSupportReference)
    )
    assert computation.derivation_id == "unadmitted:original-episode"
    assert computation.admission_use_id == "unadmitted:use"
    assert grouped["empty"] == ()  # Decoded grouping adds no coverage/availability assertion.
    assert grouped["members"][0].member_id is None
    assert canonical_bytes(selected) == before


@pytest.mark.parametrize(
    "mutation",
    [
        "unknown-role",
        "multiplicity",
        "boolean-multiplicity",
        "missing-scalar",
        "duplicate",
        "missing-context",
        "extra-header",
        "empty-product",
        "fractional-position",
        "invalid-support",
        "v1",
        "missing-replicate",
    ],
)
def test_decoder_refuses_noncurrent_or_ambiguous_typed_populations(mutation):
    value = deepcopy(decode_semantic_value(basis()))
    row = next(row for row in value["roles"] if row["role"] == "source")
    if mutation == "unknown-role":
        row["role"] = "unrequested"
    elif mutation == "multiplicity":
        row["multiplicity"] = 2
    elif mutation == "boolean-multiplicity":
        row["multiplicity"] = True
    elif mutation == "missing-scalar":
        value["roles"].remove(row)
    elif mutation == "duplicate":
        value["roles"].append(deepcopy(row))
    elif mutation == "missing-context":
        del row["context"]["original_source"]
    elif mutation == "extra-header":
        row["invented_provenance"] = "independent-provider"
    elif mutation == "empty-product":
        row["product_id"] = ""
    elif mutation == "fractional-position":
        row["position"] = 1.0
    elif mutation == "invalid-support":
        row["support"] = None
    elif mutation == "v1":
        value["version"] = "cpu-input-basis-1"
    else:
        del value["replicate"]
    with pytest.raises(ValueError):
        cpu_basis_values(semantic_value(value), scalar_roles=("source",), set_roles=("members",))


def test_decoded_missing_support_never_becomes_invented_authority():
    value = decode_semantic_value(basis())
    source = next(row for row in value["roles"] if row["role"] == "source")
    source["support"] = []
    source["producer_output"] = None
    grouped, _ = cpu_basis_values(
        semantic_value(value), scalar_roles=("source",), set_roles=("members",)
    )
    assert grouped["source"][0].support == ()


def sequence_basis():
    value = decode_semantic_value(basis())
    template = next(row for row in value["roles"] if row["role"] == "members")
    value["roles"] = []
    for position, number in enumerate((0.75, 0.75, -0.25)):
        row = deepcopy(template)
        row.update(
            role="features", position=position, product_id=f"feature-{position}", body=number
        )
        value["roles"].append(row)
    return value


def test_sequence_decoding_preserves_order_repeated_values_and_empty_population():
    grouped, _ = cpu_basis_values(
        semantic_value(sequence_basis()),
        scalar_roles=(),
        set_roles=(),
        sequence_roles=("features", "unobserved"),
    )
    assert tuple(row.body for row in grouped["features"]) == (0.75, 0.75, -0.25)
    assert tuple(row.product_id for row in grouped["features"]) == (
        "feature-0",
        "feature-1",
        "feature-2",
    )
    assert grouped["unobserved"] == ()


@pytest.mark.parametrize("positions", [(1, 0, 2), (0, 2, 3), (0, 0, 2), (None, 1, 2), (0, 1)])
def test_sequence_requires_exact_encountered_contiguous_positions(positions):
    value = sequence_basis()
    for row, position in zip(value["roles"], positions, strict=False):
        row["position"] = position
    if len(positions) != len(value["roles"]):
        value["roles"].pop(1)  # Omitted interior element leaves a genuine position gap.
    with pytest.raises(ValueError, match="contiguous ordered positions"):
        cpu_basis_values(
            semantic_value(value), scalar_roles=(), set_roles=(), sequence_roles=("features",)
        )
