"""Named serving consumers read actual admitted source/result bindings through real roles."""

import base64
import json
from pathlib import Path

import anyio
import pytest
from fastmcp import Client
from pydantic import BaseModel
from sqlalchemy import select

from corpus_structure.intervene.semantic_server import SemanticAgentSession, build_semantic_server
from corpus_structure.orchestrate.commands import finalize_bound_run
from corpus_structure.semantic.analytics import SPINE, load_packet
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.query import Explanation as FactExplanation
from corpus_structure.semantic.query import read_session
from corpus_structure.semantic.refusals import StaleSnapshot, WrongBinding
from corpus_structure.serve.explain import UnitExplanation, explain
from corpus_structure.serve.export import export_packet
from corpus_structure.serve.journey import QueryRefused, serve_query
from corpus_structure.serve.queries import GENERIC
from corpus_structure.serve.registry import build_registry
from corpus_structure.serve.results import (
    ClaimAnswer,
    FamilyAnswer,
    FindAnswer,
    RelationAnswer,
    StatementAnswer,
    TransformationAnswer,
)

from .test_agent_resubmission import lease_and_read, source_task


def completed(admin, writer, tmp_path, *, complete_coverage=False):
    prepared, run, task, locator = source_task(
        admin, writer, tmp_path / "source.html", composed=True, domain="statistics"
    )

    async def submit():
        async with Client(build_semantic_server(SemanticAgentSession(writer, run))) as client:
            unit = await lease_and_read(client, run, task)
            claims = [
                {
                    "id": item,
                    "subject": "person2" if name == "Bob" else "person",
                    "predicate": "https://example.org/name",
                    "object": {"kind": "text", "text": name},
                    "qualification": {"modality": "asserted", "polarity": True},
                    "establishment": "stated",
                    "evidence": [
                        {
                            "sentence": unit["sentences"][0]["id"],
                            "quote": "Alice is here.",
                            "role": "primary",
                        }
                    ],
                }
                for item, name in [("name1", "Alice"), ("name2", "Alice"), ("name3", "Bob")]
            ]
            result = await client.call_tool(
                "propose_claims",
                {
                    "task_id": task,
                    "batch": {
                        "unit_ref": locator,
                        "entities": [
                            {"id": "person", "class_iri": "https://example.org/Person"},
                            {"id": "person2", "class_iri": "https://example.org/Person"},
                        ],
                        "claims": claims,
                    },
                },
            )
            assert result.structured_content is not None
            assert result.structured_content["submission_disposition"] == "completed_accepted"

    anyio.run(submit)
    if complete_coverage:
        from types import SimpleNamespace

        from corpus_structure.core.method import CoverageDraft, UnitRef, UnitResult
        from corpus_structure.core.vocab import ObservationOutcome, TaskUnitType
        from corpus_structure.semantic.operations import (
            claim_tasks,
            complete_unit_result,
            create_task,
            record_method,
        )

        class WitnessConfig(BaseModel):
            pass

        method = SimpleNamespace(
            name="coverage.witness",
            version="1",
            family="extract",
            tier="deterministic",
            unit_type=TaskUnitType.RUN,
            Config=WitnessConfig,
            confidence_source=None,
        )
        with writer.begin() as conn:
            config = record_method(conn, method, "default", {}, "coverage-witness")
            task_id = create_task(
                conn,
                run_id=run,
                config_id=config,
                stage="extract",
                unit_type="run",
                unit_key="global",
                input_hash="coverage-witness",
            )
            claimed = claim_tasks(conn, run_id=run, config_id=config, holder="coverage-witness")[0]
            complete_unit_result(
                conn,
                task_id=task_id,
                attempt=claimed.attempt,
                holder="coverage-witness",
                prepared=prepared,
                method=method,
                configuration_hash="coverage-witness",
                source="coverage-witness",
                result=UnitResult(
                    ref=UnitRef(TaskUnitType.RUN, unit_key="global"),
                    outcome=ObservationOutcome.EMPTY,
                    coverage=(
                        CoverageDraft(
                            family="https://example.org/name",
                            scope="*",
                            outcome="complete",
                        ),
                    ),
                ),
            )
    finalize_bound_run(writer, run, "served-result")
    return prepared, run, task, locator


