"""Native demand identity and operational recovery stay independent of CLI receipt expiry."""

from dataclasses import replace
from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from sqlalchemy import JSON, Column, Integer, MetaData, String, Table

from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
from corpus_structure.orchestrate.characterization import CharacterizationDemandRequest
from corpus_structure.orchestrate.characterization_recovery import (
    CharacterizationDemand,
    CharacterizationOperation,
    _validate_current_profiles,
    native_thread_profile,
    resolve_characterization_anchor,
)
from corpus_structure.semantic.operations import OperationBinding, OperationConflict
from corpus_structure.semantic.product_reference import ProductReference


def demand():
    return CharacterizationDemandRequest(
        project_id="project",
        release_id="release",
        realization_id="source",
        base_document=ProductReference(7, "native", "a" * 64),
        source_scope={
            "source_view_ids": [12],
            "selectors": [{"projection": "b" * 64, "start": 0, "end": 20}],
        },
        selected_sources=(),
        fresh_methods=("text.native_evidence",),
        method_options={"text.native_evidence": {"hanlp_device": "cpu"}},
    )


def registry():
    return SimpleNamespace(
        methods=lambda: (SimpleNamespace(name="text.native_evidence", version="1"),)
    )


def test_anchor_is_first_actual_stage_and_children_reference_it():
    from uuid import UUID

    from corpus_structure.orchestrate.source_lineage import SourceOperationLink

    link = SourceOperationLink(
        operation_id=UUID("00000000-0000-0000-0000-000000000123"), role="primary", capture_run_id=77
    )
    operation = CharacterizationOperation.freeze(
        (demand(), demand()),
        registry(),
        {},
        policy=CharacterizationExecutionPolicy(),
        source_operation=link,
    )
    first = operation.options(0, ("text.native_evidence", "text.formal_evidence"))
    assert operation.anchor_run_id is None
    assert "characterization_anchor" not in first
    frozen = CharacterizationDemand.model_validate(first["characterization_demand"])
    assert frozen.requests[0].base_document == ProductReference(7, "native", "a" * 64)
    assert frozen.requests[0].source_scope["selectors"][0]["end"] == 20
    callbacks = []
    operation.created(
        SimpleNamespace(run_id=91, project="project", release_id="release"), callbacks.append
    )
    child = operation.options(1, ("text.constructions",))
    assert child == {
        "characterization_anchor": 91,
        "characterization_region": 1,
        "characterization_stage": ["text.constructions"],
        "source_operation": {
            "version": 1,
            "operation_id": "00000000-0000-0000-0000-000000000123",
            "role": "primary",
            "capture_run_id": 77,
        },
    }
    assert first["source_operation"] == child["source_operation"]
    assert "source_operation" not in first["characterization_demand"]
    operation.created(SimpleNamespace(run_id=92, project="project", release_id="release"))
    assert operation.anchor_run_id == 91
    assert len(callbacks) == 1


def test_fresh_seed_survives_native_roundtrip_and_is_distinct_per_new_demand():
    operation = CharacterizationOperation.freeze((demand(),), registry(), {})
    restored = CharacterizationDemand.model_validate_json(operation.envelope.model_dump_json())
    assert restored.freshness_seed == operation.envelope.freshness_seed
    assert restored.requests[0].fresh_methods == ("text.native_evidence",)
    assert (
        restored.freshness_seed
        != CharacterizationOperation.freeze((demand(),), registry(), {}).envelope.freshness_seed
    )
    with pytest.raises(ValidationError):
        CharacterizationDemand.model_validate({**restored.model_dump(), "version": 2})


def test_capacity_policy_change_preserves_native_profile_but_thread_change_does_not():
    policy = CharacterizationExecutionPolicy()
    capacity = replace(policy, workers=1, max_regions=1, max_claims=1)
    operation = CharacterizationOperation.freeze((demand(),), registry(), {}, policy=policy)
    _validate_current_profiles(
        None, operation.envelope, registry(), None, SimpleNamespace(execution_policy=capacity)
    )
    assert native_thread_profile(capacity) == native_thread_profile(policy)
    with pytest.raises(OperationConflict, match="thread profile changed"):
        _validate_current_profiles(
            None,
            operation.envelope,
            registry(),
            None,
            SimpleNamespace(execution_policy=replace(policy, provider_threads=2)),
        )
    with pytest.raises(OperationConflict, match="method versions changed"):
        _validate_current_profiles(
            None,
            operation.envelope,
            SimpleNamespace(methods=lambda: ()),
            None,
            SimpleNamespace(execution_policy=policy),
        )


