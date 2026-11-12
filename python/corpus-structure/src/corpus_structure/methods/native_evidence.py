"""Shared native linguistic producers under ordinary task and publication custody."""

from __future__ import annotations

import time
from collections.abc import Generator, Iterable, Mapping, Sequence
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from corpus_structure.core._model.shapes import Cost
from corpus_structure.core.method import (
    Digest,
    Resources,
    UnitRef,
    UnitResult,
    drive_prepared_work,
)
from corpus_structure.core.vocab import MethodFamily, MethodTier, ObservationOutcome, TaskUnitType
from corpus_structure.ingest.annotations import AnnotationProfile
from corpus_structure.ingest.sentences import SentenceConfig, pipeline
from corpus_structure.semantic.cpu_execution import CapacityExceeded
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.product_reference import ProductReference

from .characterization_resources import pm2_client, provider_scope
from .native_evidence_layers import (
    HANLP_FAMILIES,
    SPACY_FAMILIES,
    NativeEvidenceBuilder,
    digest,
    has_selected_native_text,
    source_selector,
)
from .pm2_worker import Pm2WorkerError, Pm2WorkerRefused
from .source_preparation import annotation_inputs

METHOD = "text.native_evidence"
MODEL = "spacy-en_core_web_sm-3.8.0+hanlp-modernbert-large-20250107"


class NativeEvidenceConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    characterization_base_document: dict[str, Any] | None = None
    characterization_source_scope: dict[str, Any] | None = None
    characterization_layers: tuple[dict[str, Any], ...] = ()
    characterization_profile: Literal["full_native", "spacy_only", "boundary_only"] = "full_native"
    language: str = Field(default="en", min_length=1)
    sentences: SentenceConfig = Field(default_factory=lambda: SentenceConfig(exclude=("ner",)))
    model: str = MODEL
    grammar: str = "none"
    context: str = "source-blocks-and-canonical-sentences-1"
    max_annotation_chars: int = Field(default=32768, ge=1)
    hanlp_device: Literal["cuda"] = "cuda"
    spacy_native_profile: dict[str, Any] | None = None
    # Frozen custody selected before task creation; result-neutral paths use MethodSettings.
    hanlp_runtime: dict[str, Any] | None = None
    hanlp_artifacts: dict[str, Any] | None = None

    @model_validator(mode="after")
    def selection(self):
        if self.characterization_base_document is not None:
            ProductReference(**self.characterization_base_document)
        if len({ProductReference(**p) for p in self.characterization_layers}) != len(
            self.characterization_layers
        ):
            raise ValueError("native evidence requires distinct selected layer pins")
        if self.model != MODEL or self.grammar != "none":
            raise ValueError("selected native evidence model/grammar differs from this producer")
        return self

    def require_selection(self):
        if (
            self.characterization_base_document is None
            or self.characterization_source_scope is None
        ):
            raise ValueError("native evidence requires an exact base document and source scope")
        return ProductReference(
            **self.characterization_base_document
        ), self.characterization_source_scope

    @property
    def families(self):
        if self.characterization_profile == "boundary_only":
            return SPACY_FAMILIES[:2]
        return SPACY_FAMILIES + (
            HANLP_FAMILIES if self.characterization_profile == "full_native" else ()
        )


def native_run(
    provider: str,
    profile: str,
    configuration: str,
    *,
    model: str,
    version: str,
    runtime_version: str,
    layout: Any,
    text: Any,
    components=(),
    packages=(),
    artifacts=(),
    limits=(),
    diagnostics=(),
) -> dict[str, Any]:
    return dict(
        local_id=provider,
        provider=provider,
        profile=profile,
        model=model,
        model_version=version,
        runtime_version=runtime_version,
        configuration=configuration,
        configuration_codec="spacy-config-v1" if provider == "spacy" else "hanlp-config-json-v1",
        configuration_digest=sha256(configuration.encode()).hexdigest(),
        layout_recipe="canonical-token-layout-1",
        layout_digest=digest(layout),
        text_digest=digest(text),
        components=list(components),
        availability=[],
        runtime_packages=list(packages),
        artifacts=list(artifacts),
        limits=list(limits),
        diagnostics=list(diagnostics),
    )


