"""Explicit policy selection and unchanged phase0 dispatch, without database access."""

from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from corpus_structure.orchestrate.semantic import BoundRunReport
from corpus_structure.semantic.product_reference import ProductReference


@pytest.mark.parametrize(
    "arguments",
    [
        ["--extraction-policy", "m1-candidate"],
        ["--m1-configuration", "described"],
        ["--extraction-policy", "m1-candidate", "--m1-configuration", "unknown"],
        ["--integrated-product-task", "23"],
        [
            "--integrated-product-task",
            "23",
            "--integrated-product-key",
            "integrated",
            "--integrated-product-digest",
            "bad",
        ],
    ],
)
def test_refused_pin_never_opens_database(cli, monkeypatch, arguments):
    from corpus_structure.cli import orchestrate

    def forbidden(*args, **kwargs):
        pytest.fail("invalid explicit selection opened a database")

    monkeypatch.setattr(orchestrate, "ENGINE", forbidden)
    result = cli("run", *arguments)
    assert result.exit_code == 2
    assert any(word in result.output for word in ("pin", "together", "SHA-256", "configuration"))


@pytest.mark.parametrize(
    ("m1", "configuration"),
    [(False, "default"), (True, "default"), (True, "described"), (True, "source-only")],
)
def test_cli_dispatch_records_explicit_policy_and_leaves_phase0_graph(
    cli, monkeypatch, m1, configuration
):
    from corpus_structure.cli import orchestrate
    from corpus_structure.orchestrate import commands
    from corpus_structure.semantic import runtime

    engine = MagicMock()

    @contextmanager
    def opened(settings):
        yield engine

    monkeypatch.setattr(orchestrate, "ENGINE", opened)
    graph, registry = object(), object()
    monkeypatch.setattr(
        orchestrate,
        "PHASE0",
        lambda: dict(graph=graph, registry_for=registry, domains=Path("/controlled/domains")),
    )
    monkeypatch.setattr(runtime, "resolve_source_binding", lambda *a, **kw: ("release", "input"))
    start = MagicMock(
        return_value=BoundRunReport(
            run_id=17, status="source_ready", release_id="release", realization_id="input"
        )
    )
    monkeypatch.setattr(commands, "start_bound_run", start)
    args = (
        [
            "--extraction-policy",
            "m1-candidate",
            "--integrated-product-task",
            "23",
            "--integrated-product-key",
            "integrated",
            "--integrated-product-digest",
            "a" * 64,
        ]
        if m1
        else []
    )
    if m1:
        args += ["--m1-configuration", configuration]
    result = cli("run", *args, "--json")
    assert result.exit_code == 0, (result.output, result.exception)
    kwargs = start.call_args.kwargs
    assert kwargs["extraction_policy"] == ("m1-candidate" if m1 else "phase0")
    if m1:
        assert kwargs["m1_configuration"] == configuration
        assert kwargs["integrated_product"] == ProductReference(23, "integrated", "a" * 64)
        assert "graph" not in kwargs and "registry_for" not in kwargs
    else:
        assert kwargs["m1_configuration"] == "default"
        assert kwargs["graph"] is graph and kwargs["registry_for"] is registry
        assert kwargs["integrated_product"] is None
