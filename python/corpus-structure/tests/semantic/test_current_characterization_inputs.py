"""Preparation and scientific kernels used by the current native consumer controls."""

from corpus_structure.semantic.construction_products import PreparedConstructionProfile
from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.formal_evidence import grammar_identity
from corpus_structure.semantic.formal_products import FormalEvidenceOptions, prepare_formal_evidence
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.source_products import source_subject
from semantic.characterization_native_support import (
    current_characterization_recipe as current_characterization_recipe,
)
from semantic.data_operation_kernel_support import prepare_kernel
from semantic.formal_products_support import selected


def test_current_characterization_package_owns_actual_producers_without_model_provider(
    current_characterization_recipe,
):
    acquired = prepare_kernel(current_characterization_recipe)
    assert (
        acquired.model.operation("text.formal_evidence/source-native").capabilities.preparation
        == "resource"
    )
    assert acquired.model.operation("text.constructions/source-native").dependencies == (
        "text.formal_evidence/source-native",
        "segment.sentences/source-native",
    )
    composition = acquired.model.operation("text.compose_view/source-native")
    assert composition.dependencies == ("source.selected_views/discovery",)
    roles = {role.name: role for role in composition.roles}
    for name, source_set in (
        ("products", "selected-characterization-products"),
        ("active", "active-characterization-products"),
    ):
        support = roles[name].support
        assert support is not None
        assert support.source == "frozen-source-set" and support.source_set == source_set
        assert support.provenance == "exact" and support.identity_requirements == ("episode",)
    assert not any(
        operation.semantic_id == "text.hanlp_native/source-native"
        for operation in acquired.model.operations
    )
    assert all(item.complete for item in acquired.model.implementation_slices)


def test_current_positioned_kernels_preserve_partial_private_interpretations(
    current_characterization_recipe,
):
    acquired = prepare_kernel(current_characterization_recipe)
    formal = prepare_formal_evidence(acquired.prepared, acquired.model, grammar=grammar_identity())
    source = selected(formal, "Not every trial succeeds.")
    value = source.value
    context = SubjectContext(
        "current-kernel-control",
        source_subject(value["source"]),
        value["source"]["document"],
        canonical_bytes({"source": value["source"], "selectors": value["selectors"]}),
        subject_definition="original-source-view",
    )
    primary = formal.run(source, FormalEvidenceOptions(), subject_context=context)
    product = PreparedConstructionProfile(acquired.prepared, acquired.model).run(
        source, (primary,), subject_context=context
    )
    assert product.value["outcome"] == "partial"
    inventory = product.inventory()
    assert any(row["kind"] == "binder" for row in inventory["terms"])
    assert any(row["value"] == "negation" for row in inventory["terms"])
    assert product.value["source"] == value["source"]
    assert b"source_view_id" not in product.content and b"task_id" not in product.content


def test_current_formal_kernel_retains_original_syntax_without_recognized_text(
    current_characterization_recipe,
):
    acquired = prepare_kernel(current_characterization_recipe)
    formal = prepare_formal_evidence(acquired.prepared, acquired.model, grammar=grammar_identity())
    source = selected(
        formal,
        "",
        pieces=[],
        items=[dict(self_ref="#/texts/0", label="formula", text="", orig="x+1")],
        recognition=[dict(pointer="#/texts/0", outcome="failed")],
    )
    value = source.value
    context = SubjectContext(
        "item-anchored-control",
        source_subject(value["source"]),
        value["source"]["document"],
        canonical_bytes({"source": value["source"], "selectors": value["selectors"]}),
        subject_definition="original-source-view",
    )
    product = formal.run(source, FormalEvidenceOptions(), subject_context=context)
    inventory = product.inventory()
    inputs = [
        row["formal_input"] for row in inventory["annotations"] if row["kind"] == "formal.input"
    ]
    assert inputs and all(item["original_text"] == "x+1" for item in inputs)
    by_representation = {item["representation"]: item for item in inputs}
    assert by_representation["source_text"]["text"] == "x+1"
    assert by_representation["source_text"]["syntax_outcome"] == "complete"
    assert by_representation["recognized_latex"]["text"] == ""
    assert by_representation["recognized_latex"]["syntax_outcome"] == "failed"
    assert (
        next(row for row in inventory["coverage"] if row["family"] == "formal.math")["outcome"]
        == "partial"
    )
    assert any(
        extent["native_pointer"] == "#/texts/0" and "start" not in extent
        for row in inventory["occurrences"]
        for extent in row["extents"]
    )
