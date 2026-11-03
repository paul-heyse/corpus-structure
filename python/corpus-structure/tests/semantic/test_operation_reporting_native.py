"""Real archived-release CLI/MCP observations, including native admission refusal."""

import json
from dataclasses import replace

import anyio
from fastmcp import Client

from corpus_structure.intervene.semantic_server import SemanticProjectSession, build_semantic_server
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.releases import persist_release
from corpus_structure.semantic.types import SourceArtifact
from corpus_structure.settings import Settings

from .test_operation_reporting import prepared, report_inputs


def test_actual_cli_and_mcp_reports_share_archived_meaning_and_located_refusal(
    semantic_db_engine,
    semantic_reader_engine,
    cli,
):
    release = prepared()
    bundle, deps, profile = report_inputs()
    with semantic_db_engine.begin() as conn:
        persist_release(conn, bundle, deps, profile, release)
    settings = Settings(
        database={
            "url": semantic_reader_engine.url.set(drivername="postgresql").render_as_string(
                hide_password=False
            )
        }
    )
    explained = cli(
        "schema",
        "explain-operation",
        "claim",
        "--release",
        release.release_id,
        "--json",
        settings=lambda: settings,
    )
    assert explained.exit_code == 0, explained.output
    observation = json.loads(explained.stdout)
    assert observation["operation"] == "claim"
    assert not observation["complete"]
    assert any(c["status"] == "unresolved" for c in observation["checks"])
    # Frozen84 supplies the required native realization. Observation alone still
    # grants no mutable task ownership and attempts no claim effect.
    native = next(
        c for c in observation["checks"] if c["owner"] == "sem.require_execution_operation"
    )
    assert native["status"] == "applicable"
    compared = cli(
        "schema",
        "diff",
        release.release_id,
        release.release_id,
        "--json",
        settings=lambda: settings,
    )
    assert compared.exit_code == 0, compared.output
    impact = json.loads(compared.stdout)
    assert impact["changes"] == []
    assert any("helper body not analyzed" in item for item in impact["unknowns"])
    invalid = cli(
        "schema",
        "explain-operation",
        "not_declared",
        "--release",
        release.release_id,
        "--json",
        settings=lambda: settings,
    )
    assert invalid.exit_code == 1, invalid.output
    assert (
        json.loads(invalid.stdout)["error"]["validation"]["observations"][0]["category"]
        == "unassessed"
    )

    async def journey():
        server = build_semantic_server(SemanticProjectSession(semantic_reader_engine, "reports"))
        async with Client(server) as client:
            answer = await client.call_tool(
                "explain_operation",
                {
                    "release": release.release_id,
                    "operation": "claim",
                },
            )
            assert answer.structured_content is not None
            result = answer.structured_content
            assert result["model_id"] == observation["model_id"]
            assert result["checks"] == observation["checks"]
            difference = await client.call_tool(
                "compare_semantic_releases",
                {
                    "before": release.release_id,
                    "after": release.release_id,
                },
            )
            assert difference.structured_content == impact

    anyio.run(journey)