def _availability(builder: NativeEvidenceBuilder, provider: str) -> list[dict[str, Any]]:
    rows = []
    for family in builder.families:
        if not family.startswith(provider + "."):
            continue
        covered = builder.covered[family]
        statuses = {status for _, status, _ in covered}
        status = (
            "absent"
            if not covered or statuses <= {"failed", "unsupported"}
            else "complete"
            if statuses <= {"complete", "empty"}
            else "partial"
        )
        row = dict(family=family, attribute=family.partition(".")[2], status=status)
        reasons = list(dict.fromkeys(reason for _, _, reason in covered if reason))
        if reasons:
            row["reason"] = "; ".join(reasons)
        rows.append(row)
    return rows


def _native_heads(document: Mapping[str, Any], index: int, population: int) -> dict[str, Any]:
    heads = {}
    for name, family in (
        ("lem", "lemma"),
        ("pos", "pos"),
        ("dep", "dependency"),
        ("con", "constituency"),
        ("srl", "srl"),
    ):
        columns = [v for k, v in document.items() if k.split("/")[0] == name]
        if len(columns) == 1 and isinstance(columns[0], list) and len(columns[0]) == population:
            heads[family] = columns[0][index]
    return heads


def _artifacts(startup: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for group, manifest in startup.get("assets", {}).items():
        rows.extend(
            dict(name=f"{group}/{name}", sha256=pin["sha256"], size=pin["size"])
            for name, pin in manifest["files"].items()
        )
    runtime = startup.get("runtime_identity", {})
    rows.extend(
        dict(name="runtime/" + name, sha256=value)
        for name, value in runtime.items()
        if name.endswith("_sha256")
    )
    return rows


def _batch_sentences(
    worker: Any,
    rows: Sequence[tuple[Any, Any, list[dict[str, Any]], int]],
    builder: NativeEvidenceBuilder,
    check_active,
) -> Generator:
    """Use actual native subword lengths; resize only a batch, never a sentence."""
    ready = []
    max_sentences = int(worker.startup.get("max_sentences", 8))
    max_chars = int(worker.startup.get("max_batch_chars", 32768))
    for offset in range(0, len(rows), max_sentences):
        population = rows[offset : offset + max_sentences]
        check_active()
        request = {
            "sentences": [[token["text"] for token in row[2]] for row in population],
            "prepare_bulk": True,
        }
        prepared = yield from worker.infer(request, check_active=check_active)
        members = prepared.get("members")
        if (
            prepared.get("outcome") != "prepared_batch"
            or not isinstance(members, list)
            or len(members) != len(population)
        ):
            raise Pm2WorkerError("HanLP bulk preparation changed the admitted population")
        for ordinal, (row, member) in enumerate(zip(population, members, strict=True)):
            if not isinstance(member, dict) or member.get("ordinal") != ordinal:
                raise Pm2WorkerError("HanLP preparation member ordinal differs")
            view, _product, words, _number = row
            if member.get("outcome") != "prepared":
                reason = (
                    f"native HanLP admission: {member.get('reason', 'unknown')} "
                    f"(limit={member.get('limit')})"
                )
                selector = source_selector(view, words[0]["source"].start, words[-1]["source"].end)
                for family in HANLP_FAMILIES:
                    builder.record(family, [selector], "unsupported", reason)
                continue
            length = member.get("row_tokens")
            if type(length) is not int or length < 1:
                raise Pm2WorkerError("HanLP preparation omitted actual native subword length")
            ready.append((row, length))
    batch = []
    lengths = []
    chars = 0

    def flush():
        if not batch:
            return
        check_active()
        sentences = [[t["text"] for t in entry[2]] for entry in batch]
        reply = yield from worker.infer(
            {"sentences": sentences, "admitted_row_tokens": list(lengths)},
            check_active=check_active,
        )
        if reply.get("outcome") != "succeeded":
            reason = (
                f"native all-head invocation {reply.get('outcome', 'failed')}: "
                f"{reply.get('reason', 'no result')}"
            )
            for view, _, words, _ in batch:
                selector = source_selector(view, words[0]["source"].start, words[-1]["source"].end)
                for family in HANLP_FAMILIES:
                    builder.record(family, [selector], "failed", reason)
            return
        native, preparation = reply.get("native"), reply.get("preparation")
        if (
            not isinstance(native, dict)
            or native.get("tok") != sentences
            or not isinstance(preparation, list)
            or len(preparation) != len(batch)
        ):
            raise Pm2WorkerError("HanLP invocation changed native token/preparation population")
        for index, (view, product, words, number) in enumerate(batch):
            builder.hanlp_sentence(
                view,
                product,
                words,
                number,
                _native_heads(native, index, len(batch)),
                preparation[index],
                "hanlp",
            )

    for entry, length in ready:
        size = sum(len(t["text"]) for t in entry[2])
        padded = (len(batch) + 1) * max([*lengths, length])
        if batch and (
            len(batch) == max_sentences
            or chars + size > max_chars
            or padded > int(worker.startup.get("max_padded_subwords", 2048))
        ):
            yield from flush()
            batch, lengths, chars = [], [], 0
        batch.append(entry)
        lengths.append(length)
        chars += size
    yield from flush()


def select_document_scope(run, base, scope) -> Iterable[UnitRef]:
    refs = [run.reader.source_view_ref(identity) for identity in scope["source_view_ids"]]
    if not refs or any(ref is None or ref.native_product != base for ref in refs):
        raise ValueError("native evidence source is outside the run's selected base document")
    documents = {ref.document_id for ref in refs if ref is not None}
    if len(documents) != 1:
        raise ValueError("native evidence requires one document")
    return (UnitRef(TaskUnitType.DOCUMENT, next(iter(documents))),)


class NativeEvidenceMethod:
    name = METHOD
    version = "2"
    family = MethodFamily.EXTRACT
    unit_type = TaskUnitType.DOCUMENT
    tier = MethodTier.DETERMINISTIC
    confidence_source = None
    Config = NativeEvidenceConfig
    resources = Resources(worker="cpu", batch_size=1, max_concurrency=1)

    def select(self, run, cfg: NativeEvidenceConfig) -> Iterable[UnitRef]:
        return select_document_scope(run, *cfg.require_selection())

    def input_digest(self, unit, cfg: NativeEvidenceConfig) -> Digest:
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

    def run(self, units, cfg: NativeEvidenceConfig, ctx):
        return drive_prepared_work(self.plan(units, cfg, ctx), ctx.check_active)

    def plan(self, units, cfg: NativeEvidenceConfig, ctx):
        with provider_scope(units, policy=ctx.settings.execution_policy) as (cpu, providers):
            from .characterization_resources import selections_for_characterization
            if providers is not None:
                providers.declare_native(selections_for_characterization({'text.native_evidence': cfg.model_dump(mode="json")}, ctx.settings), ctx.settings.nemotron_endpoint)
            base, scope = cfg.require_selection()
            results = []
            for unit in units:
                started = time.monotonic()
                ctx.check_active()
                if unit.ref not in self.select(unit.run, cfg):
                    raise ValueError("native evidence task unit differs from selected document")
                reader = unit.run.reader
                operation = ctx.characterization_operation(unit.ref)
                builder = NativeEvidenceBuilder(
                    base.values(),
                    scope,
                    operation,
                    profile=cfg.characterization_profile,
                    families=cfg.families,
                )
                pins = tuple(ProductReference(**p) for p in cfg.characterization_layers)
                dependencies = reader.characterization_layers(pins) if pins else {}
                builder.operation["required_layers"] = [p.values() for p in pins]
                releases = {reader.prepared.release_id: reader.prepared}
                for report in dependencies.values():
                    release = report.payload["release_id"]
                    if release not in releases:
                        releases[release] = reader.characterization_release(release)
                if not any(
                    has_selected_native_text(reader.source_view(identity), scope["selectors"])
                    for identity in scope["source_view_ids"]
                ):
                    for family in cfg.families:
                        builder.record(family, scope["selectors"], "empty")
                elif cfg.language.partition("-")[0].lower() != "en":
                    for family in cfg.families:
                        builder.record(
                            family,
                            scope["selectors"],
                            "unsupported",
                            "selected native linguistic profile supports English",
                        )
                else:
                    yield from self._produce(reader, cfg, ctx, builder, cpu, providers)
                report = builder.finish(
                    reader.prepared, dependencies=dependencies, releases=releases
                )
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

    def _produce(self, reader, cfg, ctx, builder, cpu, providers):
        sentence_cfg = cfg.sentences
        if cfg.characterization_profile == "boundary_only":
            sentence_cfg = cfg.sentences.model_copy(
                update={"exclude": ("ner", "tagger", "attribute_ruler", "lemmatizer")}
            )
        selected_spacy = next((s for s in providers.native_group._selections.values() if s.provider == "spacy" and s.native.parameters == sentence_cfg.model_dump(mode="json")), None)
        profile = AnnotationProfile(sentence_cfg, execution_profile=None if selected_spacy is None else selected_spacy.native.fingerprint)
        layouts, text_pins, pending, products = [], [], [], []
        nlp = None
        try:
            nlp = pipeline(profile.configuration)
            for identity in builder.scope["source_view_ids"]:
                ctx.check_active()
                view = reader.source_view(identity)
                selectors = [
                    s
                    for s in builder.scope["selectors"]
                    if s["projection"] == view.ref.projection_digest
                ]
                if not has_selected_native_text(view, selectors):
                    for family in cfg.families:
                        builder.record(family, selectors, "empty")
                    continue
                pointers = tuple(
                    dict.fromkeys(s["native_pointer"] for s in selectors if s.get("native_pointer"))
                )
                inputs = annotation_inputs(
                    view,
                    profile=profile,
                    max_annotation_chars=cfg.max_annotation_chars,
                    check_active=ctx.check_active,
                    region_pointers=pointers or None,
                )
                inputs = tuple(
                    row
                    for row in inputs
                    if any(
                        s.get("start", 0) <= row.layout.block_start
                        and row.layout.block_end <= s.get("end", len(view.text))
                        for s in selectors
                    )
                )
                from corpus_structure.semantic.native_annotations import annotation_work

                if not inputs:
                    continue
                batches = yield tuple(
                    annotation_work(providers, (item,), profile, ctx.check_active, native_profile=cfg.spacy_native_profile, require_complete=False)
                    for item in inputs
                )
                for product in (product for batch in batches for product in batch.require_available()):
                    ctx.check_active()
                    layouts.append(dict(view=view.ref.id, layout=product.layout_digest))
                    text_pins.append(dict(view=view.ref.id, text=product.text_digest))
                    _block, tokens = builder.spacy(view, product, "spacy")
                    products.append(product)
                    block_pending = []
                    for number in range(len(product.sentences)):
                        words = [
                            t
                            for t in tokens
                            if t["source"].sentence == number and t["text"].strip()
                        ]
                        if words:
                            block_pending.append((view, product, words, number))
                    pending.extend(block_pending)
                    if cfg.characterization_profile == "full_native" and not block_pending:
                        for family in HANLP_FAMILIES:
                            builder.record(
                                family,
                                [source_selector(view, product.block_start, product.block_end)],
                                "failed",
                                "native source block has no complete canonical sentence population",
                            )
                # Every native text piece requested remains in the denominator, even
                # when a whole source block is too large or the selector cuts it.
                for piece in view.pieces:
                    if piece["kind"] != "native_text" or not any(
                        (not s.get("native_pointer") or s["native_pointer"] == piece["item_ref"])
                        and s.get("start", 0) < piece["end"]
                        and s.get("end", len(view.text)) > piece["start"]
                        for s in selectors
                    ):
                        continue
                    if not any(
                        p.block_start <= piece["start"]
                        and piece["end"] <= p.block_end
                        and p.source.source_view_id == view.ref.id
                        for p in products
                    ):
                        selected_piece = source_selector(
                            view, piece["start"], piece["end"], piece["item_ref"]
                        )
                        for family in cfg.families:
                            builder.record(
                                family,
                                [selected_piece],
                                "unsupported",
                                "source block outside annotation size bound "
                                "or selected scope; no silent cut",
                            )
            # Boundary-only output must expose only its declared weaker families.
            if cfg.characterization_profile == "boundary_only":
                builder.annotations[:] = [
                    a for a in builder.annotations if a["family"] in builder.families
                ]
                builder.memberships[:] = [
                    m for m in builder.memberships if m["family"] in builder.families
                ]
                builder.roles[:] = []
        except CapacityExceeded:
            raise
        except (OSError, ValueError, RuntimeError) as error:
            ctx.check_active()
            # Keep detached earlier blocks; a producer failure cannot erase siblings.
            for family in SPACY_FAMILIES:
                if family in builder.covered:
                    builder.record(
                        family,
                        builder.scope["selectors"],
                        "failed",
                        f"spaCy preparation/inference failed: {error}",
                    )
        if nlp is not None:
            config = nlp.config.to_str()
            row = native_run(
                "spacy",
                cfg.characterization_profile,
                config,
                model=cfg.sentences.model,
                version=cfg.sentences.model_version,
                runtime_version=cfg.sentences.spacy_version,
                layout=layouts,
                text=text_pins,
                components=[
                    dict(name=name, factory=nlp.get_pipe_meta(name).factory)
                    for name in nlp.pipe_names
                ],
                packages=[
                    dict(name="spacy", version=cfg.sentences.spacy_version),
                    dict(name=cfg.sentences.model, version=cfg.sentences.model_version),
                ],
            )
            from corpus_structure.semantic.observations import source_value
            if selected_spacy is not None:
                row["execution_profile"] = source_value(selected_spacy.native.wire)
                host = providers.native_group._hosts.get(selected_spacy.native.host)
                observed = None if host is None else host.startup.get(selected_spacy.native.fingerprint)
                if observed is not None:
                    row["startup_observation"] = source_value(observed)
            row["availability"] = _availability(builder, "spacy")
            builder.native_runs.append(row)
        if cfg.characterization_profile != "full_native":
            return
        if not pending:
            for family in HANLP_FAMILIES:
                builder.record(
                    family,
                    builder.scope["selectors"],
                    "failed",
                    "no complete canonical sentence population available for HanLP",
                )
            return
        yield from self._hanlp(cfg, ctx, builder, pending, layouts, text_pins, providers)

    def _hanlp(self, cfg, ctx, builder, pending, layouts, text_pins, providers):
        assets = ctx.settings.model_cache / "pm2"
        startup = None
        try:
            if cfg.hanlp_runtime is None or cfg.hanlp_artifacts is None:
                raise Pm2WorkerRefused(
                    "full_native requires frozen HanLP runtime and artifact identities "
                    "selected before task creation"
                )
            worker = pm2_client(
                providers,
                ctx,
                provider="hanlp",
                assets=assets,
                runtime=cfg.hanlp_runtime,
                artifacts=cfg.hanlp_artifacts,
                device=cfg.hanlp_device,
            )
            yield from worker.start()
            startup = worker.startup
            if (
                startup.get("runtime_identity") != cfg.hanlp_runtime
                or startup.get("assets") != cfg.hanlp_artifacts
            ):
                raise Pm2WorkerRefused(
                    "executed HanLP runtime/artifacts differ from frozen selection"
                )
            yield from _batch_sentences(worker, pending, builder, ctx.check_active)
        except CapacityExceeded:
            raise
        except (Pm2WorkerError, Pm2WorkerRefused, OSError, ValueError) as error:
            ctx.check_active()
            for family in HANLP_FAMILIES:
                covered = {canonical_bytes(selector) for selector, _, _ in builder.covered[family]}
                missing = [
                    source_selector(view, words[0]["source"].start, words[-1]["source"].end)
                    for view, _, words, _ in pending
                    if canonical_bytes(
                        source_selector(view, words[0]["source"].start, words[-1]["source"].end)
                    )
                    not in covered
                ]
                builder.record(family, missing, "failed", f"HanLP native attempt failed: {error}")
        if startup is not None:
            config = startup["native_configuration"]
            row = native_run(
                "hanlp",
                cfg.characterization_profile,
                config,
                model="EN_TOK_LEM_POS_NER_SRL_UDEP_SDP_CON_MODERNBERT_LARGE",
                version="20250107_181612",
                runtime_version=startup["packages"]["hanlp"],
                layout=layouts,
                text=text_pins,
                components=[
                    dict(name=name, factory="hanlp-mtl-native-head") for name in startup["heads"]
                ],
                packages=[
                    dict(name=name, version=value) for name, value in startup["packages"].items()
                ],
                artifacts=_artifacts(startup),
                limits=[
                    dict(name=name, value=value)
                    for name, value in startup.items()
                    if (name.startswith("max_") or name == "srl_max_arg_width")
                    and type(value) is int
                ],
                diagnostics=[
                    "native SRL decoding and candidate width bound "
                    "do not establish semantic exhaustiveness",
                    "constituency sentinel repair: " + startup["constituency_eos"],
                    "omitted checkpoint buffers: "
                    + ",".join(startup["omitted_checkpoint_buffers"]),
                ],
            )
            from corpus_structure.semantic.observations import source_value
            row["execution_profile"] = source_value(worker.selection_factory().native.wire)
            row["startup_observation"] = source_value(startup)
            row["availability"] = _availability(builder, "hanlp")
            builder.native_runs.append(row)
