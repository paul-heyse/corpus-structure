"""Explicit full-book selection retains intent and exact original custody."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from corpus_structure.cli.app import app
from corpus_structure.orchestrate import commands, phase0
from corpus_structure.semantic.product_reference import ProductReference

ROOT = Path(__file__).resolve().parents[4]


@pytest.mark.parametrize("command", ["run", "ingest", "regenerate"])
@pytest.mark.parametrize("selection", ["--slice", "--scope"])
def test_whole_document_conflict_refuses_before_execution(command, selection):
    result = CliRunner().invoke(app, [command, "--whole-document", selection, "selected"])
    assert result.exit_code == 2
    assert "mutually exclusive" in result.output


def test_resume_refuses_new_source_projection():
    for args in (["--whole-document"], ["--source-membership", "direct"]):
        result = CliRunner().invoke(app, ["regenerate", "--resume-run", "17", *args])
        assert result.exit_code == 2
        assert "retains its original source selection" in result.output


def test_projection_binding_freezes_nondefault_original_and_keeps_pack_unchanged():
    registry = phase0.registry(ROOT / "domains/statistics")
    prior = registry.overlay("ingest.pdf_integrated", "default")
    pin = ProductReference(23, "integrated", "a" * 64)
    selected = phase0.bind_pdf_selection(
        phase0.bind_pdf_source(registry, pin, input_role="integrated"),
        document=SimpleNamespace(source_uri="grinstead_snell/book.pdf"), membership="direct",
    )
    cfg = selected.overlay("ingest.pdf_integrated", "default")
    assert cfg.originals == ("grinstead_snell/book.pdf",)
    assert cfg.membership == "direct" and cfg.integrated_product == pin
    assert registry.overlay("ingest.pdf_integrated", "default") == prior


@pytest.mark.parametrize("whole", [False, True])
def test_explicit_whole_document_bypasses_default_scope_and_is_frozen(monkeypatch, tmp_path, whole):
    from corpus_structure.orchestrate import semantic
    from corpus_structure.semantic import releases

    pack = tmp_path / "statistics"
    pack.mkdir()
    for name in ("methods.yaml", "guideline.md", "policies.yaml"):
        (pack / name).write_bytes((ROOT / "domains/statistics" / name).read_bytes())
    (pack / "slices.yaml").write_text(
        "default_scope: limited\nslices:\n  limited:\n    - native_sections: [Subset]\n"
    )
    conn = MagicMock()
    conn.execute.return_value.mappings.return_value.one.return_value = dict(release_id="release", data_revision=1)
    conn.execute.return_value.mappings.return_value.__iter__.side_effect = lambda: iter([
        dict(id=1, key="book", content_hash="a" * 64, mime="application/pdf", meta={})
    ])
    engine = MagicMock()
    engine.connect.return_value.__enter__.return_value = conn
    monkeypatch.setattr(releases, "load_release", lambda *a: SimpleNamespace(release_id="release"))
    started = MagicMock(return_value="captured")
    monkeypatch.setattr(semantic, "run_source_methods", started)
    result = commands.start_bound_run(
        engine, release_id="release", realization_id="source", project_id="project",
        domain="statistics", domains=tmp_path, method_settings=None,
        whole_document=whole, source_membership="direct", source_only=True,
    )
    assert result == "captured"
    options = started.call_args.kwargs
    assert options["whole_document"] is whole
    assert options["source_membership"] == "direct"
    assert (options["scope_record"] is None) is whole
    if not whole:
        assert options["scope_record"]["sections"] == ["Subset"]
    assert options["registry"].overlay("ingest.pdf_integrated", "default").membership == "direct"


@pytest.mark.parametrize("whole", [False, True])
def test_full_policy_scope_requires_explicit_intent(monkeypatch, tmp_path, whole):
    from corpus_structure.core.vocab import Stage
    from corpus_structure.orchestrate import semantic
    from corpus_structure.orchestrate.runner import Graph, Step
    from corpus_structure.semantic import releases

    pack = tmp_path / "statistics"
    pack.mkdir()
    for name in ("methods.yaml", "guideline.md", "policies.yaml"):
        (pack / name).write_bytes((ROOT / "domains/statistics" / name).read_bytes())
    conn = MagicMock()
    conn.execute.return_value.mappings.return_value.one.return_value = dict(release_id="release", data_revision=1)
    conn.execute.return_value.mappings.return_value.__iter__.side_effect = lambda: iter([
        dict(id=1, key="book", content_hash="a" * 64, mime="application/pdf", meta={})
    ])
    engine = MagicMock()
    engine.connect.return_value.__enter__.return_value = conn
    monkeypatch.setattr(releases, "load_release", lambda *a: SimpleNamespace(release_id="release"))
    started = MagicMock(return_value="captured")
    monkeypatch.setattr(semantic, "run_source_methods", started)
    kwargs = dict(
        release_id="release", realization_id="source", project_id="project",
        domain="statistics", domains=tmp_path, method_settings=None, whole_document=whole,
        graph=Graph(((Stage.INGEST, (Step("ingest.pdf_integrated/default"),)),), policy_propose=True),
    )
    if whole:
        assert commands.start_bound_run(engine, **kwargs) == "captured"
        assert started.call_args.kwargs["whole_document"] is True
    else:
        with pytest.raises(commands.CommandError, match="requires a scope"):
            commands.start_bound_run(engine, **kwargs)
        started.assert_not_called()
