"""Current captured query analysis and retained comparison preserve their evidence limits."""

import json
import os
import shutil
import subprocess
import sys
from dataclasses import replace
from functools import lru_cache
from pathlib import Path

import pytest
import yaml

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.pdf_domain import (
    ANALYSIS_RUNTIME,
    CONTRACT,
    PREFIX,
    PdfDomainContract,
    pdf_domain_sources,
)
from corpus_structure.semantic.projection_analysis_products import (
    ARTIFACT,
    compare_retained_projection_analysis,
    prepare_projection_analysis,
    read_projection_analysis,
)
from corpus_structure.semantic.refusals import SemanticRefusal
from corpus_structure.semantic.types import (
    PreparedArtifact,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
)
from semantic.pdf_domain_support import altered_domain, dependencies


@lru_cache(maxsize=1)
def domain():
    contract, *sources = pdf_domain_sources()
    return PdfDomainContract(contract.content, tuple(sources))


def analysis_dependencies():
    return ResolvedDependencies((SourceArtifact(CONTRACT, domain().content), *domain().sources))


@lru_cache(maxsize=1)
def report_inputs():
    return SourceBundle(
        "tiny",
        (
            SourceArtifact(
                "tiny", b"id: urn:query-analysis\nname: query_analysis\nclasses: {Thing: {}}\n"
            ),
        ),
    ), dependencies(domain())


@lru_cache(maxsize=1)
def prepared():
    from corpus_structure.semantic.prepare import prepare_release

    return prepare_release(*report_inputs())


@lru_cache(maxsize=1)
def product():
    result = prepare_projection_analysis(analysis_dependencies())
    assert result is not None
    return result


def with_product(release, artifact):
    return replace(
        release, artifacts=(*(a for a in release.artifacts if a.kind != ARTIFACT), artifact)
    )


def changed_sources(path, content):
    changed = altered_domain(
        domain(),
        sources=tuple(
            SourceArtifact(s.name, content) if s.name == path else s for s in domain().sources
        ),
    )
    return ResolvedDependencies((SourceArtifact(CONTRACT, changed.content), *changed.sources))


def test_runtime_mismatch_refuses_before_warm_preparation_or_direct_production(monkeypatch):
    from corpus_structure.semantic import determinants
    from corpus_structure.semantic.prepare import prepare_release
    from corpus_structure.semantic.types import PreparationError

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
    deps = analysis_dependencies()
    stripped = replace(
        deps, artifacts=tuple(item for item in deps.artifacts if item.name != ANALYSIS_RUNTIME)
    )
    with pytest.raises(ValueError, match="provenance missing"):
        prepare_projection_analysis(stripped)


def test_retained_analysis_read_does_not_consult_current_analyzer(monkeypatch):
    from corpus_structure.semantic import projection_analysis_products

    retained = with_product(prepared(), product())
    monkeypatch.setattr(
        projection_analysis_products,
        "analyze_recipe",
        lambda *args: pytest.fail("archive reader executed analysis"),
    )
    value = read_projection_analysis(retained)
    assert value is not None
    assert {entry.family for entry in value.projections} == {
        "input",
        "relation",
        "coverage",
        "mapping_report",
    }


