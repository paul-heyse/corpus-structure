"""Thin detached GLiNER contracts; observations remain candidates, never accepted facts.

Native combined extraction is the ordinary route. The bounded proposal diagnostic
does not supply decoded observations or admission witnesses.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import math
import platform
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, Literal

if TYPE_CHECKING:
    from corpus_structure.semantic.source_contexts import NativeSourceContext


def _json(value: object) -> str:
    # Object and list order both matter to native schema conditioning.
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def _digest(value: object) -> str:
    return hashlib.sha256(_json(value).encode()).hexdigest()


class GlinerRefused(ValueError):
    """A request cannot preserve the selected profile/input contract."""


WHITESPACE_PROFILE = "gliner2-2.1.0-cpu-fp32-standard-whitespace-v1"
CODEPOINT_PROFILE = "gliner2-2.1.0-cpu-fp32-standard-codepoints-v1"
CUDA_WHITESPACE_PROFILE = "gliner2-2.1.0-cuda-fp32-standard-whitespace-v1"
CUDA_CODEPOINT_PROFILE = "gliner2-2.1.0-cuda-fp32-standard-codepoints-v1"
BOUNDARY_DIAGNOSTIC = "boundary-span-diagnostic-1"
MAX_DIAGNOSTIC_SPANS = 256


class UnicodeCodepointSplitter:
    """One non-whitespace source codepoint per token; source offsets never change."""

    def __call__(self, text: str, lower: bool = True):
        for index, character in enumerate(text):
            if not character.isspace():
                yield character.lower() if lower else character, index, index + 1


def gliner_profile_device(version: str) -> Literal["cpu", "cuda"]:
    """The profile owner interprets both current CUDA and sealed CPU versions."""
    if version in {CUDA_WHITESPACE_PROFILE, CUDA_CODEPOINT_PROFILE}:
        return "cuda"
    if version in {WHITESPACE_PROFILE, CODEPOINT_PROFILE}:
        return "cpu"
    raise GlinerRefused("unsupported execution profile")


def normalize_gliner_profile(
    values: Mapping[str, Any], *, snapshot: Path | None = None, json_input: bool = False
) -> dict[str, Any]:
    """Validate non-acquisition fields and normalize the owned artifact-map meaning.

    Projection from retained JSON has no acquisition location. It validates all
    represented invariants without inventing a path or asserting artifact availability.
    Normal construction additionally supplies its actual snapshot for the metadata bound.
    """
    values = dict(values)
    if (
        not isinstance(values["checkpoint"], str)
        or not values["checkpoint"]
        or not isinstance(values["revision"], str)
        or not values["revision"]
    ):
        raise GlinerRefused("profile requires an absolute local snapshot and immutable identity")
    if json_input:
        hashes = values["artifact_hashes"]
        if not isinstance(hashes, list) or any(
            not isinstance(entry, list) or len(entry) != 2 for entry in hashes
        ):
            raise GlinerRefused("artifact hashes require JSON pairs")
        values["artifact_hashes"] = tuple(tuple(entry) for entry in hashes)
    gliner_profile_device(values["version"])
    for bound in (
        values["threads"],
        values["max_input_bytes"],
        values["max_words"],
        values["max_subwords"],
        values["max_batch"],
        values["max_batch_bytes"],
        values["max_schema_bytes"],
        values["max_metadata_bytes"],
        values["max_request_frame_bytes"],
        values["max_reply_frame_bytes"],
    ):
        if type(bound) is not int or bound < 1:
            raise GlinerRefused("runtime bounds must be positive integers")
    if not math.isfinite(values["timeout_seconds"]) or values["timeout_seconds"] <= 0:
        raise GlinerRefused("timeout must be positive and finite")
    if not isinstance(values["artifact_hashes"], tuple) or any(
        not isinstance(entry, tuple) for entry in values["artifact_hashes"]
    ):
        raise GlinerRefused("artifact hashes must be immutable tuples")
    names = {name for name, _ in values["artifact_hashes"]}
    required = {
        "config.json",
        "encoder_config/config.json",
        "model.safetensors",
        "tokenizer.json",
        "tokenizer_config.json",
    }
    if names != required or len(values["artifact_hashes"]) != len(required):
        raise GlinerRefused("profile requires exactly the five qualified snapshot artifacts")
    metadata = [
        *([str(snapshot)] if snapshot is not None else []),
        values["checkpoint"],
        values["revision"],
        values["version"],
        *(part for entry in values["artifact_hashes"] for part in entry),
    ]
    if sum(len(value.encode()) for value in metadata) > values["max_metadata_bytes"]:
        raise GlinerRefused("profile metadata byte bound exceeded")
    for _, digest in values["artifact_hashes"]:
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise GlinerRefused("artifact identity must be SHA-256")
    values["artifact_hashes"] = sorted(values["artifact_hashes"])
    return values


@dataclass(frozen=True)
class GlinerProfile:
    snapshot: Annotated[Path, "ddo:acquisition"]
    checkpoint: Annotated[str, "ddo:semantic"]
    revision: Annotated[str, "ddo:semantic"]
    artifact_hashes: Annotated[tuple[tuple[str, str], ...], "ddo:semantic"]
    threads: Annotated[int, "ddo:execution"] = 4
    max_input_bytes: Annotated[int, "ddo:execution"] = 32768
    max_words: Annotated[int, "ddo:execution"] = 512
    max_subwords: Annotated[int, "ddo:execution"] = 2048
    max_batch: Annotated[int, "ddo:execution"] = 4
    max_batch_bytes: Annotated[int, "ddo:execution"] = 65536
    max_schema_bytes: Annotated[int, "ddo:execution"] = 32768
    max_metadata_bytes: Annotated[int, "ddo:execution"] = 8192
    max_request_frame_bytes: Annotated[int, "ddo:execution"] = 131072
    max_reply_frame_bytes: Annotated[int, "ddo:execution"] = 1048576
    timeout_seconds: Annotated[float, "ddo:execution"] = 120
    version: Annotated[str, "ddo:semantic"] = CUDA_WHITESPACE_PROFILE

    def __post_init__(self) -> None:
        if not self.snapshot.is_absolute():
            raise GlinerRefused(
                "profile requires an absolute local snapshot and immutable identity"
            )
        values = asdict(self)
        del values["snapshot"]
        normalize_gliner_profile(values, snapshot=self.snapshot)

    @property
    def device(self) -> Literal["cpu", "cuda"]:
        return gliner_profile_device(self.version)

    @property
    def codepoint_splitter(self) -> bool:
        return self.version in {CODEPOINT_PROFILE, CUDA_CODEPOINT_PROFILE}

    @property
    def fingerprint(self) -> str:
        identity = asdict(self)
        del identity["snapshot"]  # Acquisition location is provenance, not model behavior.
        identity["artifact_hashes"] = sorted(self.artifact_hashes)
        return _digest(identity)

    def verify_artifacts(self) -> None:
        """Verify acquired files, without downloads or installing anything."""
        if not self.snapshot.is_dir():
            raise GlinerRefused("immutable local snapshot is unavailable")
        names = {name for name, _ in self.artifact_hashes}
        directories = {str(Path(name).parent) for name in names} - {"."}
        for path in self.snapshot.rglob("*"):
            relative = path.relative_to(self.snapshot).as_posix()
            if path.is_dir() and not path.is_symlink():
                allowed = relative in directories
            else:
                allowed = relative in names and path.is_file()
            if not allowed:
                raise GlinerRefused(f"unexpected snapshot entry: {relative}")
        for name, expected in self.artifact_hashes:
            path = self.snapshot / name
            if not path.is_file():
                raise GlinerRefused(f"missing snapshot artifact: {name}")
            with path.open("rb") as handle:
                actual = hashlib.file_digest(handle, "sha256").hexdigest()
            if actual != expected:
                raise GlinerRefused(f"snapshot artifact differs: {name}")


ASSERTION_LITERAL_PACK = "native-assertion-literal-v1"


@dataclass(frozen=True)
class GlinerPack:
    release: str
    declaration_json: str
    version: str = "native-combined-v1"

    @classmethod
    def from_declaration(
        cls, release: str, declaration: dict[str, Any], *, version: str = "native-combined-v1"
    ) -> GlinerPack:
        pack = cls(release, _json(declaration), version)
        pack.compile()
        return pack

    def compile(self) -> Any:
        # Lazy method-boundary import. No model object crosses the worker boundary.
        from gliner2.inference.schema import Schema

        if not self.release.strip() or self.version not in {
            "native-combined-v1",
            "native-combined-v2",
            "native-local-v1",
            ASSERTION_LITERAL_PACK,
        }:
            raise GlinerRefused("pack requires a released identity and supported operation")
        declaration = json.loads(self.declaration_json)
        if not isinstance(declaration, dict):
            raise GlinerRefused("schema declaration must be an object")
        structures = declaration.get("structures", {})
        if self.version == ASSERTION_LITERAL_PACK and (
            set(declaration) != {"structures"}
            or not isinstance(structures, dict)
            or set(structures) != {"assertion"}
        ):
            raise GlinerRefused("literal assertion packs require exactly one assertion structure")
        if self.version == "native-local-v1" and (
            declaration.get("structures")
            or not (declaration.get("entities") or declaration.get("relations"))
        ):
            raise GlinerRefused(
                "local packs require entity or relation questions without record structures"
            )
        for structure in structures.values():
            names = [field["name"] for field in structure.get("fields", [])]
            if len(names) != len(set(names)):
                raise GlinerRefused("duplicate structure field names are unsupported")
            mode, anchor = structure.get("mode"), structure.get("anchor")
            if self.version == ASSERTION_LITERAL_PACK and (
                mode != "natural"
                or anchor != "predicate"
                or anchor not in names
                or any("choices" in field or "__" in field["name"] for field in structure["fields"])
            ):
                raise GlinerRefused(
                    "literal assertion packs require a natural predicate and literal fields"
                )
            if self.version == "native-combined-v1" and (mode != "natural" or not anchor):
                raise GlinerRefused("initial packs require an explicit natural occurrence anchor")
            if self.version == "native-combined-v2" and not (
                (mode == "natural" and anchor) or (mode == "latent" and anchor is None)
            ):
                raise GlinerRefused("v2 packs require natural anchored or latent grouping")
        schema = Schema.from_dict(declaration)
        effective = schema.to_dict()
        if Schema.from_dict(effective).to_dict() != effective:
            raise GlinerRefused("native schema declaration does not round-trip")
        return schema

    @property
    def fingerprint(self) -> str:
        return _digest(asdict(self))

    def field_is_classified(self, structure: str, field: str) -> bool:
        fields = json.loads(self.declaration_json)["structures"][structure]["fields"]
        matching = [item for item in fields if item["name"] == field]
        if len(matching) != 1:
            raise GlinerRefused("record field must have one unambiguous declaration")
        return bool(matching[0].get("choices"))


@dataclass(frozen=True)
class GlinerInput:
    @classmethod
    def from_context(cls, context: NativeSourceContext) -> GlinerInput:
        if context.version not in {1, 2}:
            raise GlinerRefused("unsupported native source context version")
        return cls(context.dependency_digest, context.dependency_digest, context.text)

    context_id: str
    context_digest: str
    text: str
    operation: str | None = None

    def __post_init__(self) -> None:
        if not self.context_id or not self.text or len(self.context_digest) != 64:
            raise GlinerRefused("input requires nonempty context identity, digest and text")
        if any(c not in "0123456789abcdef" for c in self.context_digest):
            raise GlinerRefused("context identity must be SHA-256")


@dataclass(frozen=True)
class GlinerPreparation:
    consumed_text: str
    synthetic_suffix: str
    words: int
    subwords: int
    input_bytes: int


@dataclass(frozen=True)
class GlinerReport:
    context_id: str
    context_digest: str
    computation: str
    profile: str
    pack: str
    preparation: GlinerPreparation
    raw_json: str
    effective_profile_json: str
    inference_seconds: float
    resident_reused: bool
    # Native high-level extraction does not expose these diagnostics.
    diagnostics: tuple[tuple[str, str], ...] = (
        ("proposal_pool", "unavailable"),
        ("suppression", "unavailable"),
        ("count", "unavailable"),
        ("abstention", "unavailable"),
        ("feasibility", "unavailable"),
    )
    request_digest: str | None = None
    observation_digest: str | None = None
    batch_receipt_json: str | None = None
    member_ordinal: int | None = None

    @property
    def raw(self) -> dict[str, Any]:
        return json.loads(self.raw_json)


def map_literal(
    report: GlinerReport,
    context: NativeSourceContext,
    span: dict[str, Any],
    *,
    allow_multiple: bool = False,
) -> tuple[Any, ...]:
    """Map a declared literal only; choices/attributes retain classification separately.

    The existing context owner enforces synthetic crossings and occurrence coordinates.
    Provider-added suffix material is never allowed to become source evidence.
    """
    from corpus_structure.semantic.source_contexts import ContextRefused

    try:
        context.require_native_projection()
    except ContextRefused as error:
        raise GlinerRefused(str(error)) from error
    if report.context_digest != context.dependency_digest:
        raise GlinerRefused("report belongs to another source context")
    if report.preparation.consumed_text != context.text + report.preparation.synthetic_suffix:
        raise GlinerRefused("provider preprocessing changed the source prefix")
    start, end, literal = span.get("start"), span.get("end"), span.get("text")
    if (
        type(start) is not int
        or type(end) is not int
        or not isinstance(literal, str)
        or not 0 <= start < end <= len(context.text)
        or context.text[start:end] != literal
    ):
        raise GlinerRefused("literal does not reconstruct independently in source coordinates")
    return context.map_span(start, end, literal=literal, allow_multiple=allow_multiple)


def map_record_field(
    pack: GlinerPack,
    structure: str,
    field: str,
    report: GlinerReport,
    context: NativeSourceContext,
    span: dict[str, Any],
    *,
    allow_multiple: bool = False,
) -> tuple[Any, ...]:
    """Guard the report's exact schema and field kind before literal source mapping."""
    if report.pack != pack.fingerprint:
        raise GlinerRefused("report belongs to another schema pack")
    if pack.field_is_classified(structure, field):
        raise GlinerRefused("classified field offsets cannot become literal field evidence")
    return map_literal(report, context, span, allow_multiple=allow_multiple)


