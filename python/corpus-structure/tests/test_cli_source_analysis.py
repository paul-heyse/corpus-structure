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
    result = cli("source", "native-request", "--demand", "demand:retained", "--source-root", "/retained", "--json")
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