def test_named_semantic_pages_explanations_and_source_search(
    semantic_db_engine, semantic_writer_engine, semantic_reader_engine, tmp_path
):
    prepared, run, _task, locator = completed(semantic_db_engine, semantic_writer_engine, tmp_path)
    registry = build_registry(GENERIC)
    with (
        semantic_reader_engine.connect().execution_options(
            isolation_level="REPEATABLE READ"
        ) as conn,
        conn.begin(),
    ):
        conn.exec_driver_sql("SET TRANSACTION READ ONLY")
        first = serve_query(
            conn, registry, "claims", {"predicate": "https://example.org/name"}, run=run, max_rows=1
        )
        assert first.binding.release_id == prepared.release_id
        assert len(first.rows) == 1 and first.next_page_token
        second = serve_query(
            conn,
            registry,
            "claims",
            {"predicate": "https://example.org/name"},
            run=run,
            page_token=first.next_page_token,
            max_rows=1,
        )
        first_fact = json.loads(first.model_dump_json())["rows"][0]["fact"]
        second_fact = json.loads(second.model_dump_json())["rows"][0]["fact"]
        assert {first_fact["object"], second_fact["object"]} == {"Alice", "Bob"}
        assert first_fact["fact_id"] != second_fact["fact_id"]
        occurrences = serve_query(
            conn,
            registry,
            "claims",
            {"predicate": "https://example.org/name"},
            run=run,
            projection="occurrence",
        )
        occurrence_rows = json.loads(occurrences.model_dump_json())["rows"]
        assert sorted(row["fact"]["object"] for row in occurrence_rows) == ["Alice", "Alice", "Bob"]
        assert len({row["fact"]["occurrence_id"] for row in occurrence_rows}) == 3
        candidates = serve_query(
            conn,
            registry,
            "claims",
            {"predicate": "https://example.org/name", "include_candidates": True},
            run=run,
        )
        assert candidates.projection == "fact"
        filtered = serve_query(
            conn,
            registry,
            "claims",
            {"predicate": "https://example.org/name", "object": "Alice"},
            run=run,
        )
        assert filtered.rows and {
            row["fact"]["object"] for row in json.loads(filtered.model_dump_json())["rows"]
        } == {"Alice"}
        occurrence_filter = serve_query(
            conn,
            registry,
            "claims",
            {"predicate": "https://example.org/name", "object": "Alice"},
            run=run,
            projection="occurrence",
        )
        assert len(occurrence_filter.rows) == 2
        assert {
            row["fact"]["object"] for row in json.loads(occurrence_filter.model_dump_json())["rows"]
        } == {"Alice"}
        unknown = serve_query(
            conn,
            registry,
            "claims",
            {"predicate": "https://example.org/name", "subject": "missing"},
            run=run,
        )
        assert unknown.rows == [] and unknown.knowledge == "unknown"
        with pytest.raises(QueryRefused, match="size limit"):
            serve_query(
                conn,
                registry,
                "claims",
                {"predicate": "https://example.org/name"},
                run=run,
                max_chars=1,
            )
        with pytest.raises(WrongBinding, match="params"):
            serve_query(
                conn,
                registry,
                "claims",
                {"predicate": "https://example.org/name", "subject": "different"},
                run=run,
                page_token=first.next_page_token,
            )

        explanation = explain(conn, run, "claim", first_fact["fact_id"])
        assert isinstance(explanation.detail, FactExplanation)
        assert explanation.detail.supports and explanation.detail.evidence
        assert explanation.detail.evidence[0].source is not None
        assert explanation.detail.evidence[0].source.observation_key
        source = explain(conn, run, "unit", locator)
        assert isinstance(source.detail, UnitExplanation)
        assert any(t.included_in_cut for t in source.detail.tasks)
        assert source.detail.observations
        matches = serve_query(conn, registry, "find", {"text": "Alice"}, run=run)
        hits = [
            FindAnswer.model_validate(row)
            for row in matches.rows
            if row.get("source_selection") is not None
        ]
        assert len(hits) == 1
        hit = hits[0]
        assert hit.text is not None
        assert hit.text_is_excerpt is True and "<b>Alice</b>" in hit.text
        assert hit.source_uri == "source.html"
        assert hit.source_view_id is not None
        from corpus_structure.semantic.source_views import load_source_view

        selected = table("ops.run_source_view")
        assert (
            conn.scalar(
                select(selected.c.source_view_id).where(
                    selected.c.run_id == run, selected.c.source_view_id == hit.source_view_id
                )
            )
            == hit.source_view_id
        )
        view = load_source_view(conn, hit.source_view_id)
        assert view.text == "Alice is here."
        assert hit.projection_digest == view.ref.projection_digest
        pin = hit.source_selection
        assert pin is not None
        assert (pin.run_id, pin.task_id, pin.product_key, pin.content_digest) == (
            run,
            view.ref.native_product.task_id,
            view.ref.native_product.product_key,
            view.ref.native_product.content_digest,
        )
        assert (pin.section_pointer, pin.membership) == (
            view.ref.section_pointer,
            view.ref.membership,
        )
        token = json.loads(base64.urlsafe_b64decode(first.next_page_token))
        token["revision"] += 1
        with pytest.raises(StaleSnapshot, match="revision"):
            serve_query(
                conn,
                registry,
                "claims",
                {"predicate": "https://example.org/name"},
                run=run,
                page_token=base64.urlsafe_b64encode(json.dumps(token).encode()).decode(),
            )
        with pytest.raises(WrongBinding, match="projection"):
            serve_query(
                conn,
                registry,
                "claims",
                {"predicate": "https://example.org/name"},
                run=run,
                page_token=first.next_page_token,
                projection="occurrence",
            )