def prepare_input(
    model: Any, pack: Any, item: GlinerInput, profile: GlinerProfile
) -> GlinerPreparation:
    size = len(item.text.encode())
    if size > profile.max_input_bytes:
        raise GlinerRefused("input byte bound exceeded")
    # No max_len: inspect complete native preparation before admitting inference.
    prepared = model.processor.transform_record(item.text, pack, max_len=None)
    if not prepared.text.startswith(item.text):
        raise GlinerRefused("native preprocessing changed source text")
    suffix = prepared.text[len(item.text) :]
    if suffix not in ("", "."):
        raise GlinerRefused("unsupported native synthetic text delta")
    words, subwords = len(prepared.start_token_idx), len(prepared.input_ids)
    if len(prepared.end_token_idx) != words or words > profile.max_words:
        raise GlinerRefused("native word bound exceeded or token maps disagree")
    if subwords > profile.max_subwords:
        raise GlinerRefused("schema-conditioned subword bound exceeded")
    if any(
        not 0 <= start < end <= len(prepared.text)
        for start, end in zip(prepared.start_token_idx, prepared.end_token_idx, strict=True)
    ):
        raise GlinerRefused("native token map lies outside consumed text")
    return GlinerPreparation(prepared.text, suffix, words, subwords, size)


def boundary_diagnostic(
    model: Any,
    schema: Any,
    item: GlinerInput,
    prepared: GlinerPreparation,
    supplied: tuple[tuple[int, int], ...],
) -> dict[str, Any]:
    """Report ordinary and independently supplied spans on the same bounded input."""
    import torch

    if getattr(model, "architecture", None) != "boundary":
        raise GlinerRefused("proposal diagnostics require the native boundary checkpoint")
    # Same native collation as batch_extract, but never fall back to a dummy row.
    batch = model.processor.collate_fn_inference(
        [(item.text, schema.build())], architecture="boundary", error_policy="raise"
    )
    if len(batch) != 1 or batch.original_texts[0] != prepared.consumed_text:
        raise GlinerRefused("native diagnostic collation differs from the prepared scope")
    parameter = next(model.parameters())
    # The native batch_extract route performs this transfer itself. Public
    # score_candidates/encode consume an already device-owned PreprocessedBatch.
    batch = batch.to(
        parameter.device, parameter.dtype if parameter.dtype != torch.float32 else None
    )
    starts, ends = batch.start_mappings[0], batch.end_mappings[0]
    prefix = int(batch.text_word_counts[0]) - len(starts)
    layout = batch.query_layouts[0].queries
    if (
        prefix < 0
        or len(starts) != prepared.words
        or len(ends) != prepared.words
        or len(set(starts)) != len(starts)
        or len(set(ends)) != len(ends)
    ):
        raise GlinerRefused("native diagnostic word mapping differs from preparation")
    if not 0 < len(layout) <= 16:
        raise GlinerRefused("diagnostic requires between 1 and 16 native extractive queries")
    aligned = []
    for start, end in supplied:
        try:
            left = starts.index(start)
            right = ends.index(end) + 1
        except ValueError as error:
            raise GlinerRefused("supplied span is not aligned to native word boundaries") from error
        if not 0 <= start < end <= len(item.text) or left >= right:
            raise GlinerRefused("supplied span is outside the exact native source word range")
        aligned.append((left + prefix, right + prefix))

    if (
        model.boundary_settings.candidate_pool == "shared"
        and len(set(aligned)) > model.boundary_settings.pool_size
    ):
        raise GlinerRefused("explicit spans exceed the native shared candidate pool")
    with torch.inference_mode():
        candidates, aux = model.score_candidates(batch, return_auxiliary_logits=True)
        if candidates is None or candidates.shape[:2] != (1, len(layout)):
            raise GlinerRefused("native candidate population differs from the extractive layout")
        ordinary = []
        pairs = {}
        for query, positions in enumerate(candidates.indices[0].tolist()):
            for index, (left, right) in enumerate(positions):
                if not bool(candidates.valid_mask[0, query, index]):
                    continue
                exact = None
                if prefix <= left < right <= prefix + len(starts):
                    start, end = starts[left - prefix], ends[right - prefix - 1]
                    if 0 <= start < end <= len(item.text):
                        exact = [start, end]
                logit = float(candidates.pair_logits[0, query, index])
                pairs[query, left, right] = logit
                ordinary.append(
                    {
                        "query": query,
                        "words": [left, right],
                        "input_chars": exact,
                        "pair_logit": logit,
                        "proposal_logit": (
                            float(candidates.proposal_logits[0, query, index])
                            if candidates.proposal_logits is not None
                            else None
                        ),
                    }
                )

        explicit = []
        if aligned:
            encoded = model.encode(batch)

            # encode() expands entity field_path to (entities, name); query identity
            # is the group/role route, not that redundant representation.
            def query_routes(queries):
                return [
                    (q.query_id, q.task_index, q.task_type, q.task_name, q.role_index, q.role_name)
                    for q in queries
                ]

            if query_routes(encoded.query_layouts[0].queries) != query_routes(layout) or int(
                encoded.text_lengths[0]
            ) != prefix + len(starts):
                raise GlinerRefused("native explicit scoring changed the extractive query layout")
            indices = torch.tensor(aligned, dtype=torch.long, device=encoded.text_states.device)[
                None, None
            ].expand(1, len(layout), -1, -1)
            try:
                scored = model.score_explicit_spans(encoded, indices)[0].tolist()
            except ValueError as error:
                if "exceed the shared candidate pool" not in str(error):
                    raise
                raise GlinerRefused(
                    "explicit spans exceed the native shared candidate pool"
                ) from error
            for query, logits in enumerate(scored):
                for (left, right), chars, logit in zip(aligned, supplied, logits, strict=True):
                    explicit.append(
                        {
                            "query": query,
                            "words": [left, right],
                            "input_chars": list(chars),
                            "pair_logit": logit,
                            "ordinary_pair_logit": pairs.get((query, left, right)),
                        }
                    )
    return {
        "operation": BOUNDARY_DIAGNOSTIC,
        "queries": [asdict(query) for query in layout],
        "schema_prefix_words": prefix,
        "ordinary": ordinary,
        "explicit": explicit,
        "available_boundary_logits": sorted(key for key, value in aux.items() if value is not None),
    }


