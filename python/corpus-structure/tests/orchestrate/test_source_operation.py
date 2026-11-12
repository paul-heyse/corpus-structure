"""Real application composition across Python/CLI; native boundaries are controlled."""

import json
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock

import pytest
import yaml
from typer.testing import CliRunner

from corpus_structure.cli.app import app
from corpus_structure.cli.output import CliState
from corpus_structure.core.method import MethodSettings
from corpus_structure.core.vocab import Stage
from corpus_structure.orchestrate import phase0
from corpus_structure.orchestrate.characterization import EnrichedDocumentResult
from corpus_structure.orchestrate.semantic import BoundRunReport, SourceRunCreated
from corpus_structure.orchestrate.source_operation import run_source_operation
from corpus_structure.orchestrate.source_request import (
    Capture,
    CharacterizationOptions,
    ConfiguredGraph,
    M1Candidate,
    Phase0Analysis,
    RetainedViews,
    SourceRequestError,
    SourceRunRequest,
    source_selection,
)
from corpus_structure.semantic._operation_ids import RunId
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.structural_products import ExternalSourceRef
from corpus_structure.settings import Settings

ROOT = Path(__file__).resolve().parents[4]


@pytest.fixture
def source_case(monkeypatch, tmp_path):
    from corpus_structure.cli import orchestrate as cli_owner
    from corpus_structure.orchestrate import characterization, m1, semantic
    from corpus_structure.semantic import characterization_store, query, releases, runtime

    conn, engine = MagicMock(), MagicMock()
    engine.connect.return_value.__enter__.return_value = conn
    engine.begin.return_value.__enter__.return_value = conn
    conn.execute.return_value.mappings.return_value.one.return_value = dict(
        release_id="release", data_revision=1
    )
    docs = [dict(id=1, key="book", content_hash="a" * 64, mime="application/pdf", meta={})]
    conn.execute.return_value.mappings.return_value.__iter__.side_effect = lambda: iter(docs)
    conn.scalar.return_value = "project"
    prepared = SimpleNamespace(release_id="release")
    verification = []
    monkeypatch.setattr(
        releases, "load_release", lambda *args: verification.append(args) or prepared
    )
    declaration = yaml.safe_load((ROOT / "domains/statistics/semantic.yaml").read_text())
    monkeypatch.setattr(
        releases,
        "open_release",
        lambda *a: SimpleNamespace(
            manifest=json.dumps({"sources": [[declaration["name"], "archived"]]})
        ),
    )
    monkeypatch.setattr(runtime, "resolve_source_binding", lambda *a, **kw: ("release", "input"))
    monkeypatch.setattr(query, "read_snapshot", lambda engine: engine.connect())
    base = ProductReference(9, "integrated", "a" * 64)
    layer = ProductReference(10, "layer", "b" * 64)
    view = ProductReference(11, "view", "c" * 64)
    source = ExternalSourceRef(
        project_id="project",
        run_id=100,
        cut_id=1,
        release_id="release",
        result_revision=1,
        source_view_id=41,
        native_task_id=9,
        native_product_key="integrated",
        native_content_digest="a" * 64,
        projection_digest="b" * 64,
        recipe_digest="c" * 64,
        coordinate_version=3,
    )
    monkeypatch.setattr(
        characterization_store,
        "read_view",
        lambda *a: SimpleNamespace(
            base_document=base, payload={"profile": "selected_layers", "layers": [layer.values()]}
        ),
    )
    monkeypatch.setattr(characterization_store, "read_layer_manifest", lambda *a: object())
    monkeypatch.setattr(characterization, "characterization_sources", lambda *a, **kw: (source,))
    monkeypatch.setattr(
        m1,
        "retained_document",
        lambda *a, **kw: m1.RetainedDocument(1, "book", "a" * 64, "fixture.pdf"),
    )
    calls, enrichments, executions = [], [], []

    def run_source(engine, **kwargs):
        calls.append(kwargs)
        execution = kwargs["execution_preparation"]
        executions.append(execution)
        identity = 100 + len(calls)
        kwargs["on_created"](SourceRunCreated(RunId(identity), "project", "release"))
        return BoundRunReport(
            run_id=identity,
            status="source_ready",
            release_id="release",
            realization_id="input",
            characterization_views=tuple(kwargs.get("characterization_views", ())),
        )

    def enrich(execution, engine, capture, **kwargs):
        executions.append(execution)
        enrichments.append((capture, kwargs))
        kwargs["on_created"](SourceRunCreated(RunId(201), "project", "release"))
        kwargs["on_created"](SourceRunCreated(RunId(202), "project", "release"))
        return (EnrichedDocumentResult(view, (layer,), (201, 202), "ready", (), anchor_run_id=201),)

    monkeypatch.setattr(semantic, "run_source_methods", run_source)
    monkeypatch.setattr(characterization, "_characterize_captured_run", enrich)

    @contextmanager
    def opened(settings):
        yield engine

    monkeypatch.setattr(cli_owner, "ENGINE", opened)
    settings = Settings(
        ci_results=tmp_path / "managed", paths={"data_dir": tmp_path, "model_cache": tmp_path}
    )
    methods = MethodSettings(data_dir=tmp_path, model_cache=tmp_path)
    return SimpleNamespace(
        engine=engine,
        conn=conn,
        prepared=prepared,
        verification=verification,
        calls=calls,
        enrichments=enrichments,
        executions=executions,
        base=base,
        layer=layer,
        view=view,
        source=source,
        settings=settings,
        methods=methods,
        request=SourceRunRequest("project", "release", "input"),
    )


