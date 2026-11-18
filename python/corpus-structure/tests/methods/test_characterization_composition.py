"""Current composition preserves exact products, source selection and weak coverage."""

import pytest
from semantic.construction_products_test_support import profiles as profiles
from semantic.construction_products_test_support import publication_context
from semantic.formal_products_support import selected

from corpus_structure.semantic.data_product_reference import DataProductReference
from corpus_structure.semantic.enriched_document_products import compose_enriched_document
from corpus_structure.semantic.formal_products import FormalEvidenceOptions


def test_source_only_view_preserves_source_without_analytical_coverage(profiles):
    formal, construction = profiles
    source = selected(formal, "All samples are finite.")
    view = compose_enriched_document(
        construction.prepared,
        construction.model,
        (source,),
        (),
        profile="source_only",
        subject_context=publication_context(source, document=True),
    ).value.model_dump(mode="json", exclude_unset=True)
    assert view["sources"] == [source.value]
    assert view["profile"] == "source_only"
    assert view["products"] == view["active"] == view["coverage"] == []


def test_retained_dependency_is_not_an_active_interpretation_or_relabelled_product(profiles):
    formal, construction = profiles
    source = selected(formal, "Not every trial succeeds.")
    context = publication_context(source)
    primary = formal.run(source, FormalEvidenceOptions(), subject_context=context)
    symbolic = construction.run(source, (primary,), subject_context=context)
    original = (primary.content, primary.semantic_id, primary.prepared)
    result = compose_enriched_document(
        construction.prepared,
        construction.model,
        (source,),
        (primary, symbolic),
        active=(DataProductReference(symbolic.semantic_id),),
        subject_context=publication_context(source, document=True),
    ).value.model_dump(mode="json", exclude_unset=True)
    assert result["products"] == [
        DataProductReference(primary.semantic_id).values(),
        DataProductReference(symbolic.semantic_id).values(),
    ]
    assert result["active"] == [DataProductReference(symbolic.semantic_id).values()]
    assert result["coverage"]
    assert all(
        row["products"] == [DataProductReference(symbolic.semantic_id).values()]
        for row in result["coverage"]
    )
    assert (primary.content, primary.semantic_id, primary.prepared) == original
    assert primary.prepared is original[2]
    for active in (
        (DataProductReference(symbolic.semantic_id), DataProductReference(symbolic.semantic_id)),
        (DataProductReference("unselected-product"),),
    ):
        with pytest.raises(ValueError, match="exact subset"):
            compose_enriched_document(
                construction.prepared,
                construction.model,
                (source,),
                (primary, symbolic),
                active=active,
                subject_context=publication_context(source, document=True),
            )
    with pytest.raises(ValueError, match="exact selected dependency"):
        compose_enriched_document(
            construction.prepared,
            construction.model,
            (source,),
            (symbolic,),
            active=(DataProductReference(symbolic.semantic_id),),
            subject_context=publication_context(source, document=True),
        )
    with pytest.raises(ValueError, match="source-only"):
        compose_enriched_document(
            construction.prepared,
            construction.model,
            (source,),
            (primary,),
            profile="source_only",
            subject_context=publication_context(source, document=True),
        )


def test_composition_refuses_an_actual_product_from_an_unselected_source(profiles):
    formal, construction = profiles
    source = selected(formal, "All samples are finite.")
    other = selected(formal, "Every trial succeeds.")
    product = formal.run(other, FormalEvidenceOptions(), subject_context=publication_context(other))
    with pytest.raises(ValueError, match="no retained original source coordinate"):
        compose_enriched_document(
            construction.prepared,
            construction.model,
            (source,),
            (product,),
            active=(DataProductReference(product.semantic_id),),
            subject_context=publication_context(source, document=True),
        )
