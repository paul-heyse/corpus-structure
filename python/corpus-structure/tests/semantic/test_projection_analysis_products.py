"""Retained-source analysis is a product, not a current-code archive substitute."""

import json
import os
import shutil
import subprocess
import sys
from dataclasses import replace
from functools import lru_cache

import pytest
import yaml

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


def test_runtime_mismatch_refuses_before_warm_preparation_or_direct_production(monkeypatch):
    from corpus_structure.semantic import determinants
    from corpus_structure.semantic.prepare import prepare_release
    from corpus_structure.semantic.types import PreparationError

    from .test_operation_reporting import report_inputs

    inputs = report_inputs()
    prepare_release(*inputs)
    original = determinants.determinant_version
    monkeypatch.setattr(
        determinants,
        "determinant_version",
        lambda name: "incompatible-analyzer" if name == "sqlglot" else original(name),
    )
    with pytest.raises(PreparationError, match="reacquire"):
        prepare_release(*inputs)
    with pytest.raises(ValueError, match="reacquire"):
        prepare_projection_analysis(inputs[1])


def test_missing_analysis_provenance_refuses_but_nonanalysis_preparation_is_independent():
    from corpus_structure.semantic.determinants import projection_analysis_runtime

    assert projection_analysis_runtime(ResolvedDependencies()) == ()
    deps = composed_dependencies(ResolvedDependencies())
    stripped = replace(
        deps,
        artifacts=tuple(
            item
            for item in deps.artifacts
            if item.name != "execution/implementation/libraries.json"
        ),
    )
    with pytest.raises(ValueError, match="provenance missing"):
        prepare_projection_analysis(stripped)


def test_retained_analysis_read_does_not_consult_current_analyzer(monkeypatch):
    from corpus_structure.semantic import projection_analysis, projection_analysis_products

    retained = with_product(prepared(), product())

    def unavailable():
        raise AssertionError("retained artifact reading must not execute analysis")

    monkeypatch.setattr(projection_analysis, "analyze_recipe", unavailable)
    monkeypatch.setattr(projection_analysis_products, "analyze_recipe", unavailable)
    value = read_projection_analysis(retained)
    assert value is not None
    assert {entry.family for entry in value.projections} == {
        "input",
        "relation",
        "coverage",
        "mapping_report",
    }


