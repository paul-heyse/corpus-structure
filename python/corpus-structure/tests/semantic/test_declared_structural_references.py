"""Native semantic addresses and local domain IDs remain distinct structural facts."""

from dataclasses import replace

import pytest
from pydantic import ValidationError

from corpus_structure.semantic.data_operation_model import BoundRoleMember
from corpus_structure.semantic.declared_structural_references import (
    DeclaredContributionRef,
    DeclaredProductRef,
    DeclaredStructuralSource,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.structural_products import ExternalSourceRef


def test_qualified_product_ref_preserves_header_and_does_not_alias_domain_content_id():
    member = BoundRoleMember(
        "product:whole-report",
        "kind:inspection",
        "source:subject",
        "document:B",
        b'{"page":1.0}',
        b"{}",
        (),
        b"{}",
    )
    reference = DeclaredContributionRef.from_bound(
        member, project="p", contribution_id="source-contribution:" + "a" * 64
    )
    assert reference.product_id == "product:whole-report"
    assert reference.member_id is None
    assert reference.analyzed_scope_meaning == '["mapping",[["page",["decimal","1"]]]]'
    assert not {"run_id", "task_id", "source_view_id", "release_id"} & reference.model_dump().keys()
    assert (
        DeclaredProductRef.from_bound(
            replace(member, analyzed_scope=b'{"page":1}'), project="p"
        ).context
        == reference.context
    )
    assert (
        DeclaredProductRef.from_bound(
            replace(member, analyzed_scope=b'{"page":true}'), project="p"
        ).context
        != reference.context
    )


def test_declared_source_ref_has_one_exact_native_address_and_legacy_schema_is_separate():
    pin = {
        "format": "declared-native-source-v1",
        "source": '["product:source",null]',
        "subject": "subject",
        "document": "document",
        "projection_digest": "a" * 64,
        "section_pointer": "#/texts/0",
        "membership": "direct",
        "project_id": "p",
        "original_source": "document",
        "analyzed_scope_meaning": '["null"]',
        "source_product": "product:source",
        "kind_contract": "kind:source",
    }
    source = DeclaredStructuralSource.model_validate(pin)
    assert source.matches_pin(pin)
    assert not source.matches_pin({**pin, "source_product": "different"})
    assert canonical_bytes(pin) == canonical_bytes(
        source.model_dump(mode="json", exclude_none=True)
    )
    with pytest.raises(ValidationError, match="complete native address"):
        DeclaredStructuralSource.model_validate({**pin, "source_product": "different"})
    assert set(ExternalSourceRef.model_json_schema()["properties"]) == {
        "project_id",
        "run_id",
        "cut_id",
        "release_id",
        "result_revision",
        "source_view_id",
        "native_task_id",
        "native_product_key",
        "native_content_digest",
        "projection_digest",
        "recipe_digest",
        "coordinate_version",
    }


def test_task_replay_source_view_preserves_original_refs_and_refuses_declared_custody():
    from corpus_structure.semantic.structural_products import (
        DeclaredStructuralInput,
        legacy_structural_sources,
    )
    from semantic.structural_products_support import inputs

    legacy = inputs()
    selected = legacy_structural_sources(legacy)
    assert all(
        actual is original for actual, original in zip(selected, legacy.sources, strict=True)
    )
    target = DeclaredStructuralSource(
        format="declared-native-source-v1",
        source='["product:source",null]',
        source_product="product:source",
        kind_contract="kind:source",
        subject="subject",
        document="document",
        projection_digest="a" * 64,
        section_pointer="#/texts/0",
        membership="direct",
        project_id="p",
        original_source="document",
        analyzed_scope_meaning='["null"]',
    )
    passage = legacy.passages[0].model_copy(update={"source_ref": target.identity})
    current = DeclaredStructuralInput(
        question=legacy.question,
        scope=legacy.scope,
        inventory_id=legacy.inventory_id,
        policy_id=legacy.policy_id,
        sources=(target,),
        passages=(passage,),
        dependencies=legacy.dependencies,
    )
    with pytest.raises(
        ValueError, match="task-based structural replay requires original legacy source custody"
    ):
        legacy_structural_sources(current)
    assert current.sources[0] is target
    assert not hasattr(target, "native_task_id") and not hasattr(target, "source_view_id")
