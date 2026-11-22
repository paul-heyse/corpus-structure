"""Selected formal product identity and standalone semantic validation."""

from types import SimpleNamespace

import pytest

from corpus_structure.semantic.formal_products import FormalEvidenceOptions, retained_formal_product
from semantic.formal_products_support import profile as profile
from semantic.formal_products_support import publication_context, selected


def test_retained_product_cannot_change_selected_identity(profile):
    source = selected(profile, "Quantity: 2 kg")
    context = publication_context(source)
    product = profile.run(source, FormalEvidenceOptions(), subject_context=context)
    body = product.value.model_dump(mode="json", exclude_unset=True)
    member = SimpleNamespace(member=None, product=product.semantic_id)

    assert (
        retained_formal_product(
            profile.prepared,
            body,
            source,
            model=profile.model,
            subject_context=context,
            member=member,
        ).content
        == product.content
    )
    member.product = "product:another"
    with pytest.raises(ValueError, match="exact selected native product"):
        retained_formal_product(
            profile.prepared,
            body,
            source,
            model=profile.model,
            subject_context=context,
            member=member,
        )


def test_standalone_formal_product_checks_member_identity(profile):
    source = selected(profile, "Quantity: 2 kg")
    context = publication_context(source)
    product = profile.run(source, FormalEvidenceOptions(), subject_context=context)
    body = product.value.model_dump(mode="json", exclude_unset=True)
    body["members"][0]["member_id"] = "changed-member-identity"

    with pytest.raises(ValueError):
        retained_formal_product(
            profile.prepared, body, source, model=profile.model, subject_context=context
        )