def test_terminal_child_resolves_native_anchor_and_rejects_cross_binding(monkeypatch):
    from corpus_structure.semantic import metadata

    runs = Table(
        "run",
        MetaData(),
        Column("id", Integer),
        Column("options", JSON),
        Column("project_id", String),
        Column("release_id", String),
        Column("input_realization_id", String),
    )
    monkeypatch.setattr(metadata, "table", lambda name: runs)
    operation = CharacterizationOperation.freeze((demand(),), registry(), {})
    anchor = dict(
        id=91,
        project_id="project",
        release_id="release",
        input_realization_id="source",
        options=operation.options(0, ("text.native_evidence",)),
    )
    child = dict(
        id=92,
        project_id="project",
        release_id="release",
        input_realization_id="source",
        status="cancelled",
        options={"characterization_anchor": 91},
    )

    class Connection:
        def __init__(self, rows):
            self.rows = iter(rows)

        def execute(self, query):
            return SimpleNamespace(mappings=lambda: SimpleNamespace(one=lambda: next(self.rows)))

    found, envelope = resolve_characterization_anchor(Connection([child, anchor]), 92)
    assert found == 91
    assert envelope.freshness_seed == operation.envelope.freshness_seed
    with pytest.raises(OperationConflict, match="retained run binding"):
        resolve_characterization_anchor(Connection([{**child, "project_id": "other"}, anchor]), 92)


def test_old_run_without_anchor_requires_ordinary_resume(monkeypatch):
    from corpus_structure.semantic import metadata

    runs = Table("run", MetaData(), Column("id", Integer), Column("options", JSON))
    monkeypatch.setattr(metadata, "table", lambda name: runs)
    row = dict(id=12, options={}, status="finished")
    connection = SimpleNamespace(
        execute=lambda query: SimpleNamespace(mappings=lambda: SimpleNamespace(one=lambda: row))
    )
    with pytest.raises(OperationConflict, match="ordinary resume"):
        resolve_characterization_anchor(connection, 12)


def test_interleaved_first_region_stages_persist_exactly_one_anchor(monkeypatch):
    from contextlib import nullcontext

    from pydantic import BaseModel

    from corpus_structure.orchestrate import characterization, semantic
    from corpus_structure.orchestrate.registry import MethodRegistry, MethodsFile
    from corpus_structure.semantic import query

    class ComposeConfig(BaseModel):
        characterization_base_document: dict | None = None
        characterization_source_scope: dict | None = None
        characterization_layers: tuple[dict, ...] = ()
        characterization_active_layers: tuple[dict, ...] = ()
        characterization_profile: str = "source_only"

    composer = SimpleNamespace(name="text.compose_view", version="1", Config=ComposeConfig)
    selected = MethodRegistry((composer,), MethodsFile())
    request = demand().model_copy(
        update={
            "source_scope": {"source_view_ids": []},
            "source_only": True,
            "fresh_methods": (),
            "method_options": {},
        }
    )
    policy = CharacterizationExecutionPolicy()
    operation = CharacterizationOperation.freeze((request, request), selected, {}, policy=policy)
    execution = SimpleNamespace(cpu=SimpleNamespace(policy=policy))
    snapshots = []

    def source_plan(*args, **kwargs):
        options = kwargs["source_run_options"]
        assert callable(options), "persisted options must resolve after stage admission"
        yield ()  # Both region plans have entered, neither has acquired its actual run yet.
        snapshots.append(options())
        run_id = 90 + len(snapshots)
        kwargs["on_created"](
            SimpleNamespace(run_id=run_id, project="project", release_id="release")
        )
        return SimpleNamespace(run_id=run_id)

    monkeypatch.setattr(semantic, "_source_methods_plan", source_plan)
    monkeypatch.setattr(query, "read_snapshot", lambda engine: nullcontext(None))
    monkeypatch.setattr(characterization, "characterization_profiles", lambda prepared: {})
    monkeypatch.setattr(
        characterization,
        "_inventory",
        lambda engine, run: [
            {"kind": "view", "reference": ProductReference(run, "view", "c" * 64).values()}
        ],
    )
    plans = [
        characterization._enrich_document_plan(
            None,
            demand=characterization.EnrichedDocumentDemand(
                request.base_document, request.source_scope, source_only=True
            ),
            project_id="project",
            prepared=object(),
            binding=OperationBinding("release", "source", 0, b"{}"),
            registry=selected,
            method_settings=SimpleNamespace(execution_policy=policy),
            selected_sources=(),
            execution_preparation=execution,
            characterization_operation=operation,
            region_index=index,
        )
        for index in range(2)
    ]
    assert next(plans[0]) == ()
    assert next(plans[1]) == ()
    for plan in plans:
        with pytest.raises(StopIteration):
            next(plan)
    assert sum("characterization_demand" in options for options in snapshots) == 1
    assert snapshots[1]["characterization_anchor"] == 91
    assert snapshots[1]["characterization_region"] == 1