def test_default_cli_and_python_share_actual_capture_primary_exact_view_composition(source_case):
    case = source_case
    created = []
    direct = run_source_operation(
        case.engine, case.request, case.methods, on_created=created.append
    )
    assert direct.created_run_ids == tuple(item.run_id for item in created) == (101, 201, 202, 102)
    assert direct.capture is not None and direct.analytical is not None
    assert direct.capture.run_id == 101 and direct.analytical.run_id == 102
    assert direct.characterization[0].anchor_run_id == 201
    assert direct.characterization_views == (case.view,)
    assert len(case.verification) == 1 and len({id(value) for value in case.executions}) == 1
    before = case.calls.copy()
    case.calls.clear()
    case.enrichments.clear()
    result = CliRunner().invoke(
        app,
        ["run", "--project", "project", "--json"],
        obj=CliState(settings_factory=lambda: case.settings),
    )
    assert result.exit_code == 0, (result.output, result.exception)
    report = json.loads(result.stdout)
    assert report["capture"]["run_id"] == 101 and report["analytical"]["run_id"] == 102
    assert report["characterization_views"] == [case.view.values()]
    assert report["created_run_ids"] == [101, 201, 202, 102]
    assert len(case.calls) == 2 and len(case.enrichments) == 1
    for prior, actual in zip(before, case.calls, strict=True):
        assert prior["graph"] == actual["graph"]
        assert prior.get("selected_sources", ()) == actual.get("selected_sources", ())
        assert prior.get("characterization_views", ()) == actual.get("characterization_views", ())
    assert case.calls[-1]["registry"].overlay(
        "extract.math", "default"
    ).characterization_layers == (case.layer.values(),)
    assert case.calls[0]["graph"].stages[0][0] == Stage.INGEST
    assert all(stage != Stage.INGEST for stage, _ in case.calls[-1]["graph"].stages)


@pytest.mark.parametrize(
    "configuration", ["default", "described", "readings", "contextual", "source-only"]
)
def test_real_cli_preserves_each_m1_configuration(source_case, configuration):
    case = source_case
    result = CliRunner().invoke(
        app,
        [
            "run",
            "--project",
            "project",
            "--extraction-policy",
            "m1-candidate",
            "--m1-configuration",
            configuration,
            "--integrated-product-task",
            "9",
            "--integrated-product-key",
            "integrated",
            "--integrated-product-digest",
            "a" * 64,
            "--json",
        ],
        obj=CliState(settings_factory=lambda: case.settings),
    )
    assert result.exit_code == 0, (result.output, result.exception)
    assert len(case.verification) == 1
    final = case.calls[-1]
    assert final["extraction_policy"] == "m1-candidate"
    if configuration == "source-only":
        assert not case.enrichments and len(case.calls) == 1
        assert [stage for stage, _ in final["graph"].stages] == [Stage.INGEST]
    else:
        assert len(case.enrichments) == 1 and len(case.calls) == 2
        assert final["characterization_views"] == (case.view,)
        assert final["configurations"] == (
            {"extract.m1_candidates": configuration} if configuration != "default" else None
        )


@pytest.mark.parametrize("retained", [False, True])
def test_explicit_configured_graph_keeps_declared_intent_and_original_authority(
    source_case, retained
):
    case = source_case
    workflow = ConfiguredGraph(RetainedViews((case.view,))) if retained else ConfiguredGraph()
    request = replace(case.request, workflow=workflow, fresh=("extract.math",) if retained else ())
    result = run_source_operation(
        case.engine, request, case.methods, graph=phase0.PHASE0, registry_for=phase0.registry
    )
    assert not case.enrichments and len(case.calls) == 1
    assert result.capture is None and result.analytical is not None
    if retained:
        assert case.calls[0]["selected_sources"] == (case.source,)
        assert result.characterization_views == (case.view,)
    else:
        assert case.calls[0]["graph"] is phase0.PHASE0
        assert case.calls[0]["characterization_views"] == ()