def test_live_preflight_never_authorizes_stale_native_publication(
    semantic_db_engine,
    semantic_writer_engine,
    semantic_reader_engine,
):
    import pytest
    from sqlalchemy import insert

    from corpus_structure.semantic.arrow_publication import StaleAnalysisError
    from corpus_structure.semantic.inference import derive, publish_inference
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.operation_reporting import explain_operation
    from corpus_structure.semantic.publication import PublicationBatch, publish_batch
    from corpus_structure.semantic.query import SnapshotBinding, read_snapshot

    from .test_inference import _inference_publication_state

    release = prepared()
    bundle, deps, profile = report_inputs()
    realization = "report-stale-realization"
    with semantic_db_engine.begin() as conn:
        persist_release(conn, bundle, deps, profile, release)
        conn.execute(insert(table("data.project")).values(project_id="report-stale"))
        conn.execute(
            insert(table("data.realization")).values(
                realization_id=realization,
                project_id="report-stale",
                release_id=release.release_id,
            )
        )
    binding = SnapshotBinding(release.release_id, realization, 0, "report-preflight")
    with read_snapshot(semantic_reader_engine) as conn:
        observed = explain_operation(
            release, "derive", subject=binding, connection=conn
        ).model_dump(mode="json")
    check = next(item for item in observed["checks"] if item["contract_ref"] == "SnapshotBinding")
    assert check["status"] == "applicable"
    with (
        semantic_writer_engine.connect().execution_options(
            isolation_level="REPEATABLE READ"
        ) as conn,
        conn.begin(),
    ):
        result = derive(conn, binding)
    publish_batch(
        semantic_writer_engine,
        PublicationBatch(release.release_id, realization, "advance-after-preflight"),
    )
    with semantic_db_engine.connect() as conn:
        before = _inference_publication_state(conn, release.release_id, realization)
    assert len(before["data.batch"]) == 1
    assert before["data.batch"][0]["batch_id"] == "advance-after-preflight"
    assert before["data.realization"][0]["data_revision"] == 1
    with pytest.raises(StaleAnalysisError, match="revision changed"):
        publish_inference(semantic_writer_engine, result)
    with semantic_db_engine.connect() as conn:
        after = _inference_publication_state(conn, release.release_id, realization)
    assert {name: len(rows) for name, rows in after.items()} == {
        name: len(rows) for name, rows in before.items()
    }
    assert after == before
    assert result.batch.batch_id not in {row["batch_id"] for row in after["data.batch"]}
    with read_snapshot(semantic_reader_engine) as conn:
        stale = explain_operation(release, "derive", subject=binding, connection=conn).model_dump(
            mode="json"
        )
    check = next(item for item in stale["checks"] if item["contract_ref"] == "SnapshotBinding")
    assert check["status"] == "unavailable"


def test_actual_diff_preserves_selection_dependencies_and_declared_consumer_unknowns(
    semantic_db_engine,
    semantic_reader_engine,
    cli,
):
    """Change retained recipe inputs, rather than fabricating an analysis result."""
    import yaml

    bundle, deps, profile = report_inputs()
    path = "execution/implementation/capture/companion-projection-model.yaml"
    source = next(item for item in deps.artifacts if item.name == path)
    model = yaml.safe_load(source.content)
    declaration = model["classes"]["PublishedCoverageRow"]["annotations"]
    recipe = json.loads(declaration["cp:recipe"])
    recipe["predicate"] = {
        "all": [
            recipe["predicate"],
            {"equal": [{"field": ["c", "local_id"]}, {"constant": "selected-only"}]},
        ]
    }
    declaration["cp:recipe"] = json.dumps(recipe)
    changed = replace(
        deps,
        artifacts=tuple(
            SourceArtifact(item.name, yaml.safe_dump(model).encode()) if item.name == path else item
            for item in deps.artifacts
        ),
    )
    changed_bundle = replace(
        bundle,
        sources=tuple(
            SourceArtifact(item.name, item.content.replace(b"required: true", b"required: false"))
            for item in bundle.sources
        ),
    )
    before = prepare_release(bundle, deps, profile)
    after = prepare_release(changed_bundle, changed, profile)
    with semantic_db_engine.begin() as conn:
        persist_release(conn, bundle, deps, profile, before)
        persist_release(conn, changed_bundle, changed, profile, after)
    settings = Settings(
        database={
            "url": semantic_reader_engine.url.set(drivername="postgresql").render_as_string(
                hide_password=False
            )
        }
    )
    result = cli(
        "schema",
        "diff",
        before.release_id,
        after.release_id,
        "--json",
        settings=lambda: settings,
    )
    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    where = next(
        item
        for item in report["changes"]
        if item["model_ref"] == "projection:coverage"
        and item["aspect"] == "relational_dependencies"
    )
    assert "physical:kb.pdf_record_companion.local_id" in where["reason"]
    assert "ops.read_published_coverage_batch" in where["consumers"]
    assert "corpus_structure.serve.companion_export.export_companion_parquet" in where["consumers"]
    changed_class = next(item for item in report["changes"] if item["model_ref"] == "class:Thing")
    assert changed_class["members"] == [
        {
            "kind": "changed",
            "model_path": "class:Thing/properties/label/minimum_cardinality",
            "before": {"kind": "integer", "integer": 1},
            "after": {"kind": "null"},
        },
        {
            "kind": "changed",
            "model_path": "class:Thing/properties/label/required",
            "before": {"kind": "boolean", "boolean": True},
            "after": {"kind": "boolean", "boolean": False},
        },
    ]
    assert report["before_release"] == before.release_id
    assert report["after_release"] == after.release_id
    assert not report["complete"]
    assert any("helper body not analyzed" in value for value in report["unknowns"])

    async def journey():
        server = build_semantic_server(SemanticProjectSession(semantic_reader_engine, "impact"))
        async with Client(server) as client:
            answer = await client.call_tool(
                "compare_semantic_releases",
                dict(before=before.release_id, after=after.release_id),
            )
            assert answer.structured_content == report

    anyio.run(journey)