def test_full_projection_exports_and_cancel_cleanup(
    semantic_db_engine, semantic_writer_engine, semantic_reader_engine, tmp_path, monkeypatch
):
    import pyarrow.parquet as pq

    _, _run, _, _ = completed(semantic_db_engine, semantic_writer_engine, tmp_path)
    uri = semantic_reader_engine.url.render_as_string(hide_password=False).replace(
        "postgresql+psycopg:", "postgresql:"
    )
    with read_session(semantic_reader_engine, "served-result") as session:
        packet = load_packet(session, uri)
    parquet = export_packet(packet, tmp_path / "parquet")
    jsonl = export_packet(packet, tmp_path / "jsonl", format="jsonl")
    assert set(parquet["relations"]) == set(jsonl["relations"]) == set(SPINE)
    for name, relation in packet.relations.items():
        assert pq.read_table(tmp_path / "parquet" / f"{name}.parquet").equals(
            packet.to_table(name), check_metadata=True
        )
        assert (
            len((tmp_path / "jsonl" / f"{name}.jsonl").read_text().splitlines())
            == relation.num_rows
        )
    original = pq.ParquetWriter.write_batch
    count = 0

    def cancel(*args, **kwargs):
        nonlocal count
        count += 1
        if count == 2:
            raise KeyboardInterrupt()
        return original(*args, **kwargs)

    monkeypatch.setattr(pq.ParquetWriter, "write_batch", cancel)
    with pytest.raises(KeyboardInterrupt):
        export_packet(packet, tmp_path / "cancelled")
    assert not (tmp_path / "cancelled").exists()
    assert not list(tmp_path.glob(".semantic-export-*"))


