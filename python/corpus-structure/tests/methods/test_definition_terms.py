"""Literal source and original-component identity controls for term projection."""

from types import SimpleNamespace

import pytest

from corpus_structure.core.method import UnitRef
from corpus_structure.core.vocab import TaskUnitType
from corpus_structure.methods.contextual_candidates import retained_definition_witnesses
from corpus_structure.methods.definition_terms import DefinitionTermsConfig, DefinitionTermsMethod
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.structural_products import ExternalSourceRef, RetainedComponentRef
from methods.test_m1_producer import view


def test_projection_uses_retained_source_role_and_refuses_foreign_source():
    source_view = view()
    reference = RetainedComponentRef(product_id="structural:original", component_id="a" * 64,
        operation_id="structure.definition_components", operation_version="3", project_id="book", run_id=1,
        cut_id=2, release_id="release", result_revision=1, selected_task_id=3, origin_task_id=3,
        runtime_fingerprint="runtime", dependencies=("original-source",))
    source = ExternalSourceRef(project_id="book", run_id=1, cut_id=2, release_id="release", result_revision=1,
        source_view_id=source_view.ref.id, native_task_id=23, native_product_key="integrated",
        native_content_digest="a" * 64, projection_digest=source_view.ref.projection_digest,
        recipe_digest=source_view.ref.recipe_digest, coordinate_version=2)
    retained = dict(component=dict(component_id=reference.component_id,
        term=dict(passage_id="p", start=0, end=4, text="Mean")),
        report=dict(inputs=dict(passages=[dict(passage_id="p", source_ref=source.identity)],
                                sources=[source.model_dump(mode="json")])))
    cfg = DefinitionTermsConfig(component_refs=(reference,), source_product_digest="a" * 64,
                                source_projection_digest=source.projection_digest)
    ctx = SimpleNamespace(reader=SimpleNamespace(source_view=lambda _: source_view,
        retained_definition_component=lambda _: retained), check_active=lambda: None)
    unit = SimpleNamespace(ref=UnitRef(TaskUnitType.SOURCE_VIEW, source_view.ref.id, source_view.ref.key))
    (result,) = DefinitionTermsMethod().run((unit,), cfg, ctx)
    assert result.contributions is not None
    (product,) = result.contributions
    assert product["anchors"][0]["source_piece"] == "Mean"
    assert product["anchors"][0]["start"] == 0 and product["anchors"][0]["end"] == 4
    assert source_python(product["value"])["role"] == "defined_term"
    assert source_python(product["value"])["component_reference"]["origin_task_id"] == 3
    target = SimpleNamespace(target_id=reference.component_id, source_binding="definition-component:" + reference.identity)
    query = dict(product, computation_dependencies=(product["contribution_id"], "upstream-operation"))
    witnesses = retained_definition_witnesses(dict(contributions=(product,)), (query,), product["occurrence_id"],
        SimpleNamespace(targets=(target,)), {reference.component_id}, "source", "scope", None)
    assert len(witnesses) == 1 and witnesses[0].relation == "defined-by"
    assert witnesses[0].support_state == "unassessed"
    target.source_binding = "definition-component:wrong-origin"
    with pytest.raises(ValueError, match="different component origin"):
        retained_definition_witnesses(dict(contributions=(product,)), (query,), product["occurrence_id"],
            SimpleNamespace(targets=(target,)), {reference.component_id}, "source", "scope", None)
    retained["report"]["inputs"]["sources"][0]["native_task_id"] = 999
    retained["report"]["inputs"]["passages"][0]["source_ref"] = ExternalSourceRef.model_validate(retained["report"]["inputs"]["sources"][0]).identity
    with pytest.raises(ValueError, match="another original source"):
        DefinitionTermsMethod().run((unit,), cfg, ctx)
    with pytest.raises(ValueError, match="duplicate"):
        DefinitionTermsConfig(component_refs=(reference, reference), source_product_digest="a" * 64,
                              source_projection_digest=source.projection_digest)
