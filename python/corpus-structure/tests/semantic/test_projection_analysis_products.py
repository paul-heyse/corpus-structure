"""Retained-source analysis is a product, not a current-code archive substitute."""

import json
from dataclasses import replace
from functools import lru_cache

import pytest

from corpus_structure.semantic.composed import composed_dependencies
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.operation_reporting import compare_semantic_releases
from corpus_structure.semantic.projection_analysis_products import (
    ARTIFACT,
    prepare_projection_analysis,
    read_projection_analysis,
)
from corpus_structure.semantic.refusals import SemanticRefusal
from corpus_structure.semantic.types import PreparedArtifact, ResolvedDependencies, SourceArtifact

from .test_operation_reporting import prepared


@lru_cache(maxsize=1)
def product():
    result = prepare_projection_analysis(composed_dependencies(ResolvedDependencies()))
    assert result is not None
    return result


def with_product(release, artifact):
    return replace(
        release, artifacts=(*(a for a in release.artifacts if a.kind != ARTIFACT), artifact)
    )


def test_supplied_recipe_closure_yields_all_four_typed_qualified_products():
    value = read_projection_analysis(with_product(prepared(), product()))
    assert value is not None
    assert {entry.family for entry in value.projections} == {
        "input",
        "relation",
        "coverage",
        "mapping_report",
    }
    relation = next(entry.analysis for entry in value.projections if entry.family == "relation")
    assert "kb.pdf_record_endpoint" in relation.relational_sources
    assert (
        "physical:kb.pdf_record_endpoint.role" in dict(relation.value_dependencies)["endpoint_role"]
    )
    assert dict(relation.relational_dependencies)["join"]
    assert "ops.read_published_relation_batch" in relation.consumers
    assert not value.complete
    assert relation.unknowns == ("helper body not analyzed: ops.pdf_companion_body",)


def test_absent_or_incompatible_retained_physical_source_does_not_borrow_installed_schema():
    assert prepare_projection_analysis(ResolvedDependencies()) is None
    deps = composed_dependencies(ResolvedDependencies())
    path = "execution/implementation/pdf/record-physical.yaml"
    missing = replace(deps, artifacts=tuple(a for a in deps.artifacts if a.name != path))
    result = prepare_projection_analysis(missing)
    assert result is not None
    assert json.loads(result.content)["projections"] == []
    changed = replace(
        deps,
        artifacts=tuple(
            SourceArtifact(a.name, a.content + b"\n# different retained profile\n")
            if a.name == path
            else a
            for a in deps.artifacts
        ),
    )
    result = prepare_projection_analysis(changed)
    assert result is not None
    value = json.loads(result.content)
    assert not value["complete"]
    assert value["unknowns"][0].startswith("Unsupported retained physical profile:")
    before = with_product(prepared(), product())
    after = with_product(replace(before, release_id="release:unsupported-physical"), result)
    report = compare_semantic_releases(before, after).model_dump(mode="json")
    assert not any(change["model_ref"].startswith("projection:") for change in report["changes"])
    assert any("addition or removal is unassessed" in value for value in report["unknowns"])


def test_impact_consumes_retained_non_output_dependencies_and_unknowns():
    before = with_product(prepared(), product())
    payload = json.loads(product().content)
    entry = next(p for p in payload["projections"] if p["family"] == "relation")
    entry["analysis"]["relational_dependencies"] = [
        ["where", ["physical:kb.pdf_record_companion.local_id"]]
    ]
    after = with_product(
        replace(before, release_id="release:changed"),
        PreparedArtifact(ARTIFACT, canonical_bytes(payload)),
    )
    report = compare_semantic_releases(before, after).model_dump(mode="json")
    change = next(c for c in report["changes"] if c["aspect"] == "relational_dependencies")
    assert change["model_ref"] == "projection:relation"
    assert "ops.read_published_relation_batch" in change["consumers"]
    assert "physical:kb.pdf_record_companion.local_id" in change["reason"]
    assert any("helper body not analyzed" in item for item in report["unknowns"])
    assert not report["complete"]


def test_unsupported_product_is_refused_instead_of_empty_success():
    bad = PreparedArtifact(ARTIFACT, b'{"version":"future","complete":true,"projections":[]}')
    with pytest.raises(SemanticRefusal, match="Unsupported retained"):
        read_projection_analysis(with_product(prepared(), bad))
