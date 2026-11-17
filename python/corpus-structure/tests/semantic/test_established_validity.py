"""Retained semantic validation is reused only under its exact original premises."""

from types import SimpleNamespace

import pytest

from corpus_structure.semantic import formal_products
from corpus_structure.semantic.established_validity import (
    ProductValidation,
    bind_product_validation,
)
from corpus_structure.semantic.formal_products import FormalEvidenceOptions, retained_formal_product
from corpus_structure.semantic.identity import canonical_bytes
from semantic.formal_products_support import profile as profile
from semantic.formal_products_support import publication_context, selected


def produced(profile):
    source = selected(profile, "Quantity: 2 kg")
    context = publication_context(source)
    product = profile.run(source, FormalEvidenceOptions(), subject_context=context)
    assert isinstance(product.established_validity, ProductValidation)
    return source, context, product


def selected_member(product, proof):
    return SimpleNamespace(
        member=None,
        product=product.semantic_id,
        support_evidence=canonical_bytes({"product_validation": proof.model_dump(mode="json")}),
    )


def test_exact_native_product_skips_semantics_but_still_decodes(profile, monkeypatch):
    source, context, product = produced(profile)
    proof = bind_product_validation(product, context)
    member = selected_member(product, proof)

    def unexpected(*args, **kwargs):
        pytest.fail("exact original retained product repeated full semantic validation")

    monkeypatch.setattr(formal_products, "validate_formal_product", unexpected)
    body = product.value.model_dump(mode="json", exclude_unset=True)
    retained = retained_formal_product(
        profile.prepared, body, source, model=profile.model, subject_context=context, member=member
    )
    assert retained.content == product.content
    assert retained.semantic_id == product.semantic_id
    with pytest.raises(ValueError):
        retained_formal_product(
            profile.prepared,
            {**body, "outcome": 7},
            source,
            model=profile.model,
            subject_context=context,
            member=member,
        )


@pytest.mark.parametrize(
    "premise", ["revision", "release", "source", "selectors", "context", "body"]
)
def test_changed_established_premise_falls_back_to_full_validation(profile, monkeypatch, premise):
    source, context, product = produced(profile)
    proof = product.established_validity
    changes = {
        "revision": {"validator_revision": "0" * 64},
        "release": {"release_id": "another-producing-release"},
        "source": {"source_json": "{}"},
        "selectors": {"selectors_json": "[]"},
        "context": {"subject_context_json": "{}"},
        "body": {"body_id": "body:" + "0" * 64},
    }
    proof = proof.model_copy(update=changes[premise])
    member = selected_member(product, proof)
    original = formal_products.validate_formal_product
    calls = []

    def full(*args, **kwargs):
        calls.append(True)
        return original(*args, **kwargs)

    monkeypatch.setattr(formal_products, "validate_formal_product", full)
    retained = retained_formal_product(
        profile.prepared,
        product.value.model_dump(mode="json", exclude_unset=True),
        source,
        model=profile.model,
        subject_context=context,
        member=member,
    )
    assert calls == [True]
    assert retained.content == product.content


def test_missing_proof_and_changed_body_cannot_reuse_success(profile, monkeypatch):
    source, context, product = produced(profile)
    calls = []
    original = formal_products.validate_formal_product

    def full(*args, **kwargs):
        calls.append(True)
        return original(*args, **kwargs)

    monkeypatch.setattr(formal_products, "validate_formal_product", full)
    retained_formal_product(
        profile.prepared,
        product.value.model_dump(mode="json", exclude_unset=True),
        source,
        model=profile.model,
        subject_context=context,
    )
    assert calls == [True]
    body = product.value.model_dump(mode="json", exclude_unset=True)
    body["members"][0]["member_id"] = "changed-member-identity"
    with pytest.raises(ValueError):
        retained_formal_product(
            profile.prepared,
            body,
            source,
            model=profile.model,
            subject_context=context,
            member=selected_member(product, product.established_validity),
        )
    assert calls == [True, True]


def test_matching_proof_does_not_relabel_native_product(profile):
    source, context, product = produced(profile)
    member = selected_member(product, product.established_validity)
    member.product = "product:another"
    with pytest.raises(ValueError, match="exact selected native product"):
        retained_formal_product(
            profile.prepared,
            product.value.model_dump(mode="json", exclude_unset=True),
            source,
            model=profile.model,
            subject_context=context,
            member=member,
        )


def test_validation_result_survives_closed_execution_evidence_transport(profile):
    from corpus_structure.semantic.data_operation_execution_evidence import bind_execution_evidence

    _source, context, product = produced(profile)
    proof = bind_product_validation(product, context)
    assert proof is not None
    value = bind_execution_evidence(
        None,
        fence=dict(
            request_id="request:transport",
            generation=1,
            task_id=1,
            attempt=1,
            holder="holder:transport",
        ),
        runtime_id="runtime:transport",
        product_validation_content=proof.model_dump_json().encode(),
    )
    assert value["product_validations"] == [proof.model_dump(mode="json")]
