"""Current interpretation commands retain exact authored scope and real selected identity."""

from contextlib import contextmanager
from decimal import Decimal

import pytest

from corpus_structure.semantic.data_operation_json import json_loads


@pytest.fixture
def interpreted_runtime(monkeypatch):
    from corpus_structure.semantic import demand_results, runtime

    opened = []

    @contextmanager
    def engine(settings, application_name, *, purpose):
        opened.append(purpose)
        yield object()

    @contextmanager
    def snapshot(engine):
        yield object()

    monkeypatch.setattr(runtime, "open_runtime_engine", engine)
    monkeypatch.setattr(demand_results, "selected_read_snapshot", snapshot)
    return opened


def test_authoring_keeps_exact_json_scope_through_current_native_request(
    cli, tmp_path, interpreted_runtime, monkeypatch
):
    from corpus_structure.semantic import releases
    from corpus_structure.serve import interpretation_authoring

    content = (
        '{"project_id":"project:one","release_id":"release:one","runtime_id":"runtime:one",'
        '"roots":[{"subject":"subject:one","original_source":"original:one","analyzed_scope":{"fraction":0.123456789012345678901}}],'
        '"targets":["operation:one"],"execution_profile":"execution:one"}'
    )
    path = tmp_path / "authored.json"
    path.write_text(content)
    monkeypatch.setattr(releases, "open_release", lambda *args: object())
    seen = []

    def author(engine, prepared, *, request):
        seen.append(request)
        return {
            "analyzed_scope": request.roots[0].analyzed_scope,
            "demand_id": "demand:real-request",
        }

    monkeypatch.setattr(interpretation_authoring, "author_interpretations", author)
    result = cli("interpretations", "author", "release:one", str(path), "--json")
    assert result.exit_code == 0, (result.output, result.exception)
    number = Decimal("0.123456789012345678901")
    assert seen[0].roots[0].analyzed_scope["fraction"] == number
    assert json_loads(result.stdout)["body"]["analyzed_scope"]["fraction"] == number
    assert interpreted_runtime == ["write"]


def test_review_uses_actual_selected_proposal_request_without_integer_cut_alias(
    cli, tmp_path, interpreted_runtime, monkeypatch
):
    from corpus_structure.serve import interpretations

    path = tmp_path / "selected.json"
    path.write_text(
        '{"project_id":"project:one","demand_id":"demand:one","product_id":"product:one","member_id":"claim:c1"}'
    )
    seen = []

    def inspect(connection, request):
        seen.append(request)
        return interpretations.answer(
            "selected_private_proposals", {"items": [], "knowledge": "unknown"}
        )

    monkeypatch.setattr(interpretations, "inspect_selected_proposals", inspect)
    result = cli("interpretations", "review", str(path), "--json")
    assert result.exit_code == 0, (result.output, result.exception)
    assert (
        seen[0].demand_id == "demand:one"
        and seen[0].product_id == "product:one"
        and seen[0].member_id == "claim:c1"
    )
    assert "original_source" not in seen[0].model_fields_set
    assert interpreted_runtime == ["read"]
    for arguments in (
        ("review", "1", "2"),
        ("records", "1", "2", "3"),
        ("measurements", "1", "2", "3"),
    ):
        assert cli("interpretations", *arguments, "--json").exit_code != 0
    assert len(seen) == 1


def test_groups_reads_complete_candidate_universe_and_exact_reading_root(
    cli, tmp_path, interpreted_runtime, monkeypatch
):
    from corpus_structure.serve import interpretations

    path = tmp_path / "groups.json"
    path.write_text('{"project_id":"project:one","demand_id":"demand:one","roots":[{"product_id":"product:one","member_id":"record:one","interpretation_id":"reading:one"}]}')
    seen = []

    def inspect(connection, request):
        seen.append(request)
        return interpretations.answer("grouped_source_record_interpretations", {"items": [], "knowledge": "unknown"})

    monkeypatch.setattr(interpretations, "group_selected_interpretations", inspect)
    result = cli("interpretations", "groups", str(path), "--json")
    assert result.exit_code == 0, (result.output, result.exception)
    assert seen[0].roots[0].product_id == "product:one"
    assert seen[0].roots[0].member_id == "record:one"
    assert seen[0].roots[0].interpretation_id == "reading:one"
    assert interpreted_runtime == ["read"]