def test_public_fallbacks_preserve_selected_execution_policy(monkeypatch):
    from contextlib import contextmanager

    from corpus_structure.core import work
    from corpus_structure.orchestrate import characterization, ready, semantic
    from corpus_structure.semantic.cpu_execution import OwnedByteBudget

    policy = replace(CharacterizationExecutionPolicy(), max_regions=1)
    observed = []
    execution = SimpleNamespace(cpu=SimpleNamespace(budget=OwnedByteBudget(policy.max_owned_bytes)))

    @contextmanager
    def owned(prepared, *, policy=None):
        observed.append(policy)
        yield execution

    monkeypatch.setattr(ready, "owned_source_execution", owned)
    monkeypatch.setattr(work, "drive_prepared_work", lambda plan, active: "enriched")
    assert (
        characterization.enrich_document(
            None,
            prepared=object(),
            method_settings=SimpleNamespace(execution_policy=policy),
            demand=object(),
            project_id="project",
            binding=OperationBinding("release", "source", 0, b"{}"),
            registry=object(),
            selected_sources=(),
        )
        == "enriched"
    )
    monkeypatch.setattr(semantic, "_run_source_methods", lambda cpu, **kwargs: "source")
    assert (
        semantic.run_source_methods(
            None,
            project_id="project",
            prepared=object(),
            binding=OperationBinding("release", "source", 0, b"{}"),
            registry=object(),
            graph=object(),
            method_settings=SimpleNamespace(execution_policy=policy),
        )
        == "source"
    )
    assert observed == [policy, policy]


def test_optional_managed_receipt_failure_cannot_replace_native_recovery():
    from corpus_structure.orchestrate.characterization_recovery import (
        record_frozen_characterization,
    )

    operation = CharacterizationOperation.freeze((demand(),), registry(), {})

    class UnavailableReceipt:
        @property
        def directory(self):
            raise OSError("receipt unavailable")

        def observe(self, *args, **kwargs):
            raise OSError("observation unavailable too")

    record_frozen_characterization(
        UnavailableReceipt(), 91, operation.envelope, CharacterizationExecutionPolicy()
    )


@pytest.mark.parametrize(
    "threads,interop,error", [(2, 1, "frozen GLiNER"), (4, 2, "frozen GLiNER")]
)
def test_gliner_thread_policy_refuses_mismatched_frozen_profile_before_preflight(
    monkeypatch, tmp_path, threads, interop, error
):
    from contextlib import nullcontext

    from corpus_structure.methods.gliner import GlinerProfile
    from corpus_structure.methods.model_characterization import ModelCharacterizationConfig
    from corpus_structure.orchestrate import characterization
    from corpus_structure.semantic import model_characterization, query

    profile = GlinerProfile(
        snapshot=tmp_path,
        checkpoint="fastino/gliner2.5-base-v1",
        revision="54785d51df8d86a0d8f2eb212fec15871aad2c4d",
        artifact_hashes=tuple(
            (name, "a" * 64)
            for name in (
                "config.json",
                "encoder_config/config.json",
                "model.safetensors",
                "tokenizer.json",
                "tokenizer_config.json",
            )
        ),
    )
    request = demand().model_copy(
        update={
            "source_scope": {"source_view_ids": []},
            "fresh_methods": (),
            "method_options": {
                "text.model_characterization": {
                    "gliner_profile": {
                        "provider": "gliner",
                        "device": "cuda",
                        "profile": profile,
                    }
                }
            },
        }
    )
    monkeypatch.setattr(query, "read_snapshot", lambda engine: nullcontext(None))
    monkeypatch.setattr(model_characterization, "question_manifest", lambda prepared: {})
    monkeypatch.setattr(
        characterization, "PRIMARY_PRODUCERS", frozenset({"text.model_characterization"})
    )
    selected = SimpleNamespace(
        file=SimpleNamespace(configs={}, sections={}),
        method=lambda name: SimpleNamespace(Config=ModelCharacterizationConfig),
    )
    with pytest.raises(ValueError, match=error):
        characterization._freeze_request(
            None,
            request,
            selected,
            None,
            SimpleNamespace(
                execution_policy=replace(
                    CharacterizationExecutionPolicy(),
                    provider_threads=threads,
                    provider_interop_threads=interop,
                ),
            ),
            {},
        )