def effective_profile_fingerprint(effective_json: str) -> str:
    """Identify effective semantics while retaining loader locations only as provenance."""
    identity = json.loads(effective_json)
    identity.pop("snapshot", None)
    identity["config"].pop("_name_or_path", None)
    return _digest(identity)


def load_model(profile: GlinerProfile, *, configure_process: bool = True) -> tuple[Any, str]:
    profile.verify_artifacts()
    if importlib.metadata.version("gliner2") != "2.1.0":
        raise GlinerRefused("native adapter requires gliner2==2.1.0")
    import torch
    from gliner2 import AutoExtractor
    from gliner2.processing.word_splitter import WhitespaceTokenSplitter

    if configure_process:
        torch.set_num_threads(profile.threads)
        torch.set_num_interop_threads(1)
    if profile.device == "cuda" and not torch.cuda.is_available():
        raise GlinerRefused("CUDA GLiNER requires an available GPU")
    model = AutoExtractor.from_pretrained(
        str(profile.snapshot),
        map_location=profile.device,
        word_splitter=(UnicodeCodepointSplitter() if profile.codepoint_splitter else "whitespace"),
        attention_backend="standard",
    )
    model.to(profile.device)
    model.eval()
    from threadpoolctl import threadpool_info, threadpool_limits

    if configure_process:
        limiter = threadpool_limits(limits=profile.threads)
        import atexit

        atexit.register(limiter.restore_original_limits)
    if any(p.device.type != profile.device or p.dtype != torch.float32 for p in model.parameters()):
        raise GlinerRefused("resident weights differ from selected FP32 device")
    expected_splitter = (
        UnicodeCodepointSplitter if profile.codepoint_splitter else WhitespaceTokenSplitter
    )
    if type(model.processor.word_splitter) is not expected_splitter:
        raise GlinerRefused("resident splitter differs from the selected recipe")
    if getattr(model, "architecture", None) != "boundary":
        raise GlinerRefused("resident checkpoint lacks the selected boundary architecture")
    settings = asdict(model.boundary_settings)
    if settings.get("adaptive_threshold", False):
        raise GlinerRefused("adaptive threshold is outside the initial profile")
    effective = _json(
        {
            "profile": profile.fingerprint,
            "snapshot": str(profile.snapshot),
            "python": platform.python_version(),
            "config": model.config.to_dict(),
            "boundary_settings": settings,
            "splitter": expected_splitter.__name__,
            "dtype": "float32",
            "device": profile.device,
            "attention_backend": "standard",
            "threads": torch.get_num_threads(),
            "interop_threads": torch.get_num_interop_threads(),
            "supported_pools": threadpool_info(),
            "versions": {
                name: importlib.metadata.version(name)
                for name in ("gliner2", "torch", "transformers", "tokenizers", "safetensors")
            },
        }
    )
    return model, effective
