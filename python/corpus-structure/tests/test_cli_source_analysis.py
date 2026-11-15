"""Native source analysis routes immutable intent; rendering retains separate custody."""

import pytest


def test_native_request_help_requires_no_settings_and_names_exact_intent(cli):
    def refused():
        raise AssertionError("help resolved settings")

    for command in ("native-request", "native-render"):
        result = cli("source", command, "--help", settings=refused)
        assert result.exit_code == 0, result.output


def test_native_request_routes_exact_demand_only_resume(cli, monkeypatch):
    from corpus_structure.cli import demands

    seen = []
    monkeypatch.setattr(demands, "execute_request", lambda ctx, **values: seen.append(values))
    result = cli(
        "source",
        "native-request",
        "--demand",
        "demand:retained",
        "--source-root",
        "/retained",
        "--json",
    )
    assert result.exit_code == 0, result.output
    assert len(seen) == 1 and seen[0]["demand"] == "demand:retained"
    assert seen[0]["request"] is None and seen[0]["action"] == "source.native-request"


def test_native_request_rejects_missing_intent_without_an_execution_side_effect(cli, monkeypatch):
    from corpus_structure.cli import demands

    def refused(*args, **kwargs):
        pytest.fail("invalid selection reached execution")

    monkeypatch.setattr(demands, "execute_request", refused)
    result = cli("source", "native-request", "--json")
    assert result.exit_code != 0
    assert "--request or --demand" in result.output


@pytest.mark.parametrize("command", ["native-render", "native-request"])
def test_current_source_commands_share_retained_demand_execution(cli, monkeypatch, command):
    from corpus_structure.cli import demands

    seen = []
    monkeypatch.setattr(demands, "execute_request", lambda ctx, **values: seen.append(values))
    result = cli("source", command, "--demand", "demand:actual", "--json")
    assert result.exit_code == 0, result.output
    assert seen[0]["demand"] == "demand:actual"
    assert seen[0]["action"] == "source." + command


def test_render_does_not_accept_run_and_task_aliases(cli):
    result = cli("source", "native-render", "17", "31", "--json")
    assert result.exit_code != 0


def test_visual_route_acquires_native_read_with_effects_and_preserves_exact_scope(cli, monkeypatch):
    from contextlib import contextmanager
    from decimal import Decimal

    from sqlalchemy import create_engine

    from corpus_structure.semantic.data_operation_json import json_loads

    engine = create_engine("sqlite://")
    seen = []

    @contextmanager
    def opened(*args, **kwargs):
        assert kwargs["purpose"] == "read"
        yield engine

    def routed(connection, demand, **kwargs):
        assert connection.in_transaction()
        assert connection.get_execution_options().get("postgresql_readonly") is not True
        seen.append((demand, kwargs["project_id"]))
        return {
            "cut": {"analyzed_scope": {"ratio": Decimal("0.123456789012345678901")}},
            "pages": [],
        }

    monkeypatch.setattr("corpus_structure.semantic.runtime.open_runtime_engine", opened)
    monkeypatch.setattr(
        "corpus_structure.semantic.visual_routing.read_demand_visual_routes", routed
    )
    try:
        result = cli("source", "visual-route", "demand:A", "--project", "project:A", "--json")
        assert result.exit_code == 0, result.output
        assert json_loads(result.stdout)["cut"]["analyzed_scope"]["ratio"] == Decimal(
            "0.123456789012345678901"
        )
        assert seen == [("demand:A", "project:A")]
    finally:
        engine.dispose()