def install_pack(admin, writer, name, entries, *, contexts=False):
    from dataclasses import replace

    from sqlalchemy import insert

    from corpus_structure.semantic import (
        PreparationProfile,
        ResolvedDependencies,
        SourceArtifact,
        SourceBundle,
        prepare_release,
    )
    from corpus_structure.semantic.consolidation import SourceItem, assemble
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.publication import EvidenceRow, SelectionRow, publish_batch
    from corpus_structure.semantic.releases import persist_release

    root = Path(__file__).resolve().parents[4]
    bundle = SourceBundle(
        "domain",
        (
            SourceArtifact(
                "semantic_core",
                (
                    root / "python/corpus-structure/src/corpus_structure/model/semantic/core.yaml"
                ).read_bytes(),
            ),
            SourceArtifact("domain", (root / f"domains/{name}/semantic.yaml").read_bytes()),
        ),
    )
    prepared = prepare_release(bundle)
    with admin.begin() as conn:
        persist_release(conn, bundle, ResolvedDependencies(), PreparationProfile(), prepared)
        conn.execute(insert(table("data.project")).values(project_id="pack"))
        conn.execute(
            insert(table("data.realization")).values(
                project_id="pack", realization_id="pack", release_id=prepared.release_id
            )
        )
    if callable(entries):
        entries = entries(prepared)
    entries = list(entries) + [
        (subject, cls, "id", subject, {"modality": "asserted", "polarity": True}, "Qualification")
        for subject, cls in sorted({(row[0], row[1]) for row in entries})
    ]
    evidence = (EvidenceRow("pack-evidence", "pack.html", "pack.html#p", "native-parser", "1"),)
    items = tuple(
        SourceItem(
            subject, cls, prop, obj, qualification, "pack-source", str(i), "stated", evidence, qcls
        )
        for i, (subject, cls, prop, obj, qualification, qcls) in enumerate(entries)
    )
    batch = assemble(prepared, "pack", "pack-test", items)
    if contexts:
        from corpus_structure.semantic.publication import OccurrenceContextRow

        batch = replace(
            batch,
            occurrence_context=tuple(
                OccurrenceContextRow(
                    o.occurrence_id,
                    "stmt",
                    "definiens"
                    if items[int(o.item)].property_name == "defined_as"
                    else "premise"
                    if items[int(o.item)].qualification["modality"] == "supposed"
                    else "conclusion",
                )
                for o in batch.occurrence
                if items[int(o.item)].subject in {"rv0", "rv1"}
                and items[int(o.item)].property_name in {"has_distribution", "defined_as"}
            ),
        )
    batch = replace(batch, selection=tuple(SelectionRow(f.fact_id) for f in batch.fact))
    publish_batch(writer, batch)
    return prepared, batch