def test_retained_analysis_performs_no_capture_or_nlp(source_case):
    case = source_case
    result = run_source_operation(
        case.engine,
        replace(case.request, workflow=Phase0Analysis(RetainedViews((case.view,)))),
        case.methods,
    )
    assert not case.enrichments and len(case.calls) == 1
    assert result.capture is None and result.characterization_views == (case.view,)
    assert case.calls[0]["selected_sources"] == (case.source,)


@pytest.mark.parametrize(
    "workflow", [Capture(), Capture(CharacterizationOptions.from_options({})), Phase0Analysis()]
)
def test_registration_execution_shares_one_full_verification_and_live_admission(
    source_case, monkeypatch, tmp_path, workflow
):
    from corpus_structure.semantic import _operation_calls, contracts, operations

    case = source_case
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "fixture.pdf").write_bytes(b"%PDF-fixture")
    admissions, initialized, registered = [], [], []
    monkeypatch.setattr(
        contracts,
        "require_bound_operation",
        lambda prepared, name: admissions.append((prepared, name)),
    )
    monkeypatch.setattr(
        _operation_calls, "initialize_source_project", lambda *a, **kw: initialized.append(kw)
    )
    monkeypatch.setattr(operations, "register_document", lambda *a, **kw: registered.append(kw))
    request = replace(case.request, registration_corpus=corpus, workflow=workflow)
    result = run_source_operation(
        case.engine,
        request,
        case.methods,
        registry_for=lambda pack: phase0.bind_pdf_selection(
            phase0.registry(pack), document=SimpleNamespace(source_uri="fixture.pdf")
        ),
    )
    assert len(case.verification) == 1
    assert admissions == [(case.prepared, "construct_project")]
    assert len(initialized) == len(registered) == 1
    assert initialized[0]["projection_context"] is registered[0]["prepared"] is case.prepared
    assert len({id(value) for value in case.executions}) == 1
    assert result.capture is not None
    assert (result.analytical is not None) is isinstance(workflow, Phase0Analysis)
    assert len(case.enrichments) == int(
        isinstance(workflow, Phase0Analysis) or workflow.enrichment is not None
    )
    with pytest.raises(ValueError, match="closed"):
        case.executions[0].require_release("release")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"selection": "whole-document"},
        {"workflow": "phase0"},
        {"domain": "../statistics"},
        {
            "native_product": ProductReference(1, "native", "a" * 64),
            "integrated_product": ProductReference(2, "integrated", "b" * 64),
        },
        {"workflow": M1Candidate()},
    ],
)
def test_complete_request_refuses_invalid_variants_before_engine(kwargs):
    with pytest.raises(SourceRequestError):
        SourceRunRequest("project", **kwargs)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"slice": "a", "scope": "b"},
        {"slice": "a", "whole_document": True},
        {"corpus": "retired"},
    ],
)
def test_source_selector_preflight_is_shared_and_pure(kwargs):
    with pytest.raises(SourceRequestError):
        source_selection(**kwargs)


def test_explicit_domain_constrains_archive_before_preparation(source_case):
    case = source_case
    with pytest.raises(SourceRequestError, match="no matching executable pack"):
        run_source_operation(case.engine, replace(case.request, domain="toy"), case.methods)
    assert not case.verification and not case.calls


def test_shared_settings_factory_merges_policy_and_preserves_complete_settings(
    source_case, tmp_path
):
    from corpus_structure.cli.characterization_options import method_settings as from_file
    from corpus_structure.orchestrate.source_request import method_settings as from_settings

    settings = source_case.settings
    overrides = {"max_regions": 1, "workers": 1}
    policy = tmp_path / "policy.json"
    policy.write_text(json.dumps(overrides))
    shared = from_settings(settings, overrides)
    assert from_file(settings, policy) == shared
    assert shared.execution_policy.max_regions == shared.execution_policy.workers == 1
    assert shared.execution_policy.max_claims == settings.characterization_execution.max_claims
    assert shared.nemotron_endpoint == settings.nemotron.endpoint
    assert (
        shared.data_dir == settings.paths.data_dir
        and shared.model_cache == settings.paths.model_cache
    )


