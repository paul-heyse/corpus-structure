"""Selected formal product identity and standalone semantic validation."""

from dataclasses import replace

import pytest

from corpus_structure.semantic import formal_products
from corpus_structure.semantic.data_operation_model import BoundRoleMember
from corpus_structure.semantic.formal_products import (
    FormalEvidenceOptions,
    acquired_formal_product,
    validate_formal_product,
)
from corpus_structure.semantic.native_source_view import thaw_native
from semantic.formal_products_support import profile as profile
from semantic.formal_products_support import publication_context, selected


def test_retained_product_cannot_change_selected_identity(profile, monkeypatch):
    source = selected(profile, "Quantity: 2 kg")
    context = publication_context(source)
    product = profile.run(source, FormalEvidenceOptions(), subject_context=context)
    body = thaw_native(product.value)
    member = BoundRoleMember(
        product=product.semantic_id,
        kind_contract=next(
            item.key
            for item in profile.model.identities
            if item.owner == profile.prepared.index.definitions["DdoFormalProduct"].iri
            and item.domain == "kind"
        ),
        subject=context.subject,
        subject_definition=context.subject_definition,
        original_source=context.original_source,
        analyzed_scope=context.analyzed_scope,
        coverage=b"{}",
        support_episodes=(),
        support_evidence=b"{}",
        support_references=(),
    )

    def repeated(*args, **kwargs):
        pytest.fail("selected formal ingress repeated the standalone verifier")

    monkeypatch.setattr(formal_products, "validate_formal_product", repeated)
    acquired = acquired_formal_product(
        profile.prepared,
        body,
        source,
        model=profile.model,
        subject_context=context,
        member=member,
    )
    reacquired = acquired_formal_product(
        profile.prepared,
        body,
        source,
        model=profile.model,
        subject_context=context,
        member=member,
    )
    assert acquired.content == product.content
    assert reacquired.value is acquired.value
    for bad_member in (
        replace(member, product="product:another"),
        replace(member, kind_contract="kind:another"),
    ):
        with pytest.raises(ValueError, match="exact selected native product"):
            acquired_formal_product(
                profile.prepared,
                body,
                source,
                model=profile.model,
                subject_context=context,
                member=bad_member,
            )


def test_standalone_formal_product_checks_member_identity(profile):
    source = selected(profile, "Quantity: 2 kg")
    context = publication_context(source)
    product = profile.run(source, FormalEvidenceOptions(), subject_context=context)
    body = thaw_native(product.value)
    body["members"][0]["member_id"] = "changed-member-identity"

    with pytest.raises(ValueError):
        validate_formal_product(
            profile.prepared, body, source, model=profile.model, subject_context=context
        )