def test_statistics_named_algorithms_and_exact_ownership(
    semantic_db_engine, semantic_writer_engine, semantic_reader_engine
):
    from corpus_structure.serve.protocol import QueryContext

    q = {"modality": "asserted", "polarity": True}
    entries = [
        ("normal", "DistributionFamily", "label", "Normal", q, "Qualification"),
        ("standard", "DistributionFamily", "label", "Standard normal", q, "Qualification"),
        ("construction", "FamilyConstruction", "label", "Location scale", q, "Qualification"),
        ("standard", "DistributionFamily", "special_case_of", "normal", q, "Qualification"),
        (
            "normal",
            "DistributionFamily",
            "member_of_construction",
            "construction",
            {**q, "base": "standard"},
            "StatisticsQualification",
        ),
        ("scale", "FamilyParameter", "family", "normal", q, "Qualification"),
        ("scale", "FamilyParameter", "canonical_name", "scale", q, "Qualification"),
        ("scale", "FamilyParameter", "parameter_role", "scale", q, "Qualification"),
        ("normal", "DistributionFamily", "has_parameter", "scale", q, "Qualification"),
    ]
    original_entries = entries

    def with_transformations(prepared):
        premise = {**q, "modality": "supposed"}
        ref = prepared.fact_identity(
            "pack", "rv0", prepared.expand_name("stat:has_distribution"), "normal", premise
        )
        return [
            *original_entries,
            ("rv0", "RandomVariable", "symbol", "X", q, "Qualification"),
            ("rv0", "RandomVariable", "scope_locator", "pack.html#stmt", q, "Qualification"),
            ("rv1", "RandomVariable", "symbol", "Y", q, "Qualification"),
            ("rv1", "RandomVariable", "scope_locator", "pack.html#stmt", q, "Qualification"),
            ("rv0", "RandomVariable", "has_distribution", "normal", premise, "Qualification"),
            (
                "rv1",
                "RandomVariable",
                "has_distribution",
                "standard",
                {**q, "condition": {"kind": "claim", "ref": ref}},
                "Qualification",
            ),
            (
                "rv1",
                "RandomVariable",
                "defined_as",
                {"kind": "formula", "language": "latex", "expression": "X + 1"},
                {**q, "modality": "defined"},
                "Qualification",
            ),
            ("stmt", "SourceStatement", "locator", "pack.html#stmt", q, "Qualification"),
        ]

    _prepared, _batch = install_pack(
        semantic_db_engine,
        semantic_writer_engine,
        "statistics",
        with_transformations,
        contexts=True,
    )
    registry = build_registry(GENERIC, Path(__file__).resolve().parents[4] / "domains/statistics")
    with read_session(semantic_reader_engine, "pack") as session:
        ctx = QueryContext(0, session.connection)
        ctx.__dict__["session"] = session

        def run[T: BaseModel](name, params, result: type[T]) -> list[T]:
            query = registry[name]
            return [
                result.model_validate(row.row)
                for row in query.rows(ctx, query.params.model_validate(params))
            ]

        referenced = run(
            "claims", {"predicate": "stat:special_case_of", "object": "Normal"}, ClaimAnswer
        )
        assert [(row.fact.subject.entity_id, row.fact.object) for row in referenced] == [
            ("standard", "normal")
        ]
        explicit_id = run(
            "claims", {"predicate": "stat:special_case_of", "object": "normal"}, ClaimAnswer
        )
        assert [row.fact.fact_id for row in referenced] == [row.fact.fact_id for row in explicit_id]
        profile = run("family_profile", {"family": "normal"}, ClaimAnswer)
        assert {row.fact.property_iri.rsplit("/", 1)[-1] for row in profile} >= {
            "family",
            "canonical_name",
            "parameter_role",
            "has_parameter",
            "member_of_construction",
        }
        mapping = run(
            "parameter_mapping", {"family": "Normal", "construction": "Location scale"}, ClaimAnswer
        )
        assert any(
            row.fact.qualification is not None
            and row.fact.qualification.__class__.__name__ == "StatisticsQualification"
            and row.fact.qualification.model_dump()["base"] == "standard"
            for row in mapping
        )
        families = run(
            "families_where", {"predicate": "stat:parameter_role", "value": "scale"}, FamilyAnswer
        )
        assert [row.family.entity_id for row in families] == ["normal"]
        relations = run(
            "relations_between", {"a": "Standard normal", "b": "Normal"}, RelationAnswer
        )
        assert len(relations) == 1 and relations[0].depth == 1
        assert relations[0].claims[0].fact.property_iri.endswith("/special_case_of")
        assert run("construction_profile", {"construction": "Location scale"}, ClaimAnswer)
        transformations = run("transformations_of", {"family": "Normal"}, TransformationAnswer)
        assert len(transformations) == 1
        assert transformations[0].conclusion.fact.subject.entity_id == "rv1"
        assert transformations[0].premises[0].fact.subject.entity_id == "rv0"
        assert transformations[0].definiens[0].fact.object.expression == "X + 1"
        statements = run("statement", {"key": "stmt"}, StatementAnswer)
        assert len(statements) == 1 and statements[0].statement.entity_id == "stmt"