def test_alias_only_released_change_reaches_actual_cli_mcp_and_advice(
    semantic_db_engine, semantic_reader_engine, cli
):
    import yaml

    from corpus_structure.schema.pack import DOMAINS
    from corpus_structure.semantic.operation_reporting import compatibility_advice
    from corpus_structure.semantic.regeneration import prepare_pack

    bundle, deps, profile, _ = prepare_pack(DOMAINS / "statistics")
    path = "operation/domain-rules.yaml"
    source = next(item for item in deps.artifacts if item.name == path)
    policy = yaml.safe_load(source.content)
    old_policy = {
        **policy,
        "identity": {"alias_profile": "class-alias-input-1", "aliases": {}},
    }
    new_policy = {
        **policy,
        "identity": {
            "alias_profile": "class-alias-input-1",
            "aliases": {"rewrites": [{"match": "alpha", "replace": "beta"}]},
        },
    }
    releases = []
    for value in (old_policy, new_policy):
        dependencies = replace(
            deps,
            artifacts=tuple(
                SourceArtifact(item.name, yaml.safe_dump(value).encode())
                if item.name == path
                else item
                for item in deps.artifacts
            ),
        )
        release = prepare_release(bundle, dependencies, profile)
        with semantic_db_engine.begin() as conn:
            persist_release(conn, bundle, dependencies, profile, release)
        releases.append(release)
    before, after = releases
    settings = Settings(
        database={
            "url": semantic_reader_engine.url.set(drivername="postgresql").render_as_string(
                hide_password=False
            )
        }
    )
    result = cli(
        "schema",
        "diff",
        before.release_id,
        after.release_id,
        "--json",
        settings=lambda: settings,
    )
    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    expected_ref = "alias_policy:https://corpus-structure.dev/domains/statistics/DistributionFamily"
    alias = next(c for c in report["changes"] if c["model_ref"] == expected_ref)
    assert alias["aspect"] == "alias_normalization"
    assert "implementation:resolve_identity" in alias["consumers"]
    assert "analysis_profile:mathematical-interpretation/alignment_policy" in alias["consumers"]
    assert alias["members"][0]["model_path"].endswith("/classes/rewrites")

    async def journey():
        server = build_semantic_server(
            SemanticProjectSession(semantic_reader_engine, "alias-impact")
        )
        async with Client(server) as client:
            answer = await client.call_tool(
                "compare_semantic_releases",
                dict(before=before.release_id, after=after.release_id),
            )
            assert answer.structured_content == report

    anyio.run(journey)
    from corpus_structure.semantic.operation_reporting import compare_semantic_releases

    advice = compatibility_advice(compare_semantic_releases(before, after))
    assert any("implementation:resolve_identity" in text for text in advice)
    assert any(
        "analysis_profile:mathematical-interpretation/alignment_policy" in text for text in advice
    )