def test_cold_current_analysis_uses_proposed_profile_before_and_after_apply(tmp_path):
    import corpus_structure
    from corpus_structure.schema.physical import PHYSICAL_ROOT, physical_source_closure

    package = Path(corpus_structure.__file__).parent
    installed = tmp_path / package.name
    shutil.copytree(package, installed, ignore=shutil.ignore_patterns("__pycache__"))
    physical = installed / "model/semantic"
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
import json,sys
from corpus_structure.schema.physical import linkml_types_source
from corpus_structure.semantic.pdf_domain import pdf_domain_sources
from corpus_structure.semantic.projection_analysis_products import prepare_projection_analysis
from corpus_structure.semantic.metadata import get_physical_model_id
from corpus_structure.semantic.types import ResolvedDependencies
sources=json.load(sys.stdin)
kwargs=dict(physical_sources={n:bytes.fromhex(c) for n,c in sources.items()},linkml_types=linkml_types_source()) if sources else {}
artifact=prepare_projection_analysis(ResolvedDependencies(pdf_domain_sources(**kwargs)))
value=json.loads(artifact.content)
assert len(value['projections'])==4,value
print(json.dumps(dict(installed=get_physical_model_id(),physical=value['physical_id'],source=value['source_id'],digest=artifact.digest)))
"""

    def analyze(sources):
        result = subprocess.run(
            [sys.executable, "-c", child],
            cwd=tmp_path,
            env={**os.environ, "PYTHONPATH": str(tmp_path)},
            input=json.dumps({n: c.hex() for n, c in sources.items()}),
            text=True,
            capture_output=True,
            check=False,
            timeout=120,
        )
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)

    before = analyze(approved)
    assert before.pop("installed") != before["physical"]
    for name, content in approved.items():
        physical.joinpath(name).write_bytes(content)
    after = analyze({})
    assert after.pop("installed") == before["physical"]
    assert after == before


def test_supplied_recipe_closure_yields_all_four_typed_qualified_products():
    value = read_projection_analysis(with_product(prepared(), product()))
    assert value is not None
    assert value.version == "projection-analysis-3"
    assert all(item.analysis.profile == "companion-query-analysis-3" for item in value.projections)
    relation = next(entry.analysis for entry in value.projections if entry.family == "relation")
    assert "kb.pdf_record_endpoint" in relation.relational_sources
    assert (
        "physical:kb.pdf_record_endpoint.role" in dict(relation.value_dependencies)["endpoint_role"]
    )
    assert dict(relation.relational_dependencies)["join"]
    assert "ops.read_published_relation_batch" in relation.consumers
    assert not value.complete
    assert relation.unknowns == ("helper body not analyzed: ops.pdf_companion_body",)


def test_missing_or_changed_physical_source_does_not_borrow_installed_schema():
    assert prepare_projection_analysis(ResolvedDependencies()) is None
    deps = analysis_dependencies()
    path = PREFIX + "physical/physical.yaml"
    result = prepare_projection_analysis(
        replace(deps, artifacts=tuple(a for a in deps.artifacts if a.name != path))
    )
    assert result is not None and not json.loads(result.content)["projections"]
    source = next(a.content for a in deps.artifacts if a.name == path)
    changed = prepare_projection_analysis(
        changed_sources(path, source + b"\n# exact reviewed physical source\n")
    )
    assert changed is not None
    value, original = json.loads(changed.content), json.loads(product().content)
    assert len(value["projections"]) == 4
    assert value["physical_id"] != original["physical_id"]
    assert value["source_id"] != original["source_id"]


def test_retained_comparison_preserves_nonoutput_dependencies_consumers_and_unknowns():
    before = with_product(prepared(), product())
    payload = json.loads(product().content)
    entry = next(p for p in payload["projections"] if p["family"] == "relation")
    entry["analysis"]["relational_dependencies"] = [
        ["where", ["physical:kb.pdf_record_companion.local_id"]]
    ]
    entry["analysis"]["consumers"].append("reviewed.consumer")
    after = with_product(
        replace(before, release_id="release:changed"),
        PreparedArtifact(ARTIFACT, canonical_bytes(payload)),
    )
    report = compare_retained_projection_analysis(before, after)
    change = next(c for c in report.changes if c.aspect == "relational_dependencies")
    assert change.model_ref == "projection:relation"
    assert change.after == [["where", ["physical:kb.pdf_record_companion.local_id"]]]
    assert "ops.read_published_relation_batch" in change.consumers
    assert "reviewed.consumer" in change.consumers
    assert any(c.aspect == "consumers" for c in report.changes)
    assert any("helper body not analyzed" in item for item in report.unknowns)
    assert not report.complete


@pytest.mark.parametrize("version", ["future", "projection-analysis-1", "projection-analysis-2"])
def test_unsupported_product_is_refused_instead_of_empty_success(version):
    body = json.loads(product().content)
    body["version"] = version
    with pytest.raises(SemanticRefusal, match="Unsupported retained"):
        read_projection_analysis(
            with_product(prepared(), PreparedArtifact(ARTIFACT, canonical_bytes(body)))
        )


def test_nested_query_expansion_reaches_retained_comparison_and_located_validation():
    from corpus_structure.semantic.operation_reporting import projection_validation_report

    path = PREFIX + "logical/companion_projections"
    source = next(item for item in domain().sources if item.name == path)
    document = yaml.safe_load(source.content)
    declarations = document["annotations"]
    sources = json.loads(declarations["cp:sources"])
    first = dict(sources[-1], name="first", materialized=False)
    second = dict(first, name="second", input={"name": "first", "alias": "raw"})
    barrier = dict(sources[-1], input={"name": "second", "alias": "raw"})
    declarations["cp:sources"] = json.dumps([*sources[:-1], first, second, barrier])
    artifact = prepare_projection_analysis(changed_sources(path, yaml.safe_dump(document).encode()))
    assert artifact is not None
    before = with_product(prepared(), product())
    after = with_product(replace(before, release_id="release:nested"), artifact)
    retained = read_projection_analysis(after)
    assert retained is not None
    assert dict(retained.projections[0].analysis.logical_sources)["second"].endswith(
        "/sources/second"
    )
    report = compare_retained_projection_analysis(before, after)
    assert any(c.aspect == "logical_sources" and c.consumers for c in report.changes)
    assert any(c.aspect == "occurrences" and c.consumers for c in report.changes)
    assert any(c.aspect == "source_context" for c in report.changes)
    assert not report.complete
    located = projection_validation_report(after).model_dump(mode="json")
    assert located["release_id"] == after.release_id
    assert not located["complete"]
    assert all(
        item["category"] == "unassessed" and item["model_path"].startswith("projection:")
        for item in located["observations"]
    )


def test_missing_projection_has_no_fabricated_pairwise_comparison():
    before = with_product(prepared(), product())
    absent = replace(
        before,
        release_id="release:absent",
        artifacts=tuple(a for a in before.artifacts if a.kind != ARTIFACT),
    )
    result = compare_retained_projection_analysis(before, absent)
    assert not result.complete
    assert any("unavailable" in item for item in result.unknowns)
    assert any("addition or removal" in item for item in result.unknowns)
    assert {c.model_ref for c in result.changes if c.aspect == "presence"} == {
        "projection:input",
        "projection:relation",
        "projection:coverage",
        "projection:mapping_report",
    }