def test_ownership_uses_declared_qualification_type_and_exact_scale(
    semantic_db_engine, semantic_writer_engine, semantic_reader_engine
):
    from decimal import Decimal

    from corpus_structure.serve.protocol import QueryContext

    q = {"modality": "asserted", "polarity": True}
    interval = {
        "kind": "validity_interval",
        "start": {"kind": "partial_date", "lexical": "2020-01-01"},
        "start_incl": True,
        "end": {"kind": "partial_date", "lexical": "2020-12-31"},
        "end_incl": False,
    }
    entries = [
        ("org", "Organization", "registry_id", "Org101", q, "Qualification"),
        ("org", "Organization", "label", "Owner", q, "Qualification"),
        ("asset", "Asset", "label", "Asset X", q, "Qualification"),
        (
            "org",
            "Organization",
            "owns",
            "asset",
            {
                **q,
                "share": {"kind": "number", "number": Decimal("0.5000")},
                "filing_ref": "filing-A",
                "valid_time": interval,
            },
            "ToyQualification",
        ),
    ]
    _, _batch = install_pack(semantic_db_engine, semantic_writer_engine, "toy", entries)
    registry = build_registry(GENERIC, Path(__file__).resolve().parents[4] / "domains/toy")
    with read_session(semantic_reader_engine, "pack") as session:
        ctx = QueryContext(0, session.connection)
        ctx.__dict__["session"] = session
        query = registry["ownership_at"]

        def rows(at):
            return [
                p.row.model_dump(mode="python", serialize_as_any=True)
                for p in query.rows(
                    ctx, query.params.model_validate({"asset": "Asset X", "date": at})
                )
            ]

        current = rows("2020-06-01")
        assert len(current) == 1 and current[0]["applicability"] == "established"
        assert (
            current[0]["claim"]["fact"]["qualification"]["share"]["number"].as_tuple().exponent
            == -4
        )
        assert current[0]["claim"]["fact"]["qualification"]["filing_ref"] == "filing-A"
        assert rows("2020-12-31")[0]["applicability"] == "not_applicable"