def test_cold_composed_preparation_uses_proposed_profile_before_and_after_apply(tmp_path):
    from corpus_structure.schema.model import MODEL_DIR
    from corpus_structure.schema.physical import PHYSICAL_ROOT, physical_source_closure

    from .test_operation_reporting import report_inputs

    bundle = report_inputs()[0]
    package = MODEL_DIR.parent
    installed = tmp_path / package.name
    shutil.copytree(package, installed, ignore=shutil.ignore_patterns("__pycache__"))
    physical = installed / "model" / "semantic"
    approved = physical_source_closure(
        PHYSICAL_ROOT, lambda name: physical.joinpath(name).read_bytes()
    )
    proposal = yaml.safe_load(approved[PHYSICAL_ROOT])
    proposal["imports"].append("reviewed-fixture")
    approved[PHYSICAL_ROOT] = yaml.safe_dump(proposal).encode()
    approved["reviewed-fixture.yaml"] = (
        b"id: https://example.org/reviewed-fixture\nname: reviewed-fixture\n"
    )
    child = """
import json, sys
from corpus_structure.semantic import prepare_release
from corpus_structure.semantic.composed import composed_dependencies
from corpus_structure.semantic.contracts import trusted_execution_inputs
from corpus_structure.semantic.metadata import PHYSICAL_MODEL_ID
from corpus_structure.semantic.projection_analysis_products import read_projection_analysis
from corpus_structure.semantic.types import (
    SourceArtifact, SourceBundle, ResolvedDependencies, PreparationProfile,
)
payload = json.load(sys.stdin)
bundle = SourceBundle(
    payload['root'], tuple(SourceArtifact(n, bytes.fromhex(c)) for n,c in payload['sources']),
)
sources = payload['physical']
execution = trusted_execution_inputs(
    physical_sources={n: bytes.fromhex(c) for n,c in sources.items()} if sources else None,
)
prepared = prepare_release(
    bundle, composed_dependencies(ResolvedDependencies(), execution),
    PreparationProfile(version='semantic-2'),
)
product = read_projection_analysis(prepared)
assert product is not None
relation = next(item.analysis for item in product.projections if item.family == 'relation')
print(json.dumps({
    'installed': PHYSICAL_MODEL_ID, 'prepared': product.physical_id,
    'release': prepared.release_id, 'artifacts': prepared.artifacts_sha256,
    'profile': json.loads(prepared.manifest)['profile']['version'],
    'types': dict(relation.output_types), 'value': dict(relation.value_dependencies),
    'relational': dict(relation.relational_dependencies),
    'libraries': json.loads(prepared.manifest)['libraries'],
}))
"""

    def prepare(physical_sources):
        result = subprocess.run(
            [sys.executable, "-c", child],
            cwd=tmp_path,
            env={**os.environ, "PYTHONPATH": str(tmp_path)},
            input=json.dumps(
                {
                    "root": bundle.root,
                    "sources": [(s.name, s.content.hex()) for s in bundle.sources],
                    "physical": {n: c.hex() for n, c in physical_sources.items()},
                }
            ),
            text=True,
            capture_output=True,
            check=False,
            timeout=90,
        )
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)

    value = prepare(approved)
    assert value.pop("installed") != value["prepared"]
    for name, content in approved.items():
        physical.joinpath(name).write_bytes(content)
    applied = prepare({})
    assert applied.pop("installed") == value["prepared"]
    assert applied == value
    assert value["profile"] == "semantic-2"
    assert value["types"]["endpoint_role"] == "TEXT"
    assert "physical:kb.pdf_record_endpoint.role" in value["value"]["endpoint_role"]
    assert "physical:kb.pdf_record_companion.family" in value["relational"]["where"]
    assert "physical:kb.pdf_record_companion.family" not in value["value"]["endpoint_role"]
    assert value["libraries"]["sqlglot"] == "30.27.0"
    assert value["libraries"]["sqlalchemy"] == "2.1.6"


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
    assert value.version == "projection-analysis-3"
    assert all(item.analysis.profile == "companion-query-analysis-3" for item in value.projections)
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
    supported_change = replace(
        deps,
        artifacts=tuple(
            SourceArtifact(a.name, a.content + b"\n# different retained profile\n")
            if a.name == path
            else a
            for a in deps.artifacts
        ),
    )
    result = prepare_projection_analysis(supported_change)
    assert result is not None
    value = json.loads(result.content)
    original = json.loads(product().content)
    assert len(value["projections"]) == 4
    assert value["physical_id"] != original["physical_id"]
    assert value["source_id"] != original["source_id"]
    source = yaml.safe_load(next(a.content for a in deps.artifacts if a.name == path))
    source["classes"]["pdf_record_endpoint"]["is_a"] = "UnavailableRetainedShape"
    changed = replace(
        deps,
        artifacts=tuple(
            SourceArtifact(a.name, yaml.safe_dump(source).encode()) if a.name == path else a
            for a in deps.artifacts
        ),
    )
    result = prepare_projection_analysis(changed)
    assert result is not None
    value = json.loads(result.content)
    assert not value["complete"]
    assert value["unknowns"][0].startswith("Unsupported retained")
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
    old = json.loads(product().content)
    old["version"] = "projection-analysis-1"
    with pytest.raises(SemanticRefusal, match="Unsupported retained"):
        read_projection_analysis(
            with_product(prepared(), PreparedArtifact(ARTIFACT, canonical_bytes(old)))
        )


