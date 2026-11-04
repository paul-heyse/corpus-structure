"""Synthetic semantic releases for isolated operation contract tests."""

from sqlalchemy import Engine, insert

from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.types import PreparedRelease


def prepare_operation_scenario(
    engine: Engine,
    *,
    observations: bool = False,
    archive: bool = False,
    composed: bool = True,
    evaluation: bool = False,
) -> PreparedRelease:
    bundle = SourceBundle(
        "m",
        (
            SourceArtifact(
                "m",
                b"""id: https://example/m
name: m
prefixes: {ex: 'https://example/'}
default_prefix: ex
types:
 string: {base: str, uri: 'http://www.w3.org/2001/XMLSchema#string'}
 integer: {base: int, uri: 'http://www.w3.org/2001/XMLSchema#integer'}
 boolean: {base: bool, uri: 'http://www.w3.org/2001/XMLSchema#boolean'}
classes:
 Report:
  attributes:
   text: {required: true}
""",
            ),
        ),
    )
    if observations:
        from pathlib import Path

        from corpus_structure.semantic.observations import observation_inputs

        core = SourceArtifact(
            "core",
            (
                Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
            ).read_bytes(),
        )
        root = bundle.sources[0]
        bundle = SourceBundle(
            "m",
            (
                core,
                SourceArtifact(
                    root.name,
                    root.content.split(b"types:", 1)[0].replace(
                        b"default_prefix: ex", b"default_prefix: ex\nimports: [core]"
                    )
                    + b"classes:"
                    + root.content.split(b"classes:", 1)[1],
                ),
            ),
        )
        bundle = observation_inputs(bundle)
    from corpus_structure.semantic.types import ResolvedDependencies

    dependencies = ResolvedDependencies()
    if observations:
        import yaml

        from corpus_structure.semantic.metrics import METRIC_INPUT, observation_dependencies

        packaged = observation_dependencies(dependencies)
        declared = yaml.safe_load(
            next(a.content for a in packaged.artifacts if a.name == METRIC_INPUT)
        )
        declared["metrics"].append(
            dict(
                id="count",
                value_type="SourceNumberOrNull",
                subject_kind="run",
                detail_schema="SourceObject",
                description="Test method count",
            )
        )
        dependencies = observation_dependencies(dependencies, yaml.safe_dump(declared).encode())
    from corpus_structure.semantic.releases import persist_release
    from corpus_structure.semantic.types import PreparationProfile

    profile = PreparationProfile()
    if evaluation:
        from corpus_structure.semantic.analytical_profile import analytical_inputs
        from corpus_structure.semantic.domain_operations import domain_rule_inputs
        from corpus_structure.semantic.proposals import proposal_inputs

        dependencies = domain_rule_inputs(dependencies, b"rules: []\n")
        bundle = proposal_inputs(bundle, dependencies)
        bundle, dependencies = analytical_inputs(bundle, dependencies)
    if composed or evaluation:
        from corpus_structure.semantic.composed import composed_dependencies

        from .method_dimensions_support import fixture_execution_inputs

        dependencies = composed_dependencies(
            dependencies,
            fixture_execution_inputs(
                "read",
                "owned",
                "agent",
                "agent-disposition",
                "contract-unit",
                "custom.agent",
                "native-binding",
                "native.packet-fixture",
                "native.region-frame",
                "coverage.witness",
                "pdf.stage.fixture",
                "pdf13.fixture",
                "pdf.adoption-fixture",
                "pdf.consumer-fixture",
                "pdf.controlled-retained-fixture",
                "pdf.controlled-source",
                "pdf.fixture",
                "pdf.inline-fixture",
                "pdf.ocr-fixture",
                "pdf.view-fixture",
            ),
        )
        profile = PreparationProfile(version="semantic-2")
    p = prepare_release(bundle, dependencies, profile)
    with engine.begin() as c:
        persist_release(c, bundle, dependencies, profile, p)
        c.execute(insert(table("data.project")).values(project_id="p"))
        c.execute(
            insert(table("data.realization")).values(
                realization_id="z", release_id=p.release_id, project_id="p"
            )
        )
    return p
