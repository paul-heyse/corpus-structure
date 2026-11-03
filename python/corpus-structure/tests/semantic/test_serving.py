"""Named serving consumers read actual admitted source/result bindings through real roles."""

import base64
import json
from pathlib import Path

import pytest
from pydantic import BaseModel
from sqlalchemy import select

from corpus_structure.semantic.analytics import SPINE, load_packet
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.query import Explanation as FactExplanation
from corpus_structure.semantic.query import read_session
from corpus_structure.semantic.query_compatibility import open_query_registry
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

from .serving_scenarios import (
    build_completed_serving_case,
    install_pack_scenario,
)
from .serving_scenarios import (
    serving_read_scenario as serving_read_scenario,
)
from .serving_scenarios import (
    serving_scenario_seed as serving_scenario_seed,
)


def test_named_semantic_pages_explanations_and_source_search(serving_read_scenario):
    prepared, run, _task, locator = (
        serving_read_scenario.prepared,
        serving_read_scenario.run,
        serving_read_scenario.task,
        serving_read_scenario.locator,
    )
    registry = open_query_registry(
        prepared, Path(__file__).resolve().parents[4] / "domains/statistics"
    )
    with (
        serving_read_scenario.reader.connect().execution_options(
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

        def subject_classes(row):
            return frozenset(
                membership["class_iri"] for membership in row["subject"]["memberships"]
            )

        assert {
            (
                subject_classes(row),
                row["object"],
                row["qualification"]["modality"],
                row["qualification"]["polarity"],
            )
            for row in (first_fact, second_fact)
        } == {
            (frozenset({"https://example.org/Person"}), "Alice", "asserted", True),
            (frozenset({"https://example.org/Person"}), "Bob", "asserted", True),
        }
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
        assert {
            (
                subject_classes(row["fact"]),
                row["fact"]["object"],
                row["fact"]["item"],
                row["fact"]["qualification"]["modality"],
                row["fact"]["qualification"]["polarity"],
            )
            for row in occurrence_rows
        } == {
            (frozenset({"https://example.org/Person"}), "Alice", "claims/0", "asserted", True),
            (frozenset({"https://example.org/Person"}), "Alice", "claims/1", "asserted", True),
            (frozenset({"https://example.org/Person"}), "Bob", "claims/2", "asserted", True),
        }
        alice_subjects = {
            row["fact"]["subject"]["entity_id"]
            for row in occurrence_rows
            if row["fact"]["object"] == "Alice"
        }
        bob_subjects = {
            row["fact"]["subject"]["entity_id"]
            for row in occurrence_rows
            if row["fact"]["object"] == "Bob"
        }
        assert len(alice_subjects) == len(bob_subjects) == 1
        assert alice_subjects.isdisjoint(bob_subjects)
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

        alice_id = next(
            row["fact_id"] for row in (first_fact, second_fact) if row["object"] == "Alice"
        )
        explanation = explain(conn, run, "claim", alice_id)
        assert isinstance(explanation.detail, FactExplanation)
        assert {support.item for support in explanation.detail.supports} == {
            "claims/0",
            "claims/1",
        }
        assert len({support.source for support in explanation.detail.supports}) == 1
        linked_evidence = {
            evidence_id
            for support in explanation.detail.supports
            for evidence_id in support.evidence_ids
        }
        assert linked_evidence
        assert {evidence.evidence_id for evidence in explanation.detail.evidence} == linked_evidence
        assert {evidence.source_uri for evidence in explanation.detail.evidence} == {"source.html"}
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


def test_full_projection_exports_and_cancel_cleanup(serving_read_scenario, tmp_path, monkeypatch):
    import pyarrow.parquet as pq

    _run = serving_read_scenario.run
    uri = serving_read_scenario.reader.url.render_as_string(hide_password=False).replace(
        "postgresql+psycopg:", "postgresql:"
    )
    with read_session(serving_read_scenario.reader, "served-result") as session:
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

    _prepared, _batch = install_pack_scenario(
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
    _, _batch = install_pack_scenario(semantic_db_engine, semantic_writer_engine, "toy", entries)
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


def test_real_cli_query_explain_and_export_dispatch(serving_read_scenario, tmp_path, cli):
    from corpus_structure.settings import Settings

    run, locator = serving_read_scenario.run, serving_read_scenario.locator
    settings = Settings(
        database={
            "url": serving_read_scenario.reader.url.set(drivername="postgresql").render_as_string(
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
    if queried.exception is not None:
        raise queried.exception.with_traceback(queried.exc_info[2] if queried.exc_info else None)
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


def test_real_cli_query_implementation_edit_and_bound_followups(
    semantic_db_engine, semantic_writer_engine, semantic_reader_engine, tmp_path, cli, monkeypatch
):
    from corpus_structure.schema import pack as pack_module
    from corpus_structure.settings import Settings

    packs = tmp_path / "packs"
    pack = packs / "statistics"
    pack.mkdir(parents=True)
    plugin = (
        "from corpus_structure.serve.queries import Claims\n"
        "class Probe(Claims):\n    name, version = 'probe', '1'\nQUERIES=[Probe()]\n"
    )
    (pack / "queries.py").write_text(plugin)
    prepared, run, _, locator = build_completed_serving_case(
        semantic_db_engine, semantic_writer_engine, tmp_path, query_pack=pack
    )
    original = open_query_registry(prepared, pack)
    monkeypatch.setattr(pack_module, "DOMAINS", packs)
    settings = Settings(
        database={
            "url": semantic_reader_engine.url.set(drivername="postgresql").render_as_string(
                hide_password=False
            )
        }
    )

    def invoke(*args):
        result = cli(*args, settings=lambda: settings)
        # Expected semantic refusals are Click exits and retain their JSON envelope;
        # unexpected implementation errors need their full owning trace immediately.
        if result.exception is not None and not isinstance(result.exception, SystemExit):
            raise result.exception.with_traceback(result.exc_info[2] if result.exc_info else None)
        return result

    args = (
        "query",
        "probe",
        "--run",
        str(run),
        "--param",
        "predicate=https://example.org/name",
        "--max-rows",
        "1",
        "--json",
    )
    first = invoke(*args)
    assert first.exit_code == 0, first.output
    page = json.loads(first.stdout)
    assert page["query_contract"] == original["probe"].contract
    continued = invoke(
        "query",
        "probe",
        "--page-token",
        page["next_page_token"],
        "--param",
        "predicate=https://example.org/name",
        "--json",
    )
    assert continued.exit_code == 0, continued.output
    assert {
        page["rows"][0]["fact"]["object"],
        json.loads(continued.stdout)["rows"][0]["fact"]["object"],
    } == {"Alice", "Bob"}
    (pack / "queries.py").write_text("raise AssertionError('unadmitted import')\n" + plugin)
    for request in (
        args,
        ("query", "probe", "--page-token", page["next_page_token"], "--json"),
        ("explain", "unit", locator, "--query-token", page["next_page_token"], "--json"),
    ):
        refused = invoke(*request)
        assert refused.exit_code == 1, refused.output
        assert json.loads(refused.stdout)["error"]["reason"] == "incompatible_query"
    # Primitive export remains independent of named-query support.
    exported = invoke(
        "export",
        "--out",
        str(tmp_path / "independent-export"),
        "--run",
        str(run),
        "--format",
        "jsonl",
        "--json",
    )
    assert exported.exit_code == 0, exported.output

    (pack / "queries.py").write_text("# explicitly reviewed source-only change\n" + plugin)
    entries = [
        dict(
            query=name,
            contract=original[name].contract,
            implementation=original[name].producing_implementation,
            evidence="independent Alice/Bob rows and retained unit/evidence",
        )
        for name in ("probe", "evidence")
    ]
    (pack / "query-bundle.json").write_text(json.dumps({"compatibility": entries}))
    supported = invoke(*args)
    assert supported.exit_code == 0, supported.output
    current = json.loads(supported.stdout)
    assert current["query_contract"] == page["query_contract"]
    assert current["implementation"] != page["implementation"]
    explained = invoke(
        "explain", "unit", locator, "--query-token", current["next_page_token"], "--json"
    )
    assert explained.exit_code == 0, explained.output
    assert json.loads(explained.stdout)["query_binding"]["contract"] == page["query_contract"]
    evidence = invoke(
        "query",
        "evidence",
        "--origin-token",
        current["next_page_token"],
        "--param",
        "key=" + current["rows"][0]["fact"]["fact_id"],
        "--json",
    )
    assert evidence.exit_code == 0, evidence.output
    assert json.loads(evidence.stdout)["origin_binding"]["contract"] == page["query_contract"]
    assert json.loads(evidence.stdout)["rows"]
    wrong_run = invoke(
        "query",
        "evidence",
        "--origin-token",
        current["next_page_token"],
        "--run",
        str(run + 1),
        "--param",
        "key=" + current["rows"][0]["fact"]["fact_id"],
        "--json",
    )
    assert wrong_run.exit_code == 1, wrong_run.output
    assert json.loads(wrong_run.stdout)["error"]["reason"] == "wrong_realization"
    old = invoke(
        "query",
        "probe",
        "--page-token",
        page["next_page_token"],
        "--param",
        "predicate=https://example.org/name",
        "--json",
    )
    assert old.exit_code == 1
    assert json.loads(old.stdout)["error"]["reason"] == "incompatible_query"


def test_empty_named_continuation_does_not_assert_whole_query_absence(
    semantic_db_engine, semantic_writer_engine, semantic_reader_engine, tmp_path
):
    from corpus_structure.semantic.query import read_snapshot

    prepared, run, _, _ = build_completed_serving_case(
        semantic_db_engine, semantic_writer_engine, tmp_path, complete_coverage=True
    )
    registry = open_query_registry(
        prepared, Path(__file__).resolve().parents[4] / "domains/statistics"
    )
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
