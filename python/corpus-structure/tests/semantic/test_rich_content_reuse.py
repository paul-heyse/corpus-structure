"""Rich support references preserve exact canonical meaning."""

import pytest


@pytest.mark.parametrize(
    "record",
    (
        {"kind": "computation", "derivation_id": "derivation:1", "admission_use_id": "use:1"},
        {"kind": "original-source", "admission_id": "admission:1", "source_reference": "source:1"},
        {"kind": "authored", "admission_id": "admission:1", "source_reference": "source:1"},
    ),
)
def test_rich_support_normalization_needs_only_its_exact_reference_fields(monkeypatch, record):
    from corpus_structure.semantic import value_codec
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.rich_knowledge_contracts import (
        DdoRichSelectedMember,
        rich_reference_key,
        rich_support_records,
    )

    def forbid_model():
        raise AssertionError("reference normalization must not acquire a numeric model")

    monkeypatch.setattr(value_codec, "decimal_digit_limit", forbid_model)
    reference = DdoRichSelectedMember.model_validate(
        dict(
            product_id="product:1",
            member_id=None,
            kind_contract="kind:1",
            support_references=[record, record],
        )
    )
    assert rich_support_records(reference.support_references) == [record]
    assert rich_reference_key(reference) == canonical_bytes(["product:1", None, "kind:1", [record]])