def test_retained_nested_query_expansion_reaches_impact_and_located_validation():
    import yaml

    from corpus_structure.semantic.operation_reporting import (
        compatibility_advice,
        projection_validation_report,
    )

    deps = composed_dependencies(ResolvedDependencies())
    name = "execution/implementation/capture/companion-projection-model.yaml"
    source = next(item for item in deps.artifacts if item.name == name)
    document = yaml.safe_load(source.content)
    declarations = document["annotations"]
    sources = json.loads(declarations["cp:sources"])
    # Existing materialized source stays a barrier. Add two nonmaterialized
    # model-owned definitions before it using the same typed physical fields.
    first = dict(sources[-1], name="first", materialized=False)
    second = dict(first, name="second", input={"name": "first", "alias": "raw"})
    barrier = dict(sources[-1], input={"name": "second", "alias": "raw"})
    declarations["cp:sources"] = json.dumps([*sources[:-1], first, second, barrier])
    changed = replace(
        deps,
        artifacts=tuple(
            SourceArtifact(item.name, yaml.safe_dump(document).encode())
            if item.name == name
            else item
            for item in deps.artifacts
        ),
    )
    artifact = prepare_projection_analysis(changed)
    assert artifact is not None
    before = with_product(prepared(), product())
    after = with_product(replace(before, release_id="release:nested"), artifact)
    retained = read_projection_analysis(after)
    assert retained is not None
    assert dict(retained.projections[0].analysis.logical_sources)["second"].endswith(
        "/sources/second"
    )
    impact = compare_semantic_releases(before, after)
    value = impact.model_dump(mode="json")
    assert any(
        change["aspect"] == "logical_sources" and change["consumers"] for change in value["changes"]
    )
    assert not value["complete"]
    assert any("helper body not analyzed" in message for message in value["unknowns"])
    located = projection_validation_report(after).model_dump(mode="json")
    assert located["release_id"] == after.release_id
    assert not located["complete"]
    assert all(
        item["category"] == "unassessed" and item["model_path"].startswith("projection:")
        for item in located["observations"]
    )
    advice = compatibility_advice(impact)
    assert any("Regenerate and qualify" in message for message in advice)
    assert any("unknown" in message for message in advice)


def test_v2_archive_preserves_summaries_without_fabricated_occurrence_detail(monkeypatch):
    from corpus_structure.semantic import projection_analysis_products

    body = json.loads(product().content)
    body["version"] = "projection-analysis-2"
    for entry in body["projections"]:
        entry["analysis"]["profile"] = "companion-query-analysis-2"
        entry["analysis"].pop("occurrences")
        entry["analysis"].pop("detail_status")
    archive = with_product(prepared(), PreparedArtifact(ARTIFACT, canonical_bytes(body)))
    monkeypatch.setattr(
        projection_analysis_products,
        "analyze_recipe",
        lambda *args: pytest.fail("reanalyzed archive"),
    )
    value = read_projection_analysis(archive)
    assert value is not None
    assert all(
        entry.analysis.detail_status == "unavailable" and not entry.analysis.occurrences
        for entry in value.projections
    )
    assert next(e.analysis for e in value.projections if e.family == "relation").value_dependencies


def test_v2_archive_validation_exposes_unavailable_detail_without_reanalysis(monkeypatch):
    from corpus_structure.semantic import projection_analysis_products
    from corpus_structure.semantic.operation_reporting import projection_validation_report

    body = json.loads(product().content)
    body["version"] = "projection-analysis-2"
    for entry in body["projections"]:
        entry["analysis"]["profile"] = "companion-query-analysis-2"
        entry["analysis"].pop("occurrences")
        entry["analysis"].pop("detail_status")
    archive = with_product(prepared(), PreparedArtifact(ARTIFACT, canonical_bytes(body)))
    monkeypatch.setattr(
        projection_analysis_products,
        "analyze_recipe",
        lambda *args: pytest.fail("validation reanalyzed archived detail"),
    )
    compact = projection_validation_report(archive).model_dump(mode="json")
    detailed = projection_validation_report(
        archive, dependency_detail=True, dependency_family="relation"
    ).model_dump(mode="json")
    assert detailed["complete"] == compact["complete"]
    assert detailed["observations"] == compact["observations"]
    page = detailed["projection_dependencies"]
    assert page["items"] == [
        {
            "side": "current",
            "family": "relation",
            "status": "unavailable",
            "reason": "Archived analysis does not retain occurrence detail.",
        }
    ]
    assert page["paging_complete"] and not page["coverage_complete"]