def test_recovery_compares_provider_identity_without_transient_selection_memo(monkeypatch):
    from corpus_structure.orchestrate import characterization

    policy = CharacterizationExecutionPolicy()
    snapshot = {"runtime_identity": {"python": "3.14.10"}, "assets": {}}
    profile = {"provider": "spacy", "identity": "frozen"}
    request = demand().model_copy(
        update={"method_options": {"text.native_evidence": {"spacy_native_profile": profile}}}
    )
    cache = {"hanlp": snapshot, "_profile_selections": {("spacy", "configuration"): object()}}
    operation = CharacterizationOperation.freeze((request,), registry(), cache, policy=policy)
    assert operation.envelope.provider_profiles == {"hanlp": snapshot}

    def authenticate(engine, candidate, selected, prepared, settings, cache, **kwargs):
        assert "spacy_native_profile" not in candidate.method_options["text.native_evidence"]
        cache.update({"hanlp": snapshot, "_profile_selections": {("spacy",): object()}})
        return request, ()

    monkeypatch.setattr(characterization, "_freeze_request", authenticate)
    settings = SimpleNamespace(execution_policy=policy)
    _validate_current_profiles(None, operation.envelope, registry(), None, settings)

    changed = request.model_copy(
        update={
            "method_options": {
                "text.native_evidence": {
                    "spacy_native_profile": {"provider": "spacy", "identity": "changed"}
                }
            }
        }
    )
    monkeypatch.setattr(characterization, "_freeze_request", lambda *args, **kwargs: (changed, ()))
    with pytest.raises(OperationConflict, match="provider profile changed"):
        _validate_current_profiles(None, operation.envelope, registry(), None, settings)


def test_resume_declares_all_regions_before_any_native_stage(monkeypatch):
    from contextlib import nullcontext

    from corpus_structure.methods import characterization_resources
    from corpus_structure.orchestrate import characterization, characterization_recovery
    from corpus_structure.semantic import execution_preparation, metadata, query

    policy = CharacterizationExecutionPolicy()
    first = demand().model_copy(update={"method_options": {"text.native_evidence": {}}})
    second = demand().model_copy(update={"method_options": {"text.model_characterization": {}}})
    operation = CharacterizationOperation.freeze((first, second), registry(), {}, policy=policy)
    retained = [{"id": 91, "status": "finished", "options": operation.options(0, ())}]
    connection = SimpleNamespace(
        execute=lambda statement: SimpleNamespace(
            mappings=lambda: SimpleNamespace(all=lambda: retained)
        )
    )
    runs = Table("run", MetaData(), Column("id", Integer), Column("options", JSON))
    monkeypatch.setattr(metadata, "table", lambda name: runs)
    monkeypatch.setattr(query, "read_snapshot", lambda engine: nullcontext(connection))
    monkeypatch.setattr(
        characterization_recovery,
        "resolve_characterization_anchor",
        lambda conn, run: (91, operation.envelope),
    )
    monkeypatch.setattr(
        characterization_recovery, "_validate_current_profiles", lambda *args, **kwargs: None
    )
    declared = set()

    class Execution:
        prepared = object()
        cpu = SimpleNamespace(policy=policy)
        providers = SimpleNamespace(
            declare_native=lambda population, **kwargs: declared.update(population)
        )

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(
        execution_preparation, "prepare_execution", lambda *args, **kwargs: Execution()
    )
    monkeypatch.setattr(
        characterization_resources,
        "selections_for_characterization",
        lambda options, settings: tuple(options),
    )
    monkeypatch.setattr(characterization, "_inventory", lambda *args: ())

    def stage(*args, **kwargs):
        assert declared == {"text.native_evidence", "text.model_characterization"}
        yield ()
        return "completed"

    monkeypatch.setattr(characterization, "_demand_plan", stage)
    monkeypatch.setattr(
        characterization,
        "_combine_characterization_results",
        lambda execution, engine, regional, *args, **kwargs: regional,
    )
    selected = SimpleNamespace(bind_release=lambda prepared: registry())
    settings = SimpleNamespace(execution_policy=policy, nemotron_endpoint=None)
    result = characterization_recovery.resume_characterization(
        None, 91, settings, registry=selected
    )
    assert [value for request, value in result] == ["completed", "completed"]
