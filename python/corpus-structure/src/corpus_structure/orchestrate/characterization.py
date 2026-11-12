"""Explicit enriched-document demand over ordinary source execution and retained pins.

Each dependency stage freezes the actual predecessor products before scheduling. Existing
task reuse, worker ownership and source cuts remain authoritative; no query runs inference.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, replace
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from corpus_structure.core.vocab import Stage
from corpus_structure.semantic.characterization import characterization_profiles
from corpus_structure.semantic.characterization_store import (
    read_inventory,
    read_layer,
    read_layer_manifest,
)
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.structural_products import ExternalSourceRef

from .registry import MethodRegistry
from .runner import Graph, Step

PRIMARY_PRODUCERS = frozenset(
    {
        "text.native_evidence",
        "text.formal_evidence",
        "text.constructions",
        "text.contextual_characterization",
        "text.model_characterization",
        "text.evaluate_context",
    }
)


class CharacterizationDemandRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    project_id: str = Field(min_length=1)
    release_id: str = Field(min_length=1)
    realization_id: str = Field(min_length=1)
    domain: str = "statistics"
    base_document: ProductReference
    source_scope: dict[str, Any]
    selected_sources: tuple[ExternalSourceRef, ...]
    selected_layers: tuple[ProductReference, ...] = ()
    source_only: bool = False
    active_layers: tuple[ProductReference, ...] | None = None
    run_missing: bool = True
    fresh_methods: tuple[str, ...] = ()
    method_options: dict[str, dict[str, Any]] = Field(default_factory=dict)


@dataclass(frozen=True)
class EnrichedDocumentDemand:
    base_document: ProductReference
    source_scope: Mapping[str, Any]
    selected_layers: tuple[ProductReference, ...] = ()
    source_only: bool = False
    active_layers: tuple[ProductReference, ...] | None = None
    run_missing: bool = True
    fresh_methods: tuple[str, ...] = ()

    def __post_init__(self):
        if (
            len(set(self.fresh_methods)) != len(self.fresh_methods)
            or not set(self.fresh_methods) <= PRIMARY_PRODUCERS
        ):
            raise ValueError("fresh methods must be distinct primary producer names")
        if self.fresh_methods and (self.source_only or not self.run_missing):
            raise ValueError("fresh inference requires an enriching demand")
        if self.source_only and self.selected_layers:
            raise ValueError("source-only demand cannot select analytical layers")


@dataclass(frozen=True)
class EnrichedDocumentResult:
    view: ProductReference
    layers: tuple[ProductReference, ...]
    runs: tuple[int, ...]
    readiness: str
    missing_families: tuple[str, ...]
    preparation_diagnostics: tuple[str, ...] = ()
    anchor_run_id: int | None = None
    execution_policy: dict[str, Any] | None = None


def _inventory(engine, run_id):
    from corpus_structure.semantic.query import read_snapshot

    rows, after = [], None
    while True:
        with read_snapshot(engine) as conn:
            page = read_inventory(conn, run_id, after=after, limit=1000)
        rows.extend(page["products"])
        after = page["continuation"]
        if after is None:
            return rows


def enrich_document(*args, **kwargs):
    from contextlib import ExitStack

    from corpus_structure.core.work import drive_prepared_work
    from corpus_structure.semantic.execution_preparation import RegionalPreparation

    from .ready import owned_source_execution

    with ExitStack() as owners:
        execution = kwargs.get("execution_preparation")
        if execution is None:
            execution = owners.enter_context(
                owned_source_execution(
                    kwargs["prepared"], policy=kwargs["method_settings"].execution_policy
                )
            )
            kwargs["execution_preparation"] = execution
        if kwargs.get("regional_preparation") is None:
            kwargs["regional_preparation"] = owners.enter_context(RegionalPreparation(execution))
        return drive_prepared_work(_enrich_document_plan(*args, **kwargs), lambda: None)


def _enrich_document_plan(
    engine,
    *,
    demand: EnrichedDocumentDemand,
    project_id,
    prepared,
    binding,
    registry,
    method_settings,
    selected_sources,
    domain: str = "statistics",
    method_options: Mapping[str, Mapping[str, Any]] | None = None,
    preparation_cache: dict[str, dict[str, Any] | None] | None = None,
    on_created=None,
    execution_preparation=None,
    regional_preparation=None,
    characterization_operation=None,
    region_index=0,
):
    """Fulfil an explicit demand; provider profiles are frozen ordinary method options.

    Capture is a prerequisite, so failure here cannot erase the original document. Runs
    provide existing independent recovery/reuse boundaries between actual dependency stages.
    They are never selected or promoted here.
    """
    from corpus_structure.semantic.query import read_snapshot

    if execution_preparation is None:
        raise ValueError("incremental enrichment requires an owned execution scope")
    if characterization_operation is None:
        from .characterization_recovery import CharacterizationOperation

        request = CharacterizationDemandRequest(
            project_id=project_id,
            release_id=binding.release_id,
            realization_id=binding.input_realization_id,
            domain=domain,
            base_document=demand.base_document,
            source_scope=dict(demand.source_scope),
            selected_sources=tuple(selected_sources),
            selected_layers=demand.selected_layers,
            source_only=demand.source_only,
            active_layers=demand.active_layers,
            run_missing=demand.run_missing,
            fresh_methods=demand.fresh_methods,
            method_options=dict(method_options or {}),
        )
        cache = {} if preparation_cache is None else preparation_cache
        request, diagnostics = _freeze_request(
            engine,
            request,
            registry,
            prepared,
            method_settings,
            cache,
            execution_preparation=execution_preparation,
        )
        characterization_operation = CharacterizationOperation.freeze(
            (request,), registry, cache, diagnostics, method_settings.execution_policy
        )
        method_options = request.method_options
    options = method_options or {}
    required = set(characterization_profiles(prepared).get("full_characterization", ()))
    if not demand.source_only and not required:
        raise ValueError("full demand requires a released baseline family inventory")
    base = demand.base_document
    pins = list(demand.selected_layers)
    layers = {}

    def selected_layer(pin, run_id=None):
        with read_snapshot(engine) as conn:
            if demand.run_missing and regional_preparation is not None:
                return regional_preparation.layer(conn, pin, run_id=run_id)
            return (read_layer if demand.run_missing else read_layer_manifest)(
                conn, pin, run_id=run_id
            )

    def layer_plan(pin, run_id=None):
        if regional_preparation is None:
            return selected_layer(pin, run_id)
        (report,) = yield (regional_preparation.read_work(lambda: selected_layer(pin, run_id)),)
        return report

    for pin in pins:
        layers[pin] = yield from layer_plan(pin)
    if any(layer.base_document != base for layer in layers.values()):
        raise ValueError("enrichment selection mixes native documents")
    from corpus_structure.semantic.characterization import scope_contains

    selected_ids = {source.source_view_id for source in selected_sources}
    if len(selected_ids) != len(selected_sources):
        raise ValueError("enrichment requires one original custody selection per source view")
    if selected_ids != set(demand.source_scope["source_view_ids"]):
        raise ValueError("enrichment demand must name exactly its original source views")
    for source in selected_sources:
        if (
            source.project_id != project_id
            or ProductReference(
                source.native_task_id, source.native_product_key, source.native_content_digest
            )
            != base
        ):
            raise ValueError("enrichment source belongs to another project or document")
    for layer in layers.values():
        if not scope_contains(demand.source_scope, layer.payload["source_scope"]):
            raise ValueError("selected enrichment layer is outside demand source scope")
        if not {ProductReference(**value) for value in layer.payload["dependencies"]} <= set(pins):
            raise ValueError("enrichment selection lacks exact layer dependency closure")
    if len(set(pins)) != len(pins):
        raise ValueError("enrichment selection repeats a layer")
    active_pins = list(pins if demand.active_layers is None else demand.active_layers)
    if len(set(active_pins)) != len(active_pins) or not set(active_pins) <= set(pins):
        raise ValueError("active demand layers must be a distinct subset of retained closure")
    runs = (
        list(characterization_operation.recovered_runs.get(region_index, ()))
        if characterization_operation is not None
        else []
    )
    preparation_diagnostics = (
        list(characterization_operation.envelope.preparation_diagnostics)
        if characterization_operation is not None
        else []
    )

    def retained_context(parameters):
        """Reuse raw populations only under the same complete inference request."""
        from sqlalchemy import select

        from corpus_structure.methods.contextual_characterization import (
            ContextualCharacterizationConfig,
        )
        from corpus_structure.semantic.identity import canonical_bytes
        from corpus_structure.semantic.metadata import table

        cfg = ContextualCharacterizationConfig.model_validate(parameters).model_dump(mode="json")
        from corpus_structure.core.evidence import config_key

        from .registry import canonical_numbers

        current_hash = config_key(
            "text.contextual_characterization",
            registry.method("text.contextual_characterization").version,
            canonical_numbers(cfg),
        )
        if any(
            layers[pin].payload["operation"]["key"] == "text.contextual_characterization"
            and layers[pin].payload["operation"]["configuration"] == current_hash
            for pin in active_pins
        ):
            return []
        raw_keys = (
            "characterization_base_document",
            "characterization_source_scope",
            "focal",
            "native_token_layer",
            "native_runtime",
            "native_artifacts",
            "native_device",
            "language",
            "model",
        )
        candidates = []
        task, config = table("ops.task"), table("ops.method_config")
        with read_snapshot(engine) as conn:
            for pin in active_pins:
                body = layers[pin].payload
                if not compatible_execution(pin):
                    continue
                if body["operation"]["key"] != "text.contextual_characterization":
                    continue
                if not all(
                    any(
                        row["family"] == family and row["outcome"] in {"complete", "empty"}
                        for row in body["coverage"]
                    )
                    for family in (
                        "maverick.mentions",
                        "maverick.clusters",
                        "dipo.edus",
                        "dipo.rst",
                    )
                ):
                    continue
                previous = conn.execute(
                    select(config.c.params)
                    .select_from(task)
                    .join(config, task.c.method_config_id == config.c.id)
                    .where(task.c.id == pin.task_id)
                ).scalar_one()
                if all(
                    canonical_bytes(previous.get(key)) == canonical_bytes(cfg.get(key))
                    for key in raw_keys
                ):
                    # Follow an earlier retained request to its original raw producer;
                    # this keeps rule refreshes from growing a chain of copied semantics.
                    candidates.extend(
                        ProductReference(**value)
                        for value in previous.get("retained_native_layers", ())
                    )
                    if not previous.get("retained_native_layers"):
                        candidates.append(pin)
        candidates = list(dict.fromkeys(candidates))
        if len(candidates) > 1:
            raise ValueError(
                "rival retained context populations require explicit native evidence selection"
            )
        return candidates

    def compatible_execution(pin):
        from sqlalchemy import select

        from corpus_structure.semantic.metadata import table

        from .characterization_recovery import native_thread_profile

        task, run = table("ops.task"), table("ops.run")
        with read_snapshot(engine) as conn:
            previous = conn.scalar(
                select(run.c.options)
                .select_from(task.join(run, task.c.run_id == run.c.id))
                .where(task.c.id == pin.task_id)
            )
        profile = (previous or {}).get("physical_policy", {})
        return all(
            profile.get(key) == value
            for key, value in native_thread_profile(method_settings.execution_policy).items()
        )

    def stage(names: Sequence[str], additions=None):
        nonlocal pins, active_pins
        configs = {name: dict(values) for name, values in registry.file.configs.items()}
        inputs = {
            "text.native_evidence": set(),
            "text.formal_evidence": set(),
            "text.constructions": {"text.native_evidence", "text.formal_evidence"},
            "text.contextual_characterization": {
                "text.native_evidence",
                "text.formal_evidence",
                "text.constructions",
            },
            "text.model_characterization": {
                "text.native_evidence",
                "text.formal_evidence",
                "text.constructions",
                "text.contextual_characterization",
            },
            "text.evaluate_context": {
                "text.native_evidence",
                "text.formal_evidence",
                "text.constructions",
                "text.contextual_characterization",
                "text.model_characterization",
            },
        }
        for name in names:
            parameters = dict(registry.file.configs.get(name, {}).get("default", {}))
            parameters.update(options.get(name, {}))
            forbidden = {
                "characterization_base_document",
                "characterization_source_scope",
                "characterization_layers",
            } & parameters.keys()
            if forbidden:
                raise ValueError("method options cannot replace demand source/dependency pins")
            parameters.update(
                characterization_base_document=base.values(),
                characterization_source_scope=dict(demand.source_scope),
            )
            parameters["characterization_layers"] = [
                p.values()
                for p in sorted(
                    active_pins, key=lambda pin: (pin.task_id, pin.product_key, pin.content_digest)
                )
                if name not in inputs or layers[p].payload["operation"]["key"] in inputs[name]
            ]
            if name == "text.formal_evidence":
                parameters.setdefault(
                    "macros", registry.file.sections.get("math", {}).get("macros", {})
                )
            if name == "text.constructions":
                parameters.setdefault("math_scope_binders", registry.file.sections.get("binders"))
                parameters.setdefault(
                    "math_domain_rules",
                    registry.file.sections.get("math", {}).get("native_domain_rules", ()),
                )
            if name == "text.compose_view":
                parameters["characterization_layers"] = [p.values() for p in pins]
                parameters["characterization_active_layers"] = [p.values() for p in active_pins]
            if name == "text.model_characterization":
                from corpus_structure.semantic.model_characterization import question_manifest

                parameters.setdefault("question_manifest", question_manifest(prepared))
            for key, value in (additions or {}).get(name, {}).items():
                parameters.setdefault(key, value)
            if (
                name == "text.contextual_characterization"
                and "native_mode" not in options.get(name, {})
                and name not in demand.fresh_methods
            ):
                retained = retained_context(parameters)
                if retained:
                    parameters.update(
                        native_mode="retained",
                        retained_native_layers=[p.values() for p in retained],
                    )
            configs.setdefault(name, {})["characterization"] = parameters
        selected = MethodRegistry(
            registry.methods(),
            replace(registry.file, configs=configs),
            registry.sources,
            prepared=prepared,
        )
        active = []
        reused = {}
        for name in names:
            expected = selected.resolve(name, "characterization")
            matches = [
                pin
                for pin, layer in layers.items()
                if layer.payload["operation"]["key"] == name
                and layer.payload["operation"]["version"] == selected.method(name).version
                and layer.payload["operation"]["configuration"] == expected.config_hash
                and layer.payload["source_scope"] == dict(demand.source_scope)
                and (name not in PRIMARY_PRODUCERS or compatible_execution(pin))
            ]
            if (
                name in demand.fresh_methods
                and characterization_operation is not None
                and characterization_operation.recovering
            ):
                matches = [
                    pin for pin in matches if pin in characterization_operation.recovered_layers
                ]
            reusable = name not in demand.fresh_methods or (
                characterization_operation is not None and characterization_operation.recovering
            )
            selected_matches = [pin for pin in matches if pin in active_pins]
            if reusable and len(selected_matches or matches) > 1:
                raise ValueError("rival reusable layers require an explicit active selection")
            if name != "text.compose_view" and reusable and matches:
                reused[name] = (selected_matches or matches)[0]
            else:
                active.append(name)
        for name, pin in reused.items():
            active_pins = [
                p for p in active_pins if layers[p].payload["operation"]["key"] != name
            ] + [pin]
        if not active:
            return []
        from .semantic import _source_methods_plan

        result = yield from _source_methods_plan(
            execution_preparation.cpu,
            engine,
            execution_preparation=execution_preparation,
            regional_preparation=regional_preparation,
            on_created=lambda created: (
                characterization_operation.created(created, on_created)
                if characterization_operation is not None
                else on_created(created)
                if on_created is not None
                else None
            ),
            source_run_options=(lambda: characterization_operation.options(region_index, names))
            if characterization_operation is not None
            else None,
            freshness_seed=characterization_operation.envelope.freshness_seed
            if characterization_operation is not None
            else None,
            project_id=project_id,
            prepared=prepared,
            binding=binding,
            registry=selected,
            graph=Graph(
                ((Stage.EXTRACT, tuple(Step(name + "/characterization") for name in active)),),
                policy_propose=False,
            ),
            method_settings=method_settings,
            selected_sources=selected_sources,
            kind="full",
            extraction_policy="phase0",
            domain=domain,
            fresh=tuple(name for name in active if name in demand.fresh_methods),
        )
        runs.append(int(result.run_id))
        products = _inventory(engine, result.run_id)
        for row in products:
            if row["kind"] == "layer":
                pin = ProductReference(**row["reference"])
                if pin not in layers:
                    layers[pin] = yield from layer_plan(pin, result.run_id)
                    pins.append(pin)
                name = layers[pin].payload["operation"]["key"]
                active_pins = [
                    p for p in active_pins if layers[p].payload["operation"]["key"] != name
                ] + [pin]
        return products

    if not demand.source_only and demand.run_missing:
        # Only semantic dependency edges order stages; source evidence and formal syntax
        # are independent operations in the same ordinary execution group.
        yield from stage(("text.native_evidence", "text.formal_evidence"))
        yield from stage(("text.constructions",))
        token_layers = [
            pin
            for pin in active_pins
            if layers[pin].payload["operation"]["key"] == "text.native_evidence"
        ]
        if len(token_layers) > 1 and "native_token_layer" not in options.get(
            "text.contextual_characterization", {}
        ):
            raise ValueError(
                "rival native layers require an explicit contextual token-layer selection"
            )
        context_options = (
            {"text.contextual_characterization": {"native_token_layer": token_layers[0].values()}}
            if len(token_layers) == 1
            else {}
        )
        yield from stage(("text.contextual_characterization",), context_options)
        yield from stage(("text.model_characterization",))
        symbolic = [
            pin
            for pin in sorted(
                active_pins, key=lambda pin: (pin.task_id, pin.product_key, pin.content_digest)
            )
            if layers[pin].payload["operation"]["key"] == "text.constructions"
        ]
        roots = []
        for pin in symbolic:
            body = layers[pin].payload
            children = {
                e["target"] for t in body["terms"] for e in t.get("children", ()) if "target" in e
            }
            children.update(m["root"] for g in body["choices"] for m in g["members"])
            roots.extend(
                {"layer": pin.values(), "local_id": t["local_id"]}
                for t in body["terms"]
                if t["local_id"] not in children
            )
        context_layers = [
            pin.values()
            for pin in sorted(
                active_pins, key=lambda pin: (pin.task_id, pin.product_key, pin.content_digest)
            )
            if layers[pin].payload["operation"]["key"]
            in {"text.contextual_characterization", "text.model_characterization"}
        ]
        yield from stage(
            ("text.evaluate_context",),
            {"text.evaluate_context": dict(symbolic_roots=roots, context_layers=context_layers)},
        )

    # Composition is an ordinary producing method, never a mutable latest pointer.
    # Keep all dependencies for validation/provenance without selecting their old
    # interpretations as analytical inputs. Remove unrelated superseded roots.
    retained = set(active_pins)
    pending = list(active_pins)
    while pending:
        pin = pending.pop()
        for value in layers[pin].payload["dependencies"]:
            dep = ProductReference(**value)
            if dep not in retained:
                if dep not in layers:
                    layers[dep] = yield from layer_plan(dep)
                retained.add(dep)
                pending.append(dep)
    pins = sorted(retained, key=lambda pin: (pin.task_id, pin.product_key, pin.content_digest))
    active_pins.sort(key=lambda pin: (pin.task_id, pin.product_key, pin.content_digest))
    layers = {pin: layers[pin] for pin in pins}
    coverage = [row for pin in active_pins for row in layers[pin].payload["coverage"]]
    present = {row["family"] for row in coverage}
    profile = (
        "source_only"
        if not pins
        else "full_characterization"
        if required <= present
        else "selected_layers"
    )
    products: list[dict[str, Any]] | None = None
    if characterization_operation is not None and characterization_operation.recovering:
        from corpus_structure.semantic.characterization_store import read_view

        for reference in reversed(characterization_operation.recovered_views.get(region_index, ())):
            with read_snapshot(engine) as conn:
                body = read_view(conn, reference).payload
            if (
                body["base_document"] == base.values()
                and body["source_scope"] == dict(demand.source_scope)
                and body["layers"] == [pin.values() for pin in pins]
                and body.get("active_layers", body["layers"])
                == [pin.values() for pin in active_pins]
                and body["profile"] == profile
            ):
                products = [{"kind": "view", "reference": reference.values()}]
                break
    if products is None:
        products = yield from stage(
            ("text.compose_view",), {"text.compose_view": dict(characterization_profile=profile)}
        )
    views = [ProductReference(**row["reference"]) for row in products if row["kind"] == "view"]
    if len(views) != 1:
        raise ValueError("enrichment demand did not produce one exact composed view")
    missing = tuple(
        sorted(
            (required - present if not demand.source_only else set())
            | {row["family"] for row in coverage if row["outcome"] not in {"complete", "empty"}}
        )
    )
    from corpus_structure.cli.observation_logging import event

    event(
        "characterization_region_settled",
        "Characterization view settled",
        anchor_run_id=characterization_operation.anchor_run_id
        if characterization_operation is not None
        else None,
        region=region_index,
        run_ids=runs,
        task_id=views[0].task_id,
        view=views[0].values(),
        readiness="source_only" if not pins else "partial" if missing else "enriched",
        missing_families=list(missing),
        activity="settled",
    )
    return EnrichedDocumentResult(
        views[0],
        tuple(pins),
        tuple(runs),
        "source_only" if not pins else "partial" if missing else "enriched",
        missing,
        tuple(preparation_diagnostics),
        characterization_operation.anchor_run_id
        if characterization_operation is not None
        else None,
        asdict(execution_preparation.cpu.policy),
    )


def _freeze_request(
    engine,
    request,
    registry,
    prepared,
    method_settings,
    preparation_cache,
    *,
    execution_preparation=None,
):
    """Freeze semantic provider/configuration selection before the first task is admitted."""
    from corpus_structure.methods.native_evidence_layers import has_selected_native_text
    from corpus_structure.semantic.execution_preparation import RegionalPreparation
    from corpus_structure.semantic.operations import OperationConflict
    from corpus_structure.semantic.query import read_snapshot

    preparation_diagnostics = []
    native_profiles = preparation_cache
    has_text = False
    for identity in request.source_scope["source_view_ids"]:
        if execution_preparation is None:
            raise ValueError("source preflight requires an owned execution preparation")
        # Preflight precedes this demand's jobs. It still shares invocation credit;
        # keep only the Boolean, never book-wide hydrated source objects.
        with RegionalPreparation(execution_preparation) as regional, read_snapshot(engine) as conn:
            has_text = has_selected_native_text(
                regional.source_view(conn, identity, analysis=False, prepared=prepared),
                request.source_scope["selectors"],
            )
        if has_text:
            break

    def native_profile(provider):
        if provider not in native_profiles:
            from pathlib import Path

            import corpus_structure.methods.pm2_native as native_module
            from corpus_structure.methods.pm2_worker import (
                Pm2WorkerError,
                Pm2WorkerRefused,
                preflight_pm2_runtime,
            )

            script = Path(native_module.__file__)
            root = script.resolve().parents[5]
            project = root if provider == "d1" else root / f"services/pm2-{provider}"
            try:
                native_profiles[provider] = preflight_pm2_runtime(
                    python=project / ".venv/bin/python",
                    script=script,
                    project=project,
                    provider=provider,
                    assets=method_settings.model_cache / "pm2",
                )
            except (Pm2WorkerError, Pm2WorkerRefused) as error:
                native_profiles[provider] = None
                preparation_diagnostics.append(f"{provider}: {error}")
        return native_profiles[provider]

    def freeze_providers(name, parameters):
        # Authentication precedes task/configuration identity and every reuse lookup.
        if not has_text:
            return
        if (
            name == "text.native_evidence"
            and parameters.get("characterization_profile", "full_native") == "full_native"
        ):
            if (
                parameters.get("hanlp_runtime") is None
                and parameters.get("hanlp_artifacts") is None
            ):
                profile = native_profile("hanlp")
                if profile is not None:
                    parameters.update(
                        hanlp_runtime=profile["runtime_identity"], hanlp_artifacts=profile["assets"]
                    )
        elif (
            name == "text.contextual_characterization"
            and parameters.get("native_mode", "infer") == "infer"
        ):
            runtimes, artifacts = (
                dict(parameters.get("native_runtime", {})),
                dict(parameters.get("native_artifacts", {})),
            )
            for provider in ("maverick", "dipo"):
                if provider not in runtimes and provider not in artifacts:
                    profile = native_profile(provider)
                    if profile is not None:
                        runtimes[provider], artifacts[provider] = (
                            profile["runtime_identity"],
                            profile["assets"],
                        )
            parameters.update(native_runtime=runtimes, native_artifacts=artifacts)
        elif (
            name == "text.model_characterization"
            and parameters.get("d1_runtime") is None
            and parameters.get("d1_artifacts") is None
        ):
            profile = native_profile("d1")
            if profile is not None:
                parameters.update(
                    d1_runtime=profile["runtime_identity"], d1_artifacts=profile["assets"]
                )

    options = {}
    names = (
        (*sorted(PRIMARY_PRODUCERS), "text.compose_view")
        if request.run_missing and not request.source_only
        else ("text.compose_view",)
    )
    for name in names:
        parameters = dict(registry.file.configs.get(name, {}).get("default", {}))
        parameters.update(request.method_options.get(name, {}))
        if {
            "characterization_base_document",
            "characterization_source_scope",
            "characterization_layers",
        } & parameters.keys():
            raise ValueError("method options cannot replace demand source/dependency pins")
        if name == "text.formal_evidence":
            parameters.setdefault(
                "macros", registry.file.sections.get("math", {}).get("macros", {})
            )
        if name == "text.constructions":
            parameters.setdefault("math_scope_binders", registry.file.sections.get("binders"))
            parameters.setdefault(
                "math_domain_rules",
                registry.file.sections.get("math", {}).get("native_domain_rules", ()),
            )
        if name == "text.model_characterization":
            from corpus_structure.semantic.model_characterization import question_manifest

            parameters.setdefault("question_manifest", question_manifest(prepared))
        device_fields = {
            "text.native_evidence": {"hanlp_device": "cpu"},
            "text.contextual_characterization": {"native_device": "cpu"},
            "text.model_characterization": {"d1_device": "cuda"},
        }
        for field, device in device_fields.get(name, {}).items():
            if parameters.get(field, device) != device:
                raise OperationConflict(f"characterization requires {field}={device}")
            parameters.setdefault(field, device)
        config_type = registry.method(name).Config
        supplied = dict(parameters)
        if name == "text.compose_view":
            parameters.setdefault(
                "characterization_profile",
                "selected_layers" if request.selected_layers else "source_only",
            )
        selected_fields = {
            "characterization_base_document": request.base_document.values(),
            "characterization_source_scope": request.source_scope,
            "characterization_layers": [pin.values() for pin in request.selected_layers],
        }
        resolved = config_type.model_validate(
            {
                **parameters,
                **{
                    key: value
                    for key, value in selected_fields.items()
                    if key in config_type.model_fields
                },
            }
        ).model_dump(mode="json")
        if name == "text.model_characterization" and resolved.get("gliner_profile") is not None:
            from corpus_structure.methods.characterization_resources import validate_gliner_policy
            from corpus_structure.methods.gliner import GlinerProfile, GlinerRefused

            profile = TypeAdapter(GlinerProfile).validate_python(
                resolved["gliner_profile"]["profile"]
            )
            try:
                validate_gliner_policy(profile, method_settings.execution_policy)
            except GlinerRefused as error:
                raise OperationConflict(str(error)) from error
        for key in selected_fields:
            resolved.pop(key, None)
        # These inputs are determined from actual predecessor products at their stage.
        dynamic = {
            "native_token_layer",
            "retained_native_layers",
            "native_mode",
            "symbolic_roots",
            "context_layers",
            "characterization_active_layers",
        }
        if name == "text.compose_view":
            dynamic.add("characterization_profile")
        for key in dynamic - supplied.keys():
            resolved.pop(key, None)
        options[name] = resolved
    # Resolve every knowable config/profile refusal before launching preflight children.
    if request.run_missing and not request.source_only:
        for name, parameters in options.items():
            freeze_providers(name, parameters)
    return request.model_copy(update={"method_options": options}), tuple(preparation_diagnostics)


def execute_characterization_demand(
    engine,
    request: CharacterizationDemandRequest,
    method_settings,
    *,
    preparation_cache=None,
    registry=None,
    on_created=None,
):
    from corpus_structure.semantic.execution_preparation import prepare_execution
    from corpus_structure.semantic.query import read_snapshot

    with read_snapshot(engine) as conn:
        execution = prepare_execution(
            conn, request.release_id, policy=method_settings.execution_policy
        )
    with execution:
        return _execute_characterization_demand(
            execution,
            engine=engine,
            request=request,
            method_settings=method_settings,
            preparation_cache=preparation_cache,
            registry=registry,
            on_created=on_created,
        )


def _execute_characterization_demand(execution, *args, **kwargs):
    from corpus_structure.core.work import drive_prepared_work

    return drive_prepared_work(_demand_plan(execution, *args, **kwargs), lambda: None)


def _demand_plan(
    execution,
    engine,
    request: CharacterizationDemandRequest,
    method_settings,
    *,
    preparation_cache=None,
    registry=None,
    on_created=None,
    characterization_operation=None,
    region_index=0,
):
    """Public execution boundary: exact released demand, never a query-side parser."""
    from sqlalchemy import select

    from corpus_structure.schema.pack import DOMAINS
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.operations import OperationBinding
    from corpus_structure.semantic.query import read_snapshot

    from .phase0 import registry as registry_for

    with read_snapshot(engine) as conn:
        from sqlalchemy import text

        prepared = execution.require_release(request.release_id)
        for selected_source in request.selected_sources:
            conn.execute(
                text("SELECT ops.validate_structural_source(CAST(:source AS jsonb))"),
                {"source": canonical_bytes(selected_source.model_dump(mode="json")).decode()},
            ).scalar_one()
        realization = table("data.realization")
        source = (
            conn.execute(
                select(realization).where(
                    realization.c.realization_id == request.realization_id,
                    realization.c.project_id == request.project_id,
                    realization.c.release_id == request.release_id,
                )
            )
            .mappings()
            .one()
        )
    binding = OperationBinding(
        request.release_id,
        request.realization_id,
        source["data_revision"],
        canonical_bytes(dict(domain=request.domain, release=request.release_id)),
    )
    selected = (registry or registry_for(DOMAINS / request.domain)).bind_release(prepared)
    if characterization_operation is None:
        from .characterization_recovery import CharacterizationOperation

        cache = {} if preparation_cache is None else preparation_cache
        request, diagnostics = _freeze_request(
            engine,
            request,
            selected,
            prepared,
            method_settings,
            cache,
            execution_preparation=execution,
        )
        characterization_operation = CharacterizationOperation.freeze(
            (request,), selected, cache, diagnostics, method_settings.execution_policy
        )
    request = characterization_operation.request(region_index, request)
    from corpus_structure.semantic.execution_preparation import RegionalPreparation

    with RegionalPreparation(execution) as regional:
        return (
            yield from _enrich_document_plan(
                engine,
                execution_preparation=execution,
                regional_preparation=regional,
                characterization_operation=characterization_operation,
                region_index=region_index,
                demand=EnrichedDocumentDemand(
                    request.base_document,
                    request.source_scope,
                    request.selected_layers,
                    request.source_only,
                    request.active_layers,
                    request.run_missing,
                    request.fresh_methods,
                ),
                project_id=request.project_id,
                prepared=prepared,
                binding=binding,
                registry=selected,
                method_settings=method_settings,
                selected_sources=request.selected_sources,
                method_options=request.method_options,
                preparation_cache=preparation_cache,
                domain=request.domain,
                on_created=on_created,
            )
        )


def bind_characterization_views(registry, views, layers):
    """Freeze explicitly selected document-view closures for local and cross-document analytics."""
    if not views or any(view.payload["profile"] == "source_only" for view in views):
        raise ValueError("analytical consumers require explicit enriched views")
    closure = list(
        dict.fromkeys(
            ProductReference(**value) for view in views for value in view.payload["layers"]
        )
    )
    pins = list(
        dict.fromkeys(
            ProductReference(**value)
            for view in views
            for value in view.payload.get("active_layers", view.payload["layers"])
        )
    )
    if set(closure) != set(layers):
        raise ValueError("consumer binding differs from exact composed-view closures")
    configs = {name: dict(values) for name, values in registry.file.configs.items()}
    for method in registry.methods():
        if "characterization_layers" not in method.Config.model_fields:
            continue
        for owner, name in registry.named():
            if owner != method.name:
                continue
            params = dict(configs.setdefault(method.name, {}).get(name, {}))
            params["characterization_layers"] = [pin.values() for pin in pins]
            configs[method.name][name] = params
    return MethodRegistry(
        registry.methods(),
        replace(registry.file, configs=configs),
        registry.sources,
        prepared=registry.prepared,
    )


def characterize_captured_run(
    engine,
    run,
    *,
    project_id,
    release_id,
    realization_id,
    domain,
    method_settings,
    method_options,
    registry=None,
    on_created=None,
    fresh_methods=(),
):
    from corpus_structure.semantic.execution_preparation import prepare_execution
    from corpus_structure.semantic.query import read_snapshot

    with read_snapshot(engine) as conn:
        execution = prepare_execution(conn, release_id, policy=method_settings.execution_policy)
    with execution:
        return _characterize_captured_run(
            execution,
            engine=engine,
            run=run,
            project_id=project_id,
            release_id=release_id,
            realization_id=realization_id,
            domain=domain,
            method_settings=method_settings,
            method_options=method_options,
            registry=registry,
            on_created=on_created,
            fresh_methods=fresh_methods,
        )


def _characterize_captured_run(
    execution,
    engine,
    run,
    *,
    project_id,
    release_id,
    realization_id,
    domain,
    method_settings,
    method_options,
    registry=None,
    on_created=None,
    fresh_methods=(),
    source_operation=None,
):
    """Attach enrichment after ordinary capture, retaining that completed source cut."""
    from sqlalchemy import select, text

    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.query import read_snapshot
    from corpus_structure.semantic.source_views import selected_source_views

    from .commands import finalize_bound_run

    # A capture branch has no knowledge promotion. Completing its existing run is
    # necessary for portable original-source references used by later stages.
    with read_snapshot(engine) as conn:
        source_runs = table("ops.run")
        origin = (
            conn.execute(select(source_runs).where(source_runs.c.id == int(run.run_id)))
            .mappings()
            .one()
        )
        if origin["project_id"] != project_id:
            raise ValueError("captured source belongs to another project")
        origin_release_id = origin["release_id"]
    if origin["status"] != "finished" or not origin["sealed"]:
        finalize_bound_run(engine, int(run.run_id), f"characterization-capture:{int(run.run_id)}")
    requests = []
    with read_snapshot(engine) as conn:
        completed, batch, source_run, selection = map(
            table, ("ops.completed_result", "data.batch", "ops.run", "ops.run_source_view")
        )
        # Natural source views bound independent layer publication and recovery.
        # A PDF-wide token report would exceed the existing bounded product reader.
        for ref in selected_source_views(conn, int(run.run_id)):
            base, refs = ref.native_product, (ref,)
            # Repeated capture can select the same immutable SourceView. Keep its
            # earliest completed custody instead of changing every producer's input
            # to a new capture run. Native source validation still checks the exact
            # project/release/cut/revision/view/product association.
            result = (
                conn.execute(
                    select(source_run.c.id, completed.c.cut_id, batch.c.data_revision)
                    .select_from(source_run)
                    .join(completed, completed.c.run_id == source_run.c.id)
                    .join(
                        batch,
                        (batch.c.release_id == completed.c.release_id)
                        & (batch.c.realization_id == completed.c.output_realization_id)
                        & (batch.c.batch_id == completed.c.batch_id),
                    )
                    .where(
                        source_run.c.project_id == project_id,
                        source_run.c.release_id == origin_release_id,
                        source_run.c.status == "finished",
                        source_run.c.sealed,
                        select(selection.c.source_view_id)
                        .where(
                            selection.c.run_id == source_run.c.id,
                            selection.c.source_view_id == ref.id,
                        )
                        .exists(),
                    )
                    .order_by(source_run.c.id)
                    .limit(1)
                )
                .mappings()
                .one()
            )
            sources, source_pins, selectors = [], [], []
            from corpus_structure.semantic.execution_preparation import RegionalPreparation

            for ref in refs:
                with RegionalPreparation(execution) as regional:
                    view = regional.source_view(
                        conn, ref, analysis=False, prepared=execution.prepared
                    )
                    sources.append(
                        ExternalSourceRef(
                            project_id=project_id,
                            run_id=result["id"],
                            cut_id=result["cut_id"],
                            release_id=origin_release_id,
                            result_revision=result["data_revision"],
                            source_view_id=ref.id,
                            native_task_id=base.task_id,
                            native_product_key=base.product_key,
                            native_content_digest=base.content_digest,
                            projection_digest=ref.projection_digest,
                            recipe_digest=ref.recipe_digest,
                            coordinate_version=3 if view.integrated_context is not None else 2,
                        )
                    )
                    conn.execute(
                        text("SELECT ops.validate_structural_source(CAST(:source AS jsonb))"),
                        {"source": canonical_bytes(sources[-1].model_dump(mode="json")).decode()},
                    ).scalar_one()
                    source_pins.append(
                        dict(
                            source_view_id=ref.id,
                            key=ref.key,
                            base_document=base.values(),
                            section_pointer=ref.section_pointer,
                            membership=ref.membership,
                            projection_digest=ref.projection_digest,
                            recipe_digest=ref.recipe_digest,
                        )
                    )
                    selectors.append(
                        dict(projection=ref.projection_digest, start=0, end=len(view.text))
                    )
                    del view
            requests.append(
                CharacterizationDemandRequest(
                    project_id=project_id,
                    release_id=release_id,
                    realization_id=realization_id,
                    domain=domain,
                    base_document=base,
                    source_scope=dict(
                        source_view_ids=[ref.id for ref in refs],
                        source_views=source_pins,
                        selectors=selectors,
                        profile="full_document",
                    ),
                    selected_sources=tuple(sources),
                    method_options=method_options,
                    fresh_methods=tuple(fresh_methods),
                )
            )
    preparation_cache = {}
    from corpus_structure.schema.pack import DOMAINS

    from .characterization_recovery import CharacterizationOperation
    from .phase0 import registry as registry_for

    selected = (registry or registry_for(DOMAINS / domain)).bind_release(
        execution.require_release(release_id)
    )
    frozen, diagnostics = [], []
    for request in requests:
        request, messages = _freeze_request(
            engine,
            request,
            selected,
            execution.prepared,
            method_settings,
            preparation_cache,
            execution_preparation=execution,
        )
        frozen.append(request)
        diagnostics.extend(messages)
    requests = frozen
    operation = CharacterizationOperation.freeze(
        tuple(requests),
        selected,
        preparation_cache,
        tuple(diagnostics),
        method_settings.execution_policy,
        source_operation=source_operation,
    )
    from corpus_structure.core.work import ReadyGroup, drive_prepared_work

    def regions_plan():
        return (
            yield ReadyGroup(
                tuple(
                    _demand_plan(
                        execution,
                        engine,
                        request,
                        method_settings,
                        preparation_cache=preparation_cache,
                        registry=registry,
                        on_created=on_created,
                        characterization_operation=operation,
                        region_index=index,
                    )
                    for index, request in enumerate(requests)
                ),
                max_active=execution.cpu.policy.max_regions,
            )
        )

    regional = list(zip(requests, drive_prepared_work(regions_plan(), lambda: None), strict=True))
    return _combine_characterization_results(
        execution,
        engine,
        regional,
        method_settings,
        registry=registry,
        on_created=on_created,
        operation=operation,
    )


def _combine_characterization_results(
    execution, engine, regional, method_settings, *, registry=None, on_created=None, operation=None
):
    # Natural units bound inference and recovery; one composed document pin brings
    # their selected analyses together without running those producers again.
    from corpus_structure.semantic.characterization_store import read_view
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.query import read_snapshot

    documents = {}
    for request, result in regional:
        documents.setdefault(request.base_document, []).append((request, result))
    combined = []
    for base, entries in documents.items():
        if len(entries) == 1:
            combined.append(entries[0][1])
            continue
        refs, active, sources, scopes = [], [], [], []
        with read_snapshot(engine) as conn:
            for request, result in entries:
                view = read_view(conn, result.view).payload
                refs.extend(ProductReference(**value) for value in view["layers"])
                active.extend(
                    ProductReference(**value) for value in view.get("active_layers", view["layers"])
                )
                sources.extend(request.selected_sources)
                scopes.append(request.source_scope)
        scope = dict(
            source_view_ids=list(
                dict.fromkeys(value for item in scopes for value in item["source_view_ids"])
            ),
            source_views=[value for item in scopes for value in item["source_views"]],
            selectors=[value for item in scopes for value in item["selectors"]],
            profile="full_document",
        )
        # Exact selector correspondence is set-based; duplicate selectors from shared
        # source projections do not represent additional examined text.
        for name in ("source_views", "selectors"):
            scope[name] = list({canonical_bytes(value): value for value in scope[name]}.values())
        request = CharacterizationDemandRequest(
            project_id=entries[0][0].project_id,
            release_id=entries[0][0].release_id,
            realization_id=entries[0][0].realization_id,
            domain=entries[0][0].domain,
            base_document=base,
            source_scope=scope,
            selected_sources=tuple(sources),
            selected_layers=tuple(dict.fromkeys(refs)),
            active_layers=tuple(dict.fromkeys(active)),
            run_missing=False,
            method_options={
                "text.compose_view": entries[0][0].method_options.get("text.compose_view", {})
            },
        )
        result = _execute_characterization_demand(
            execution,
            engine,
            request,
            method_settings,
            registry=registry,
            on_created=on_created,
            characterization_operation=operation,
            region_index=-1,
        )
        missing = tuple(
            sorted(
                set(result.missing_families).union(*(part.missing_families for _, part in entries))
            )
        )
        combined.append(
            replace(
                result,
                missing_families=missing,
                readiness="partial" if missing else result.readiness,
                runs=tuple(
                    dict.fromkeys(
                        tuple(run for _, part in entries for run in part.runs) + result.runs
                    )
                ),
                preparation_diagnostics=tuple(
                    message for _, part in entries for message in part.preparation_diagnostics
                ),
            )
        )
    return tuple(combined)


def characterization_sources(conn, reference, view, *, project_id):
    """Recover original source selections from this exact view's producing run.

    A view made in its original capture run can use that run after completion.
    Otherwise its frozen selected-source inputs own origin/cut identity. No lookup
    by latest release, text equality or projection digest substitutes another view.
    """
    from sqlalchemy import select

    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.source_views import load_source_view

    task, run = table("ops.task"), table("ops.run")
    origin = (
        conn.execute(
            select(run)
            .select_from(task.join(run, run.c.id == task.c.run_id))
            .where(task.c.id == reference.task_id)
        )
        .mappings()
        .one()
    )
    if origin["project_id"] != project_id:
        raise ValueError("enriched view belongs to another project")
    import json

    manifest = json.loads(origin["dependencies"])
    frozen = [
        ExternalSourceRef.model_validate(value) for value in manifest.get("selected_sources", ())
    ]
    sources = []
    completed, batch, selection = (
        table("ops.completed_result"),
        table("data.batch"),
        table("ops.run_source_view"),
    )
    for identity in view.payload["source_scope"]["source_view_ids"]:
        matches = [source for source in frozen if source.source_view_id == identity]
        if len(matches) > 1:
            raise ValueError("enriched view has ambiguous original source selection")
        if matches:
            sources.append(matches[0])
            continue
        original = (
            conn.execute(
                select(completed.c.cut_id, batch.c.data_revision)
                .select_from(
                    completed.join(
                        batch,
                        (batch.c.release_id == completed.c.release_id)
                        & (batch.c.realization_id == completed.c.output_realization_id)
                        & (batch.c.batch_id == completed.c.batch_id),
                    ).join(selection, selection.c.run_id == completed.c.run_id)
                )
                .where(completed.c.run_id == origin["id"], selection.c.source_view_id == identity)
            )
            .mappings()
            .one_or_none()
        )
        if original is None or not origin["sealed"] or origin["status"] != "finished":
            raise ValueError("analytical binding requires completed original source custody")
        source = load_source_view(conn, identity, analysis=False)
        pin = source.ref.native_product
        sources.append(
            ExternalSourceRef(
                project_id=project_id,
                run_id=origin["id"],
                cut_id=original["cut_id"],
                release_id=origin["release_id"],
                result_revision=original["data_revision"],
                source_view_id=identity,
                native_task_id=pin.task_id,
                native_product_key=pin.product_key,
                native_content_digest=pin.content_digest,
                projection_digest=source.ref.projection_digest,
                recipe_digest=source.ref.recipe_digest,
                coordinate_version=3 if source.integrated_context is not None else 2,
            )
        )
    return tuple(sources)
