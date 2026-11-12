"""Eight baseline characterization families through existing resident native workers."""

from __future__ import annotations

import time
from collections.abc import Iterable
from dataclasses import asdict
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from corpus_structure.core._model.shapes import Cost
from corpus_structure.core.method import (
    Digest,
    ReadyGroup,
    Resources,
    UnitRef,
    UnitResult,
    drive_prepared_work,
)
from corpus_structure.core.vocab import MethodFamily, MethodTier, ObservationOutcome, TaskUnitType
from corpus_structure.semantic.cpu_execution import CapacityExceeded
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.interpretation_questions import (
    CHARACTERIZATION_FAMILIES,
    QuestionFamily,
    declared_families,
)
from corpus_structure.semantic.model_characterization import (
    CANDIDATE_FAMILIES,
    D1_SOURCE_FAMILIES,
    GLINER_CUES,
    GLINER_FUNCTIONS,
    FrozenCandidates,
    ModelCharacterizationBuilder,
    ModelScope,
    compile_question_stage,
    contextual_candidate_populations,
    gliner_cue_request,
    prepare_model_scope,
    project_gliner_cues,
    question_manifest,
)
from corpus_structure.semantic.product_reference import ProductReference

from .characterization_resources import (
    fork_builder,
    gliner_extract_members,
    merge_builder,
    pm2_client,
    provider_scope,
    validate_gliner_policy,
)
from .gliner_worker import GlinerWorkerError
from .model_observation import released_policy
from .pm2_gliner_classification import (
    ClassificationProfile,
    classification_product,
    classification_request,
)
from .pm2_worker import Pm2WorkerError, Pm2WorkerRefused

METHOD = "text.model_characterization"
MODEL = (
    "LiquidAI/d1-2B@652f920e544ea37f81e4b0ce89b81d4ed0da90b1+"
    "fastino/gliner2.5-base-v1@54785d51df8d86a0d8f2eb212fec15871aad2c4d"
)


