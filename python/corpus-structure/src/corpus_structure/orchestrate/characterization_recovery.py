"""Frozen native demand anchors and explicit recovery of ordinary characterization runs.

The anchor lives in the first real stage run. Managed artifacts are convenient copies;
expiry of a CLI result does not remove the authoritative request or its freshness seed.
"""

from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from .characterization import CharacterizationDemandRequest


def native_thread_profile(policy):
    if policy is None:
        return {}
    return {
        key: getattr(policy, key)
        for key in ("provider_threads", "provider_interop_threads", "cpu_native_threads")
    }


class CharacterizationDemand(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    version: Literal[1] = 1
    requests: tuple[CharacterizationDemandRequest, ...] = Field(min_length=1)
    freshness_seed: str = Field(min_length=1)
    method_versions: dict[str, str]
    provider_profiles: dict[str, dict[str, Any] | None] = Field(default_factory=dict)
    preparation_diagnostics: tuple[str, ...] = ()
    execution_native_profile: dict[str, int] = Field(default_factory=dict)


@dataclass
class CharacterizationOperation:
    envelope: CharacterizationDemand
    anchor_run_id: int | None = None
    recovering: bool = False
    recovered_layers: set = field(default_factory=set)
    recovered_views: dict = field(default_factory=dict)
    recovered_runs: dict = field(default_factory=dict)

    @classmethod
    def freeze(cls, requests, registry, profiles, diagnostics=(), policy=None):
        envelope = CharacterizationDemand(
            requests=requests,
            freshness_seed=uuid4().hex,
            method_versions={method.name: str(method.version) for method in registry.methods()},
            provider_profiles=dict(profiles),
            preparation_diagnostics=diagnostics,
            execution_native_profile=native_thread_profile(policy),
        )
        return cls(CharacterizationDemand.model_validate_json(envelope.model_dump_json()))

    def request(self, index, fallback):
        return self.envelope.requests[index] if index >= 0 else fallback

    def options(self, region, stages):
        options = {"characterization_region": region, "characterization_stage": list(stages)}
        if self.anchor_run_id is None:
            options["characterization_demand"] = self.envelope.model_dump(mode="json")
        else:
            options["characterization_anchor"] = self.anchor_run_id
        return options

    def created(self, created, callback=None):
        if self.anchor_run_id is None:
            self.anchor_run_id = int(created.run_id)
        from corpus_structure.cli.observation_logging import event

        event(
            "characterization_stage_created",
            "Characterization stage run created",
            run_id=int(created.run_id),
            anchor_run_id=self.anchor_run_id,
            project=created.project,
            release_id=created.release_id,
        )
        if callback is not None:
            callback(created)


def resolve_characterization_anchor(conn, run_id):
    """Resolve even a terminal child, without changing historical run or task state."""
    from sqlalchemy import select

    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.operations import OperationConflict

    runs = table("ops.run")
    row = conn.execute(select(runs).where(runs.c.id == run_id)).mappings().one()
    options = row["options"]
    anchor = options.get("characterization_anchor", run_id)
    if isinstance(anchor, bool) or not isinstance(anchor, int) or anchor < 1:
        raise OperationConflict("invalid characterization anchor reference")
    owner = (
        row
        if anchor == run_id
        else conn.execute(select(runs).where(runs.c.id == anchor)).mappings().one()
    )
    body = owner["options"].get("characterization_demand")
    if body is None:
        raise OperationConflict("run has no frozen characterization demand; use ordinary resume")
    envelope = CharacterizationDemand.model_validate(body)
    for request in envelope.requests:
        for bound in (row, owner):
            if (bound["project_id"], bound["release_id"], bound["input_realization_id"]) != (
                request.project_id,
                request.release_id,
                request.realization_id,
            ):
                raise OperationConflict("characterization anchor differs from retained run binding")
    return anchor, envelope


def _validate_current_profiles(engine, envelope, registry, prepared, method_settings):
    from corpus_structure.semantic.operations import OperationConflict

    from .characterization import _freeze_request

    if native_thread_profile(method_settings.execution_policy) != envelope.execution_native_profile:
        raise OperationConflict(
            "characterization recovery native thread profile changed; submit a new demand"
        )
    versions = {method.name: str(method.version) for method in registry.methods()}
    if versions != envelope.method_versions:
        raise OperationConflict("characterization recovery method versions changed")
    if not envelope.provider_profiles:
        return
    # Re-authenticate auto-selected runtimes instead of trusting an expired CLI copy.
    cache = {}
    for request in envelope.requests:
        options = {name: dict(values) for name, values in request.method_options.items()}
        for name, keys, providers in (
            ("text.native_evidence", ("hanlp_runtime", "hanlp_artifacts"), ("hanlp",)),
            (
                "text.contextual_characterization",
                ("native_runtime", "native_artifacts"),
                ("maverick", "dipo"),
            ),
            ("text.model_characterization", ("d1_runtime", "d1_artifacts"), ("d1",)),
        ):
            if any(provider in envelope.provider_profiles for provider in providers):
                for key in keys:
                    options.setdefault(name, {}).pop(key, None)
        _freeze_request(
            engine,
            request.model_copy(update={"method_options": options}),
            registry,
            prepared,
            method_settings,
            cache,
        )
    if cache != envelope.provider_profiles:
        raise OperationConflict(
            "characterization recovery provider profile changed; submit a new demand"
        )


def resume_characterization(
    engine,
    run_id,
    method_settings,
    *,
    project_id=None,
    registry=None,
    on_created=None,
    on_frozen=None,
):
    from sqlalchemy import select

    from corpus_structure.core.work import ReadyGroup, drive_prepared_work
    from corpus_structure.schema.pack import DOMAINS
    from corpus_structure.semantic.execution_preparation import prepare_execution
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.operations import OperationConflict
    from corpus_structure.semantic.product_reference import ProductReference
    from corpus_structure.semantic.query import read_snapshot

    from .characterization import _combine_characterization_results, _demand_plan, _inventory
    from .phase0 import registry as registry_for

    with read_snapshot(engine) as conn:
        anchor, envelope = resolve_characterization_anchor(conn, run_id)
        request = envelope.requests[0]
        if project_id is not None and project_id != request.project_id:
            raise OperationConflict("characterization recovery belongs to another project")
        runs = table("ops.run")
        retained = (
            conn.execute(
                select(runs)
                .where(
                    (runs.c.id == anchor)
                    | (runs.c.options["characterization_anchor"].as_integer() == anchor)
                )
                .order_by(runs.c.id)
            )
            .mappings()
            .all()
        )
        from .liveness import observe_supervisor

        if any(
            row["status"] in {"created", "running"} and observe_supervisor(conn, row["id"])[0]
            for row in retained
        ):
            # An orphaned run can be explicitly cancelled first; do not race a live owner.
            raise OperationConflict(
                "characterization stage is still open; cancel its run before recovery"
            )
        execution = prepare_execution(
            conn, request.release_id, policy=method_settings.execution_policy
        )
    with execution:
        selected = (registry or registry_for(DOMAINS / request.domain)).bind_release(
            execution.prepared
        )
        _validate_current_profiles(engine, envelope, selected, execution.prepared, method_settings)
        operation = CharacterizationOperation(envelope, anchor_run_id=anchor, recovering=True)
        for retained_run in retained:
            operation.recovered_runs.setdefault(
                retained_run["options"].get("characterization_region"), []
            ).append(int(retained_run["id"]))
        recovered = []
        for index, request in enumerate(envelope.requests):
            pins = list(request.selected_layers)
            # Active selections track the latest settled layer per operation; closure retains all
            # exact dependencies until the ordinary composer prunes superseded roots.
            active = list(
                request.selected_layers if request.active_layers is None else request.active_layers
            )
            from corpus_structure.semantic.characterization_store import read_layer

            for row in retained:
                if row["options"].get("characterization_region") != index:
                    continue
                for product in _inventory(engine, row["id"]):
                    if product["kind"] == "view":
                        operation.recovered_views.setdefault(index, []).append(
                            ProductReference(**product["reference"])
                        )
                    if product["kind"] != "layer":
                        continue
                    pin = ProductReference(**product["reference"])
                    with read_snapshot(engine) as conn:
                        layer = read_layer(conn, pin, run_id=row["id"])
                    if (
                        layer.base_document != request.base_document
                        or layer.payload["source_scope"] != request.source_scope
                    ):
                        raise OperationConflict("recovered layer differs from frozen source scope")
                    if pin not in pins:
                        pins.append(pin)
                    operation.recovered_layers.add(pin)
                    active.append(pin)
            # Keep newest exact selection for each producer, with its dependency closure.
            latest = {}
            with read_snapshot(engine) as conn:
                for pin in dict.fromkeys(active):
                    latest[read_layer(conn, pin).payload["operation"]["key"]] = pin
            recovered.append(
                request.model_copy(
                    update={"selected_layers": tuple(pins), "active_layers": tuple(latest.values())}
                )
            )
        for row in retained:
            if row["options"].get("characterization_region") == -1:
                for product in _inventory(engine, row["id"]):
                    if product["kind"] == "view":
                        operation.recovered_views.setdefault(-1, []).append(
                            ProductReference(**product["reference"])
                        )
        operation.envelope = envelope.model_copy(update={"requests": tuple(recovered)})
        if on_frozen is not None:
            on_frozen(anchor, envelope)

        def plan():
            return (
                yield ReadyGroup(
                    tuple(
                        _demand_plan(
                            execution,
                            engine,
                            request,
                            method_settings,
                            registry=selected,
                            characterization_operation=operation,
                            region_index=index,
                            on_created=on_created,
                        )
                        for index, request in enumerate(recovered)
                    ),
                    max_active=execution.cpu.policy.max_regions,
                )
            )

        results = drive_prepared_work(plan(), lambda: None)
        return _combine_characterization_results(
            execution,
            engine,
            list(zip(recovered, results, strict=True)),
            method_settings,
            registry=selected,
            on_created=on_created,
            operation=operation,
        )


def record_characterization_run(invocation, engine, created):
    """Copy a native anchor into the current managed result and correlate actual runs.

    No context binding crosses a generator yield: each observation carries its own run.
    Optional receipt failure cannot replace native execution or its original failure.
    """
    from sqlalchemy import select

    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.query import read_snapshot

    try:
        with read_snapshot(engine) as conn:
            runs = table("ops.run")
            options = conn.scalar(select(runs.c.options).where(runs.c.id == created.run_id))
            if not ({"characterization_demand", "characterization_anchor"} & options.keys()):
                return False
            anchor, envelope = resolve_characterization_anchor(conn, int(created.run_id))
        selected = invocation.manifest.details.setdefault("characterization_runs", [])
        if int(created.run_id) not in selected:
            selected.append(int(created.run_id))
        role = "characterization-demand"
        if role not in invocation.manifest.artifacts:
            path = invocation.directory / "characterization-demand.json"
            path.write_text(envelope.model_dump_json(), encoding="utf-8")
            invocation.publish(role, path)
        invocation.stage(
            "characterization_running",
            anchor_run_id=anchor,
            run_id=int(created.run_id),
            project=created.project,
            release_id=created.release_id,
            execution_policy=options.get("physical_policy"),
            region=options.get("characterization_region"),
            characterization_stage=options.get("characterization_stage"),
        )
        return True
    except Exception as error:
        with suppress(Exception):
            invocation.observe(
                "binding_unavailable",
                "Characterization receipt binding unavailable",
                run_id=int(created.run_id),
                reason=type(error).__name__,
            )
        return False


def record_frozen_characterization(invocation, anchor, envelope, policy):
    """Expose recovery identity even if every retained stage already settled."""
    from dataclasses import asdict

    try:
        role = "characterization-demand"
        path = invocation.directory / "characterization-demand.json"
        path.write_text(envelope.model_dump_json(), encoding="utf-8")
        invocation.publish(role, path)
        invocation.stage(
            "characterization_recovering", anchor_run_id=anchor, execution_policy=asdict(policy)
        )
    except Exception as error:
        with suppress(Exception):
            invocation.observe(
                "binding_unavailable",
                "Characterization recovery receipt unavailable",
                anchor_run_id=anchor,
                reason=type(error).__name__,
            )