@pytest.mark.parametrize("primary", ["retained", object()])
def test_unknown_nested_input_cannot_silently_change_workflow(primary):
    with pytest.raises(SourceRequestError):
        Phase0Analysis(primary)
    with pytest.raises(SourceRequestError):
        ConfiguredGraph(primary)


@pytest.mark.parametrize("domain", ["..", ".", "", " ", 2])
def test_invalid_domain_is_purely_refused(domain):
    with pytest.raises(SourceRequestError):
        SourceRunRequest("project", domain=domain)


@pytest.mark.parametrize("content", ["null", "[]"])
def test_policy_file_requires_object_framing_without_reinterpreting_policy(
    source_case, tmp_path, content
):
    import typer

    from corpus_structure.cli.characterization_options import method_settings as from_file

    path = tmp_path / "policy.json"
    path.write_text(content)
    with pytest.raises(typer.BadParameter, match="execution policy must be an object"):
        from_file(source_case.settings, path)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"release_id": ""},
        {"realization_id": " "},
        {"release_id": 8},
        {"native_product": {}},
        {"integrated_product": "untyped"},
        {"agent_mode": "wait"},
        {"agent_reuse": "partial"},
        {"phase": True},
        {"phase": "0"},
        {"fresh": "extract.math"},
        {"fresh": (None,)},
        {"fresh": ("",)},
    ],
)
def test_complete_target_and_policy_refusals_precede_engine(kwargs):
    with pytest.raises(SourceRequestError):
        run_source_operation(
            cast(Any, object()), SourceRunRequest("project", **kwargs), cast(Any, None)
        )


@pytest.mark.parametrize(
    "selection",
    [
        source_selection(),
        source_selection(slice="selected"),
        source_selection(scope="selected"),
        source_selection(whole_document=True),
    ],
)
@pytest.mark.parametrize(
    "workflow",
    [
        Phase0Analysis(),
        Phase0Analysis(RetainedViews((ProductReference(11, "view", "a" * 64),))),
        Capture(),
        Capture(CharacterizationOptions.from_options({"text.constructions": {}})),
        M1Candidate("source-only"),
        ConfiguredGraph(),
        ConfiguredGraph(RetainedViews((ProductReference(11, "view", "a" * 64),))),
    ],
)
def test_typed_source_intent_roundtrips_selection_workflow_and_exact_pins(selection, workflow):
    from pydantic import TypeAdapter

    request = SourceRunRequest(
        "project",
        selection=selection,
        workflow=workflow,
        integrated_product=ProductReference(9, "integrated", "b" * 64),
    )
    adapter = TypeAdapter(SourceRunRequest)
    decoded = adapter.validate_json(adapter.dump_json(request))
    assert decoded == request
    assert type(decoded.selection) is type(selection)
    assert type(decoded.workflow) is type(workflow)
    assert decoded.integrated_product == request.integrated_product


@pytest.mark.parametrize("field", ["selection", "workflow"])
def test_typed_source_intent_rejects_unknown_serialized_variant(field):
    from pydantic import TypeAdapter, ValidationError

    adapter = TypeAdapter(SourceRunRequest)
    value = json.loads(adapter.dump_json(SourceRunRequest("project")))
    value[field]["kind"] = "invented"
    with pytest.raises((ValidationError, SourceRequestError)):
        adapter.validate_json(json.dumps(value))


def test_source_intent_does_not_accept_serialized_implementation_dependencies():
    from pydantic import TypeAdapter, ValidationError

    adapter = TypeAdapter(SourceRunRequest)
    value = json.loads(adapter.dump_json(SourceRunRequest("project")))
    value["graph"] = {"stages": []}
    with pytest.raises(ValidationError) as refusal:
        adapter.validate_json(json.dumps(value))
    assert refusal.value.errors()[0]["loc"] == ("graph",)
    assert refusal.value.errors()[0]["type"] == "unexpected_keyword_argument"


def test_source_intent_refuses_a_direct_variant_with_a_mismatched_tag():
    from corpus_structure.orchestrate.source_request import WholeDocument

    with pytest.raises(SourceRequestError, match="variant tag"):
        SourceRunRequest("project", selection=WholeDocument(kind=cast(Any, "scope")))


@pytest.mark.parametrize("path", [("selection",), ("workflow",), ("workflow", "primary")])
def test_nested_intent_refuses_serialized_implementation_fields(path):
    from pydantic import TypeAdapter, ValidationError

    adapter = TypeAdapter(SourceRunRequest)
    value = json.loads(adapter.dump_json(SourceRunRequest("project")))
    target = value
    for key in path:
        target = target[key]
    target["graph"] = {"stages": []}
    with pytest.raises(ValidationError):
        adapter.validate_json(json.dumps(value))