def test_real_cli_query_explain_and_export_dispatch(
    semantic_db_engine, semantic_writer_engine, semantic_reader_engine, tmp_path, cli
):
    from corpus_structure.settings import Settings

    _, run, _, locator = completed(semantic_db_engine, semantic_writer_engine, tmp_path)
    settings = Settings(
        database={
            "url": semantic_reader_engine.url.set(drivername="postgresql").render_as_string(
                hide_password=False
            )
        }
    )
    queried = cli(
        "query",
        "claims",
        "--run",
        str(run),
        "--param",
        "predicate=https://example.org/name",
        "--max-rows",
        "1",
        "--json",
        settings=lambda: settings,
    )
    assert queried.exit_code == 0, queried.output
    page = json.loads(queried.stdout)
    assert page["binding"]["realization_id"] == "served-result" and page["next_page_token"]
    continued = cli(
        "query",
        "claims",
        "--param",
        "predicate=https://example.org/name",
        "--page-token",
        page["next_page_token"],
        "--json",
        settings=lambda: settings,
    )
    assert continued.exit_code == 0, continued.output
    assert len(json.loads(continued.stdout)["rows"]) == 1
    unknown_prefix = cli(
        "query",
        "claims",
        "--run",
        str(run),
        "--param",
        "predicate=bogus:name",
        "--json",
        settings=lambda: settings,
    )
    assert unknown_prefix.exit_code == 1
    assert json.loads(unknown_prefix.stdout)["error"]["code"] == "SemanticRefusal"
    malformed = json.loads(base64.urlsafe_b64decode(page["next_page_token"]))
    malformed["position"] = 1
    malformed_token = base64.urlsafe_b64encode(json.dumps(malformed).encode()).decode()
    invalid_cursor = cli(
        "query",
        "claims",
        "--param",
        "predicate=https://example.org/name",
        "--page-token",
        malformed_token,
        "--json",
        settings=lambda: settings,
    )
    assert invalid_cursor.exit_code == 1
    assert json.loads(invalid_cursor.stdout)["error"]["code"] == "StaleToken"
    for field, changed, code, reason in (
        ("query", "entities", "WrongBinding", "wrong_query"),
        ("params", "other", "WrongBinding", "wrong_parameters"),
        ("version", "removed", "StaleSnapshot", "stale_version"),
        ("release", "release:other", "WrongRelease", "wrong_release"),
        ("realization", "other", "WrongBinding", "wrong_realization"),
        ("revision", 999, "StaleSnapshot", "stale_revision"),
        ("projection", "fact", "WrongBinding", "wrong_projection"),
        ("arithmetic", "rounded", "WrongBinding", "wrong_profile"),
    ):
        body = json.loads(base64.urlsafe_b64decode(page["next_page_token"]))
        body[field] = changed
        token = base64.urlsafe_b64encode(json.dumps(body).encode()).decode()
        refused = cli(
            "query",
            "claims",
            "--param",
            "predicate=https://example.org/name",
            "--page-token",
            token,
            "--json",
            settings=lambda: settings,
        )
        assert refused.exit_code == 1, refused.output
        error = json.loads(refused.stdout)["error"]
        assert (error["code"], error["reason"]) == (code, reason)
    fact = page["rows"][0]["fact"]["fact_id"]
    explained = cli(
        "explain", "claim", fact, "--run", str(run), "--json", settings=lambda: settings
    )
    assert explained.exit_code == 0, explained.output
    assert json.loads(explained.stdout)["detail"]["fact_id"] == fact
    unit = cli("explain", "unit", locator, "--run", str(run), "--json", settings=lambda: settings)
    assert unit.exit_code == 0, unit.output
    assert json.loads(unit.stdout)["detail"]["observations"]
    exported = cli(
        "export",
        "--out",
        str(tmp_path / "cli-export"),
        "--run",
        str(run),
        "--format",
        "parquet",
        "--json",
        settings=lambda: settings,
    )
    assert exported.exit_code == 0, exported.output
    result = json.loads(exported.stdout)
    assert result["manifest"]["binding"]["realization_id"] == "served-result"
    assert (tmp_path / "cli-export" / "manifest.json").is_file()


def test_empty_named_continuation_does_not_assert_whole_query_absence(
    semantic_db_engine, semantic_writer_engine, semantic_reader_engine, tmp_path
):
    from corpus_structure.semantic.query import read_snapshot

    _, run, _, _ = completed(
        semantic_db_engine, semantic_writer_engine, tmp_path, complete_coverage=True
    )
    registry = build_registry(GENERIC)
    params = {"predicate": "https://example.org/name"}
    with read_snapshot(semantic_reader_engine) as conn:
        first = serve_query(conn, registry, "claims", params, run=run, max_rows=1)
        assert first.rows and first.next_page_token
        assert any(c.scope == "*" and c.outcome == "complete" for c in first.coverage)
        body = json.loads(base64.urlsafe_b64decode(first.next_page_token))
        body["position"] = "zzzzzzzzzz"
        token = base64.urlsafe_b64encode(json.dumps(body).encode()).decode()
        empty = serve_query(conn, registry, "claims", params, run=run, page_token=token)
        assert empty.rows == [] and empty.next_page_token is None and not empty.truncated
        assert empty.coverage_diagnostic is None and empty.knowledge == "unknown"
        absent = serve_query(conn, registry, "claims", {**params, "subject": "missing"}, run=run)
        assert absent.rows == [] and absent.knowledge == "absent"
