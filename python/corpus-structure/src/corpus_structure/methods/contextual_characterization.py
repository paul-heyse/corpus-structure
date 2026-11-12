"""Contextual native evidence and hypotheses through the shared task boundary."""

from __future__ import annotations

import time
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from corpus_structure.core._model.shapes import Cost
from corpus_structure.core.method import ReadyGroup, Resources, UnitResult, drive_prepared_work
from corpus_structure.core.vocab import MethodFamily, MethodTier, ObservationOutcome, TaskUnitType
from corpus_structure.semantic.contextual_characterization import (
    CONTEXT_FAMILIES,
    REVISION,
    ContextInput,
    ContextPart,
    ContextualLayer,
    digest,
)
from corpus_structure.semantic.cpu_execution import CapacityExceeded
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.product_reference import ProductReference

from .characterization_resources import fork_builder, merge_builder, pm2_client, provider_scope
from .native_evidence import _artifacts, native_run
from .native_evidence_layers import NativeEvidenceBuilder, has_selected_native_text
from .pm2_worker import Pm2WorkerError, Pm2WorkerRefused

MODEL = "maverick-mes-ontonotes+dipo-dmrst-ettin-gum-12.1.0"


def context_rule_digest():
    source = Path(__file__).resolve().parents[1] / "semantic/contextual_characterization.py"
    return sha256(
        canonical_bytes(
            {
                "contextual_semantics": sha256(source.read_bytes()).hexdigest(),
                "contextual_operation": sha256(Path(__file__).read_bytes()).hexdigest(),
            }
        )
    ).hexdigest()


class ContextualCharacterizationConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    characterization_base_document: dict[str, Any] | None = None
    characterization_source_scope: dict[str, Any] | None = None
    characterization_layers: tuple[dict[str, Any], ...] = ()
    characterization_profile: Literal["contextual_native"] = "contextual_native"
    focal: tuple[dict[str, Any], ...] = ()
    retained_native_layers: tuple[dict[str, Any], ...] = ()
    native_mode: Literal["infer", "retained"] = "infer"
    native_token_layer: dict[str, Any] | None = None
    native_runtime: dict[str, dict[str, Any]] = Field(default_factory=dict)
    native_artifacts: dict[str, dict[str, Any]] = Field(default_factory=dict)
    native_device: Literal["cuda"] = "cuda"
    language: str = "en"
    model: str = MODEL
    grammar: str = "none"
    context: str = REVISION
    context_rule_digest: str = Field(default_factory=context_rule_digest, pattern="^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def pins(self):
        selected = [ProductReference(**p) for p in self.characterization_layers]
        if len(set(selected)) != len(selected):
            raise ValueError("contextual characterization requires distinct exact input layers")
        retained = [ProductReference(**p) for p in self.retained_native_layers]
        if len(set(retained)) != len(retained) or set(retained) & set(selected):
            raise ValueError("retained native evidence must have distinct separately selected pins")
        if self.native_mode == "infer" and retained:
            raise ValueError("native inference cannot also select retained provider outputs")
        if (
            self.native_token_layer is not None
            and ProductReference(**self.native_token_layer) not in selected
        ):
            raise ValueError("native token layer must be an explicitly selected dependency")
        if self.model != MODEL or self.grammar != "none" or self.context != REVISION:
            raise ValueError("contextual native operation differs from its selected model/rule")
        if self.context_rule_digest != context_rule_digest():
            raise ValueError("contextual rule digest differs from current executable rules")
        return self

    def require_selection(self):
        if (
            self.characterization_base_document is None
            or self.characterization_source_scope is None
        ):
            raise ValueError("contextual characterization requires an exact base and source scope")
        return ProductReference(
            **self.characterization_base_document
        ), self.characterization_source_scope


def context_input(reader, scope, focal=()):
    parts = []
    views = {}
    for selector in scope["selectors"]:
        pins = [
            p for p in scope["source_views"] if p["projection_digest"] == selector["projection"]
        ]
        if len(pins) != 1:
            raise ValueError("context selector has ambiguous source projection")
        identity = pins[0]["source_view_id"]
        if identity not in views:
            views[identity] = reader.source_view(identity)
        view = views[identity]
        if view.ref.projection_digest != selector["projection"]:
            raise ValueError("context input differs from its frozen source projection")
        if "start" in selector:
            selected = [(selector["start"], selector["end"])]
        elif selector.get("native_pointer"):
            selected = [
                (p["start"], p["end"])
                for p in view.pieces
                if p.get("item_ref") == selector["native_pointer"]
            ]
        elif "page" not in selector:
            selected = [(0, len(view.text))] if view.text else []
        else:
            raise ValueError("page-only context requires exact source character correspondence")
        for start, end in selected:
            if start == end or not view.text[start:end].strip():
                continue
            if any(
                part.view.ref.id == identity and start < part.end and part.start < end
                for part in parts
            ):
                raise ValueError("context selection repeats or overlaps source text")
            parts.append(ContextPart(view, start, end))
    return ContextInput.build(parts, focal or [p.selector() for p in parts])


def canonical_tokens(builder: ContextualLayer, layers, selected=None):
    pins = (
        [ProductReference(**selected)]
        if selected
        else [
            pin
            for pin, layer in layers.items()
            if any(
                a.get("native_token", {}).get("native_run") == "spacy"
                for a in layer.payload["annotations"]
            )
        ]
    )
    if len(pins) != 1 or pins[0] not in layers:
        raise ValueError("context requires one explicitly selected retained spaCy token population")
    pin = pins[0]
    body = layers[pin].payload
    occurrences = {o["local_id"]: o for o in body["occurrences"]}
    rows = []
    for part_index, part in enumerate(builder.context.parts):
        selected_rows = []
        for annotation in body["annotations"]:
            token = annotation.get("native_token")
            if token is None or token["native_run"] != "spacy" or not token["text"].strip():
                continue
            extents = [e for oid in annotation["occurrences"] for e in occurrences[oid]["extents"]]
            if not all(
                e["projection"] == part.view.ref.projection_digest
                and part.start <= e.get("start", part.start) < e.get("end", part.end) <= part.end
                for e in extents
            ):
                continue
            if "sentence" not in token:
                raise ValueError("context token lacks complete retained sentence ownership")
            if "".join(e["text"] for e in extents) != token["text"]:
                raise ValueError("context token differs from its exact source members")
            for oid in annotation["occurrences"]:
                builder.occurrences.setdefault(oid, occurrences[oid])
            selected_rows.append(
                (
                    extents[0]["start"],
                    dict(
                        text=token["text"],
                        sentence=(part_index, pin, token["sentence"]),
                        occurrences=annotation["occurrences"],
                        source=annotation["local_id"],
                    ),
                )
            )
        rows.extend(row for _, row in sorted(selected_rows, key=lambda item: item[0]))
    if not rows:
        raise ValueError("selected examined context has no retained canonical sentence tokens")
    return rows


def reuse_native(builder: ContextualLayer, layers):
    """Consume original pinned observations, preserving their producer provenance."""
    seen = set()
    for pin, report in layers.items():
        body = report.payload
        annotations = {a["local_id"]: a for a in body["annotations"]}
        raw_families = {"maverick.mentions", "maverick.clusters", "dipo.edus", "dipo.rst"}
        raw = {}
        for key, annotation in annotations.items():
            if annotation["family"] not in raw_families:
                continue
            try:
                raw[key] = builder.proxy(pin, key, family=annotation["family"])
            except ValueError:
                continue
        # Retain native populations as attributed references, including complete
        # group membership. A reference does not claim a new provider invocation.
        for membership in body["memberships"]:
            if membership["group"] not in raw or membership["member"] not in raw:
                continue
            occurrences = {o["local_id"]: o for o in body["occurrences"]}
            for identity in membership["occurrences"]:
                builder.occurrences.setdefault(identity, occurrences[identity])
            builder.memberships.append(
                dict(
                    membership,
                    local_id="retained-membership:"
                    + digest([pin.values(), membership["local_id"]]),
                    group=raw[membership["group"]],
                    member=raw[membership["member"]],
                    scope=raw.get(membership.get("scope"), raw[membership["group"]]),
                    external_premises=[dict(layer=pin.values(), local_id=membership["local_id"])],
                    required_choices=[],
                    required_external_choices=builder.required_choices(pin, membership),
                )
            )
        mentions = {}
        for key, annotation in annotations.items():
            if annotation["kind"] not in {"native.mention", "native.unmapped_mention"}:
                continue
            try:
                proxy = builder.proxy(pin, key, family="context.reference")
            except ValueError:
                continue
            mentions[key] = proxy
            builder._mention_metadata[proxy] = annotation["native_mention"]
        for annotation in annotations.values():
            if annotation["kind"] == "native.coreference_cluster":
                members = [
                    m["member"]
                    for m in body["memberships"]
                    if m["group"] == annotation["local_id"] and m["role"] == "native_member"
                ]
                if all(member in mentions for member in members):
                    group = builder.proxy(pin, annotation["local_id"], family="context.reference")
                    keys = [mentions[member] for member in members]
                    index = {a["local_id"]: a for a in builder.annotations}
                    for order, member in enumerate(keys):
                        builder.membership(
                            group,
                            member,
                            "candidate_member",
                            order,
                            "context.reference",
                            index[member]["occurrences"],
                        )
                    builder._native_clusters.append((group, keys))
            elif (
                annotation["kind"] == "native.rst_node"
                and "condition" in annotation["native_label"].casefold()
            ):
                children = [
                    m
                    for m in body["memberships"]
                    if m["group"] == annotation["local_id"]
                    and m["role"] in {"nucleus", "satellite"}
                ]
                if len(children) != 2:
                    raise ValueError("retained RST evidence omits its directed native children")
                try:
                    native = builder.proxy(pin, annotation["local_id"], family="context.host")
                    proxies = [
                        (child["role"], builder.proxy(pin, child["member"], family="context.host"))
                        for child in children
                    ]
                except ValueError:
                    continue
                index = {a["local_id"]: a for a in builder.annotations}
                if proxies[0][0] == proxies[1][0] == "nucleus":
                    builder._rst_hosts.extend(
                        (
                            (
                                index[proxies[0][1]]["occurrences"],
                                index[proxies[1][1]]["occurrences"],
                                native,
                            ),
                            (
                                index[proxies[1][1]]["occurrences"],
                                index[proxies[0][1]]["occurrences"],
                                native,
                            ),
                        )
                    )
                else:
                    satellite = next(key for role, key in proxies if role == "satellite")
                    nucleus = next(key for role, key in proxies if role == "nucleus")
                    builder._rst_hosts.append(
                        (index[satellite]["occurrences"], index[nucleus]["occurrences"], native)
                    )
        for coverage in body["coverage"]:
            family = coverage["family"]
            if family not in {"maverick.mentions", "maverick.clusters", "dipo.edus", "dipo.rst"}:
                continue
            selectors = [p.selector() for p in builder.context.parts]
            examined = coverage.get("examined", [])
            if not all(
                any(
                    s["projection"] == old["projection"]
                    and old.get("start", 0) <= s["start"]
                    and s["end"] <= old.get("end", s["end"])
                    for old in examined
                )
                for s in selectors
            ):
                continue
            seen.add(family)
            builder.record(
                family,
                selectors,
                "complete" if coverage["outcome"] in {"complete", "empty"} else "partial",
                None
                if coverage["outcome"] in {"complete", "empty"}
                else "retained native family has incomplete coverage",
            )
    for family in {"maverick.mentions", "maverick.clusters", "dipo.edus", "dipo.rst"} - seen:
        builder.record(
            family,
            [p.selector() for p in builder.context.parts],
            "failed",
            "no compatible retained native coverage; reads do not trigger inference",
        )


class ContextualCharacterizationMethod:
    name = "text.contextual_characterization"
    version = "1"
    family = MethodFamily.EXTRACT
    unit_type = TaskUnitType.DOCUMENT
    tier = MethodTier.DETERMINISTIC
    confidence_source = None
    Config = ContextualCharacterizationConfig
    resources = Resources(worker="cpu", batch_size=1, max_concurrency=1)

    def select(self, run, cfg):
        from .native_evidence import select_document_scope

        return select_document_scope(run, *cfg.require_selection())

    def input_digest(self, unit, cfg):
        from corpus_structure.core.method import Digest

        cfg.require_selection()
        return Digest(
            canonical_bytes(
                dict(
                    method=self.name,
                    version=self.version,
                    release_id=unit.run.reader.prepared.release_id,
                    configuration=cfg.model_dump(mode="json"),
                    document_id=unit.ref.unit_id,
                )
            )
        )

    def run(self, units, cfg, ctx):
        return drive_prepared_work(self.plan(units, cfg, ctx), ctx.check_active)

    def plan(self, units, cfg, ctx):
        with provider_scope(units, policy=ctx.settings.execution_policy) as (_cpu, providers):
            from .characterization_resources import selections_for_characterization

            if providers is not None:
                providers.declare_native(
                    selections_for_characterization(
                        {"text.contextual_characterization": cfg.model_dump(mode="json")},
                        ctx.settings,
                    ),
                    ctx.settings.nemotron_endpoint,
                )
            if cfg.context_rule_digest != context_rule_digest():
                raise ValueError("contextual rule digest changed after configuration freeze")
            base, scope = cfg.require_selection()
            results = []
            for unit in units:
                started = time.monotonic()
                ctx.check_active()
                if unit.ref not in self.select(unit.run, cfg):
                    raise ValueError("contextual task differs from selected source document")
                reader = unit.run.reader
                has_text = any(
                    has_selected_native_text(reader.source_view(identity), scope["selectors"])
                    for identity in scope["source_view_ids"]
                )
                operation = ctx.characterization_operation(unit.ref)
                builder = (
                    ContextualLayer(
                        base.values(), scope, operation, context_input(reader, scope, cfg.focal)
                    )
                    if has_text
                    else NativeEvidenceBuilder(
                        base.values(), scope, operation, profile=REVISION, families=CONTEXT_FAMILIES
                    )
                )
                pins = [ProductReference(**p) for p in cfg.characterization_layers]
                retained = [ProductReference(**p) for p in cfg.retained_native_layers]
                required = list(dict.fromkeys([*pins, *retained]))
                layers, pending = {}, required
                while pending:
                    read = reader.characterization_layers(pending)
                    if set(read) != set(pending):
                        raise ValueError("context requires exact retained dependency closure")
                    layers.update(read)
                    pending = list(
                        dict.fromkeys(
                            ProductReference(**value)
                            for report in read.values()
                            for value in report.payload["dependencies"]
                            if ProductReference(**value) not in layers
                        )
                    )
                if any(layer.base_document != base for layer in layers.values()):
                    raise ValueError("context dependency belongs to another source document")
                if isinstance(builder, ContextualLayer):
                    builder.depend(layers, semantic_pins=pins)
                builder.operation["required_layers"] = [p.values() for p in required]
                releases = {reader.prepared.release_id: reader.prepared}
                for layer in layers.values():
                    release = layer.payload["release_id"]
                    if release not in releases:
                        releases[release] = reader.characterization_release(release)
                if isinstance(builder, ContextualLayer):
                    builder.structural()
                    if cfg.native_mode == "retained":
                        reuse_native(builder, {pin: layers[pin] for pin in (retained or pins)})
                    else:
                        yield from self._native(cfg, ctx, builder, layers, providers)
                    builder.hypotheses()
                else:
                    for family in CONTEXT_FAMILIES:
                        builder.record(family, scope["selectors"], "empty")
                report = builder.finish(reader.prepared, dependencies=layers, releases=releases)
                results.append(
                    UnitResult(
                        ref=unit.ref,
                        outcome=ObservationOutcome.PRODUCED,
                        characterization_layer=report,
                        cost=Cost(
                            wall_ms=round((time.monotonic() - started) * 1000), model=cfg.model
                        ),
                    )
                )
            return tuple(results)

    def _native(self, cfg, ctx, builder, layers, providers):
        selections = (
            ("maverick", ("maverick.mentions", "maverick.clusters")),
            ("dipo", ("dipo.edus", "dipo.rst")),
        )
        branches = [fork_builder(builder) for _ in selections]
        yield ReadyGroup(
            tuple(
                self._native_provider(cfg, ctx, branch[0], layers, providers, provider, families)
                for branch, (provider, families) in zip(branches, selections, strict=True)
            )
        )
        for branch in branches:
            merge_builder(builder, branch)

    def _native_provider(self, cfg, ctx, builder, layers, providers, provider, families):
        assets = ctx.settings.model_cache / "pm2"
        ctx.check_active()
        startup = None
        selection = None
        checkpoint = (
            len(builder.annotations),
            len(builder.memberships),
            len(builder.roles),
            len(builder._native_clusters),
            dict(builder._mention_metadata),
            len(builder._rst_hosts),
        )
        try:
            if cfg.language.partition("-")[0].lower() != "en":
                raise Pm2WorkerRefused("selected contextual native profiles support English")
            runtime, artifacts = (
                cfg.native_runtime.get(provider),
                cfg.native_artifacts.get(provider),
            )
            if runtime is None or artifacts is None:
                raise Pm2WorkerRefused(
                    "native context requires frozen runtime/artifact selection before task creation"
                )
            tokens = (
                canonical_tokens(builder, layers, cfg.native_token_layer)
                if provider == "maverick"
                else None
            )
            request = (
                dict(sentences=builder.sentences(tokens))
                if tokens is not None
                else dict(text=builder.context.text, mode="learned")
            )
            worker = pm2_client(
                providers,
                ctx,
                provider=provider,
                assets=assets,
                runtime=runtime,
                artifacts=artifacts,
                device=cfg.native_device,
            )
            selection = worker.selection_factory()
            yield from worker.start()
            startup = worker.startup
            if startup.get("runtime_identity") != runtime or startup.get("assets") != artifacts:
                raise Pm2WorkerRefused("executed contextual provider differs from frozen selection")
            reply = yield from worker.infer(request, check_active=ctx.check_active)
            if reply.get("outcome") not in {"succeeded", "empty"}:
                for family in families:
                    builder.record(
                        family,
                        [p.selector() for p in builder.context.parts],
                        "unsupported",
                        f"native {provider} scope admission: "
                        f"{reply.get('reason', reply.get('outcome', 'unknown'))}; "
                        "crossing remains unexamined",
                    )
            elif provider == "maverick":
                builder.maverick(tokens, request, reply)
            elif reply.get("outcome") == "empty":
                for family in families:
                    builder.record(family, [p.selector() for p in builder.context.parts])
            else:
                builder.dipo(request, reply)
        except CapacityExceeded:
            raise
        except (
            Pm2WorkerError,
            Pm2WorkerRefused,
            OSError,
            ValueError,
            KeyError,
            TypeError,
        ) as error:
            ctx.check_active()
            del builder.annotations[checkpoint[0] :]
            del builder.memberships[checkpoint[1] :]
            del builder.roles[checkpoint[2] :]
            del builder._native_clusters[checkpoint[3] :]
            builder._mention_metadata = checkpoint[4]
            del builder._rst_hosts[checkpoint[5] :]
            for family in families:
                builder.record(
                    family,
                    [p.selector() for p in builder.context.parts],
                    "failed",
                    f"native {provider} context attempt failed: {error}",
                )
        if startup is not None:
            config = startup["native_configuration"]
            row = native_run(
                provider,
                REVISION,
                config,
                model=startup["encoder"],
                version="selected-staged-checkpoint",
                runtime_version=startup["packages"][
                    "maverick-coref" if provider == "maverick" else "dipo"
                ],
                layout=[p.selector() for p in builder.context.parts],
                text=builder.context.text,
                components=[dict(name=startup["head"], factory=provider)],
                packages=[
                    dict(name=name, version=value) for name, value in startup["packages"].items()
                ],
                artifacts=_artifacts(startup),
                limits=[dict(name=name, value=value) for name, value in startup["bounds"].items()],
                diagnostics=[
                    "native context observations do not establish complete reference "
                    "detection or logical discourse meaning"
                ],
            )
            from corpus_structure.semantic.observations import source_value

            assert selection is not None  # A startup observation requires its admitted selection.
            row["execution_profile"] = source_value(selection.native.wire)
            row["startup_observation"] = source_value(startup)
            row["configuration_codec"] = provider + "-config-json-v1"
            builder.native_runs.append(row)