class ModelSourceScope(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    source_view_id: int = Field(ge=1)
    focal_start: int = Field(ge=0)
    focal_end: int = Field(ge=1)
    context_start: int = Field(ge=0)
    context_end: int = Field(ge=1)

    @model_validator(mode="after")
    def nesting(self):
        if not self.context_start <= self.focal_start < self.focal_end <= self.context_end:
            raise ValueError("focal output must lie inside the complete examined context")
        return self


class ModelCharacterizationConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    characterization_base_document: dict[str, Any] | None = None
    characterization_source_scope: dict[str, Any] | None = None
    characterization_layers: tuple[dict[str, Any], ...] = ()
    question_manifest: dict[str, str] | None = None
    source_scopes: tuple[ModelSourceScope, ...] = ()
    model: str = Field(default=MODEL, min_length=1)
    grammar: Literal["none"] = "none"
    context: Literal["source-context-and-frozen-candidates-v1"] = (
        "source-context-and-frozen-candidates-v1"
    )
    d1_device: Literal["cuda"] = "cuda"
    d1_runtime: dict[str, Any] | None = None
    d1_artifacts: dict[str, Any] | None = None
    gliner_profile: ClassificationProfile | None = None
    gliner_runtime: dict[str, Any] | None = None
    max_context_chars: int = Field(default=65536, ge=1, le=65536)

    @model_validator(mode="after")
    def selected_models(self):
        if self.model != MODEL:
            raise ValueError("characterization requires the selected d1 and GLiNER checkpoints")
        if self.gliner_profile is not None and (
            self.gliner_profile.profile.checkpoint != "fastino/gliner2.5-base-v1"
            or self.gliner_profile.profile.revision != "54785d51df8d86a0d8f2eb212fec15871aad2c4d"
        ):
            raise ValueError("GLiNER profile differs from the selected characterization checkpoint")
        return self

    def require_selection(self):
        if (
            self.characterization_base_document is None
            or self.characterization_source_scope is None
        ):
            raise ValueError(
                "model characterization requires an exact base document and selected source scope"
            )
        pins = tuple(ProductReference(**pin) for pin in self.characterization_layers)
        if len(set(pins)) != len(pins):
            raise ValueError("model characterization requires distinct exact input layers")
        if any(
            scope.source_view_id not in self.characterization_source_scope["source_view_ids"]
            for scope in self.source_scopes
        ):
            raise ValueError("model focal/context scope references an unselected source view")
        if len({scope.model_dump_json() for scope in self.source_scopes}) != len(
            self.source_scopes
        ):
            raise ValueError("model focal/context scopes must be distinct")
        return (
            ProductReference(**self.characterization_base_document),
            self.characterization_source_scope,
            pins,
        )


def _dependency_closure(reader, pins):
    layers, pending = {}, tuple(pins)
    while pending:
        read = reader.characterization_layers(pending)
        if set(read) != set(pending):
            raise ValueError("model characterization has an incomplete retained input closure")
        layers.update(read)
        pending = tuple(
            dict.fromkeys(
                ProductReference(**pin)
                for layer in read.values()
                for pin in layer.payload.get("dependencies", ())
                if ProductReference(**pin) not in layers
            )
        )
    return layers


class ModelCharacterizationMethod:
    name = METHOD
    version = "2"
    family = MethodFamily.EXTRACT
    unit_type = TaskUnitType.DOCUMENT
    tier = MethodTier.DETERMINISTIC
    confidence_source = None
    Config = ModelCharacterizationConfig
    resources = Resources(worker="cpu", batch_size=1, max_concurrency=1)

    def select(self, run, cfg: ModelCharacterizationConfig) -> Iterable[UnitRef]:
        base, scope, _pins = cfg.require_selection()
        if cfg.question_manifest != question_manifest(run.reader.prepared):
            raise ValueError(
                "model characterization requires the exact frozen released question manifest"
            )
        selected = {ref.id: ref for ref in run.reader.source_views()}
        refs = [selected.get(identity) for identity in scope["source_view_ids"]]
        if not refs or any(ref is None or ref.native_product != base for ref in refs):
            raise ValueError(
                "model characterization source differs from the run's exact selected document"
            )
        documents = {ref.document_id for ref in refs if ref is not None}
        if len(documents) != 1:
            raise ValueError("model characterization requires one document")
        return (UnitRef(TaskUnitType.DOCUMENT, next(iter(documents))),)

    def input_digest(self, unit, cfg: ModelCharacterizationConfig) -> Digest:
        cfg.require_selection()
        families = declared_families(unit.run.reader.prepared.registry_rows)
        return Digest(
            canonical_bytes(
                dict(
                    method=self.name,
                    version=self.version,
                    release_id=unit.run.reader.prepared.release_id,
                    configuration=cfg.model_dump(mode="json"),
                    questions={name: families[name].digest for name in CHARACTERIZATION_FAMILIES},
                    document=unit.ref.unit_id,
                )
            )
        )

    def run(self, units, cfg: ModelCharacterizationConfig, ctx):
        return drive_prepared_work(self.plan(units, cfg, ctx), ctx.check_active)

    def plan(self, units, cfg: ModelCharacterizationConfig, ctx):
        with provider_scope(units, policy=ctx.settings.execution_policy) as (_cpu, providers):
            from .characterization_resources import selections_for_characterization
            if providers is not None:
                providers.declare_native(selections_for_characterization({'text.model_characterization': cfg.model_dump(mode="json")}, ctx.settings), ctx.settings.nemotron_endpoint)
            base, scope, pins = cfg.require_selection()
            results = []
            for unit in units:
                started = time.monotonic()
                ctx.check_active()
                if unit.ref not in self.select(unit.run, cfg):
                    raise ValueError(
                        "model characterization task differs from its selected document"
                    )
                reader = unit.run.reader
                families = declared_families(reader.prepared.registry_rows)
                if not set(CHARACTERIZATION_FAMILIES) <= families.keys():
                    raise ValueError(
                        "release lacks one or more baseline characterization question families"
                    )
                operation = ctx.characterization_operation(unit.ref)
                if any(
                    operation[key] != expected
                    for key, expected in dict(
                        key=METHOD,
                        version=self.version,
                        model=cfg.model,
                        grammar=cfg.grammar,
                        context=cfg.context,
                    ).items()
                ):
                    raise ValueError(
                        "model characterization task differs from its frozen determinants"
                    )
                dependencies = _dependency_closure(reader, pins)
                if any(layer.base_document != base for layer in dependencies.values()):
                    raise ValueError(
                        "model characterization input layer belongs to another base document"
                    )
                builder = ModelCharacterizationBuilder(base.values(), scope, operation)
                builder.operation["required_layers"] = [pin.values() for pin in pins]
                scopes = self._scopes(reader, cfg, builder)
                if scopes:
                    d1 = fork_builder(builder)
                    gliner = fork_builder(builder)
                    yield ReadyGroup(
                        (
                            self._d1(
                                cfg,
                                ctx,
                                d1[0],
                                scopes,
                                families,
                                {pin: dependencies[pin] for pin in pins},
                                providers,
                            ),
                            self._gliner(
                                cfg, ctx, reader.prepared, gliner[0], scopes, families, providers
                            ),
                        )
                    )
                    merge_builder(builder, d1)
                    merge_builder(builder, gliner)
                releases = {reader.prepared.release_id: reader.prepared}
                for layer in dependencies.values():
                    release_id = layer.payload["release_id"]
                    if release_id not in releases:
                        releases[release_id] = reader.characterization_release(release_id)
                layer = builder.finish(
                    reader.prepared, dependencies=dependencies, releases=releases
                )
                results.append(
                    UnitResult(
                        ref=unit.ref,
                        outcome=ObservationOutcome.PRODUCED,
                        characterization_layer=layer,
                        cost=Cost(
                            wall_ms=round((time.monotonic() - started) * 1000), model=cfg.model
                        ),
                    )
                )
            return tuple(results)

    def _scopes(self, reader, cfg, builder):
        from .native_evidence_layers import has_selected_native_text

        scopes = []
        explicit = cfg.source_scopes
        for identity in builder.scope["source_view_ids"]:
            view = reader.source_view(identity)
            selectors = [
                selector
                for selector in builder.scope["selectors"]
                if selector["projection"] == view.ref.projection_digest
            ]
            requested = [row for row in explicit if row.source_view_id == identity]
            if not requested and not has_selected_native_text(view, selectors):
                for family in CHARACTERIZATION_FAMILIES:
                    builder.record(family, selectors, "empty")
                continue
            if not explicit:
                # A pointer-only selector denotes its actual native pieces, not the book.
                intervals = [
                    (piece["start"], piece["end"])
                    for selector in selectors
                    for piece in view.pieces
                    if piece["kind"] == "native_text"
                    and (
                        not selector.get("native_pointer")
                        or selector["native_pointer"] == piece.get("item_ref")
                    )
                    and selector.get("start", 0)
                    <= piece["start"]
                    < piece["end"]
                    <= selector.get("end", len(view.text))
                ]
                native_pieces = [piece for piece in view.pieces if piece["kind"] == "native_text"]
                if native_pieces and all(
                    (piece["start"], piece["end"]) in intervals for piece in native_pieces
                ):
                    # The retained source view is already a natural hierarchy scope.
                    # Keep its full context rather than silently replacing it by windows.
                    intervals = [(0, len(view.text))]
                requested = [
                    ModelSourceScope(
                        source_view_id=identity,
                        focal_start=a,
                        focal_end=b,
                        context_start=a,
                        context_end=b,
                    )
                    for a, b in dict.fromkeys(intervals)
                ]
            for row in requested:
                allowed = sorted(
                    (
                        max(selector.get("start", 0), piece["start"]),
                        min(selector.get("end", len(view.text)), piece["end"]),
                    )
                    for selector in selectors
                    for piece in view.pieces
                    if piece["kind"] == "native_text"
                    and (
                        not selector.get("native_pointer")
                        or selector["native_pointer"] == piece.get("item_ref")
                    )
                    and max(selector.get("start", 0), piece["start"])
                    < min(selector.get("end", len(view.text)), piece["end"])
                )
                # Native source extents inside the examined interval must all be selected.
                if any(
                    not any(
                        a <= max(row.context_start, piece["start"])
                        and min(row.context_end, piece["end"]) <= b
                        for a, b in allowed
                    )
                    for piece in view.pieces
                    if piece["kind"] == "native_text"
                    and piece["start"] < row.context_end
                    and row.context_start < piece["end"]
                ):
                    raise ValueError("model examined context contains unselected source characters")
                try:
                    scopes.append(
                        prepare_model_scope(
                            view,
                            (row.focal_start, row.focal_end),
                            (row.context_start, row.context_end),
                            max_chars=cfg.max_context_chars,
                        )
                    )
                except ValueError as error:
                    for family in CHARACTERIZATION_FAMILIES:
                        builder.record(
                            family,
                            [
                                dict(
                                    projection=view.ref.projection_digest,
                                    start=row.context_start,
                                    end=row.context_end,
                                )
                            ],
                            "unsupported",
                            str(error),
                        )
            covered = [
                (scope.examined[0], scope.examined[1])
                for scope in scopes
                if scope.view.ref.id == identity
            ]
            for selector in selectors:
                a, b = selector.get("start", 0), selector.get("end", len(view.text))
                for piece in view.pieces:
                    if piece["kind"] != "native_text" or selector.get(
                        "native_pointer", piece.get("item_ref")
                    ) != piece.get("item_ref"):
                        continue
                    left, right = max(a, piece["start"]), min(b, piece["end"])
                    if left < right and not any(
                        start <= left and right <= end for start, end in covered
                    ):
                        for family in CHARACTERIZATION_FAMILIES:
                            builder.record(
                                family,
                                [
                                    dict(
                                        projection=view.ref.projection_digest,
                                        native_pointer=piece["item_ref"],
                                        start=left,
                                        end=right,
                                    )
                                ],
                                "unsupported",
                                (
                                    "selected source has no admitted complete model context; "
                                    "no silent source truncation"
                                ),
                            )
        return tuple(scopes)

    def _d1(self, cfg, ctx, builder, scopes, families, dependencies, providers):
        assets = ctx.settings.model_cache / "pm2"
        try:
            if cfg.d1_runtime is None or cfg.d1_artifacts is None:
                raise Pm2WorkerRefused(
                    "d1 requires frozen runtime and artifact identities before task creation"
                )
            worker = pm2_client(
                providers,
                ctx,
                provider="d1",
                assets=assets,
                runtime=cfg.d1_runtime,
                artifacts=cfg.d1_artifacts,
                device=cfg.d1_device,
            )
            yield from worker.start()
            if (
                worker.startup.get("runtime_identity") != cfg.d1_runtime
                or worker.startup.get("assets") != cfg.d1_artifacts
            ):
                raise Pm2WorkerRefused(
                    "executed d1 runtime/artifacts differ from the frozen selection"
                )
            yield from self._d1_work(worker, ctx, builder, scopes, families, dependencies)
        except CapacityExceeded:
            raise
        except (Pm2WorkerError, Pm2WorkerRefused, OSError, ValueError) as error:
            ctx.check_active()
            for scope in scopes:
                for name in (*D1_SOURCE_FAMILIES, *CANDIDATE_FAMILIES):
                    builder.unavailable(families[name], scope, str(error), state="unavailable")

    def _d1_work(self, worker, ctx, builder, scopes, families, dependencies):
        jobs: list[tuple[QuestionFamily, ModelScope, FrozenCandidates | None]] = []
        for scope in scopes:
            jobs.extend((families[name], scope, None) for name in D1_SOURCE_FAMILIES)
            for name in CANDIDATE_FAMILIES:
                populations, complete = contextual_candidate_populations(
                    families[name], scope, dependencies
                )
                jobs.extend((families[name], scope, population) for population in populations)
                if not complete:
                    builder.record(
                        name,
                        [
                            dict(
                                projection=scope.view.ref.projection_digest,
                                start=scope.examined[0],
                                end=scope.examined[1],
                            )
                        ],
                        "partial",
                        (
                            "contextual hypothesis inventory is missing or incomplete; "
                            "no candidate absence inferred"
                        ),
                    )
                elif not populations:
                    builder.record(
                        name,
                        [
                            dict(
                                projection=scope.view.ref.projection_digest,
                                start=scope.examined[0],
                                end=scope.examined[1],
                            )
                        ],
                    )
        prior = [{} for _job in jobs]
        max_stage = max(
            question.stage
            for name in (*D1_SOURCE_FAMILIES, *CANDIDATE_FAMILIES)
            for question in families[name].questions
        )
        for stage in range(max_stage + 1):
            ready = []
            for index, (family, scope, candidates) in enumerate(jobs):
                selected = [question for question in family.questions if question.stage == stage]
                blocked = [
                    question.key
                    for question in selected
                    if any(
                        key not in prior[index] or prior[index][key]["state"] != "proposed"
                        for key in question.depends_on
                    )
                ]
                keys = [question.key for question in selected if question.key not in blocked]
                if blocked:
                    builder.unavailable(
                        family,
                        scope,
                        (
                            "Earlier located/selected question premises remain unresolved; "
                            "no graph relation invented."
                        ),
                        stage=stage,
                        state="dependency_unresolved",
                        keys=blocked,
                    )
                if keys:
                    ready.append(
                        (
                            index,
                            compile_question_stage(
                                family,
                                scope,
                                stage,
                                prior=prior[index],
                                candidates=candidates,
                                keys=keys,
                            ),
                        )
                    )
            for offset in range(0, len(ready), 16):
                batch = ready[offset : offset + 16]
                ctx.check_active()
                reply = yield from worker.infer(
                    dict(batch=[request.payload for _index, request in batch]),
                    check_active=ctx.check_active,
                )
                replies = reply.get("batch")
                if not isinstance(replies, list) or len(replies) != len(batch):
                    raise ValueError("d1 returned a different admitted request population")
                for (index, request), native in zip(batch, replies, strict=True):
                    try:
                        prior[index].update(builder.d1(request, native, runtime=worker.startup))
                    except (KeyError, TypeError, ValueError) as error:
                        builder.unavailable(
                            request.family,
                            request.scope,
                            "Invalid native answer: " + str(error),
                            stage=stage,
                            request_id=request.digest,
                            keys=tuple(request.payload["questions"]),
                            native=native,
                        )

    def _gliner(self, cfg, ctx, prepared, builder, scopes, families, providers):
        profile = cfg.gliner_profile
        if profile is None:
            for scope in scopes:
                for family in (GLINER_CUES, GLINER_FUNCTIONS):
                    builder.unavailable(
                        families[family],
                        scope,
                        "GLiNER requires an explicit frozen native profile",
                        state="unavailable",
                    )
            return
        validate_gliner_policy(profile.profile, providers.policy)
        inference = released_policy(prepared)["inference"]
        # Expose a bounded known population even with one provider-job slot.
        # Cue and classification packs remain distinct; only the parent reduces.
        from .gliner import GlinerInput, GlinerPack

        for offset in range(0, len(scopes), profile.profile.max_batch):
            jobs: list[dict[str, Any]] = []
            groups: dict[tuple, list[dict[str, Any]]] = {}
            for scope in scopes[offset : offset + profile.profile.max_batch]:
                for kind in (GLINER_CUES, GLINER_FUNCTIONS):
                    ctx.check_active()
                    family = families[kind]
                    selected_scope = scope
                    job: dict[str, Any] = dict(family=family, scope=scope, native=None, error=None)
                    jobs.append(job)
                    try:
                        if kind == GLINER_CUES:
                            pack, item = gliner_cue_request(prepared.release_id, family, scope)
                            threshold, overlap = profile.threshold, "nested"
                            job["request"] = None
                        else:
                            # Classification examines the exact focal slice, without
                            # borrowing the cue's wider context or labels.
                            selected_scope = prepare_model_scope(
                                scope.view,
                                scope.focal,
                                scope.focal,
                                max_chars=cfg.max_context_chars,
                            )
                            job["scope"] = selected_scope
                            request = classification_request(
                                prepared.release_id,
                                family,
                                family.questions[0].key,
                                selected_scope.mapping,
                                profile,
                                inference,
                                characterization_family=family.family,
                            )
                            pack = GlinerPack(**request["pack"])
                            item = GlinerInput(**request["item"])
                            threshold, overlap = request["threshold"], "flat"
                            job["request"] = request
                        job.update(pack=pack, item=item)
                        groups.setdefault((kind, pack, threshold, overlap), []).append(job)
                    except (GlinerWorkerError, OSError, ValueError) as error:
                        ctx.check_active()
                        job["error"] = error
            for (_kind, pack, threshold, overlap), members in groups.items():
                outcomes = yield from gliner_extract_members(
                    providers,
                    profile.profile,
                    pack,
                    tuple(job["item"] for job in members),
                    threshold=threshold,
                    overlap_policy=overlap,
                    check_active=ctx.check_active,
                )
                for job, outcome in zip(members, outcomes, strict=True):
                    job["error" if isinstance(outcome, Exception) else "native"] = outcome
            # Stable scope/family order, independent of inference completion/grouping.
            for job in jobs:
                family, selected_scope, native = job["family"], job["scope"], job["native"]
                try:
                    if job["error"] is not None:
                        raise job["error"]
                    if job["request"] is None:
                        project_gliner_cues(
                            builder,
                            family,
                            selected_scope,
                            job["pack"],
                            job["item"],
                            native,
                            profile.profile,
                            inference,
                            threshold=profile.threshold,
                        )
                    else:
                        request = job["request"]
                        product = classification_product(request, asdict(native), profile)
                        builder.classification(family, selected_scope, request, product, native)
                except CapacityExceeded:
                    raise
                except (GlinerWorkerError, OSError, ValueError) as error:
                    ctx.check_active()
                    builder.unavailable(
                        family,
                        selected_scope,
                        str(error),
                        native=None
                        if native is None
                        else dict(report=asdict(native), reason=str(error)),
                    )
