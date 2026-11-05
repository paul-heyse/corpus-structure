"""Thin detached GLiNER contracts; observations remain candidates, never accepted facts.

Only native combined extraction is selected here. Classifier/JointIE wrappers, persistent
encoding caches, aggregate CPU admission and method registration remain integration work.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import math
import platform
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

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


class UnicodeCodepointSplitter:
    """One non-whitespace source codepoint per token; source offsets never change."""

    def __call__(self, text: str, lower: bool = True):
        for index, character in enumerate(text):
            if not character.isspace():
                yield character.lower() if lower else character, index, index + 1


@dataclass(frozen=True)
class GlinerProfile:
    snapshot: Path
    checkpoint: str
    revision: str
    artifact_hashes: tuple[tuple[str, str], ...]
    threads: int = 4
    max_input_bytes: int = 32768
    max_words: int = 512
    max_subwords: int = 2048
    max_batch: int = 4
    max_batch_bytes: int = 65536
    max_schema_bytes: int = 32768
    max_metadata_bytes: int = 8192
    max_request_frame_bytes: int = 131072
    max_reply_frame_bytes: int = 1048576
    timeout_seconds: float = 120
    version: str = WHITESPACE_PROFILE

    def __post_init__(self) -> None:
        if not self.snapshot.is_absolute() or not self.checkpoint or not self.revision:
            raise GlinerRefused(
                "profile requires an absolute local snapshot and immutable identity"
            )
        if self.version not in {WHITESPACE_PROFILE, CODEPOINT_PROFILE}:
            raise GlinerRefused("unsupported execution profile")
        for bound in (
            self.threads,
            self.max_input_bytes,
            self.max_words,
            self.max_subwords,
            self.max_batch,
            self.max_batch_bytes,
            self.max_schema_bytes,
            self.max_metadata_bytes,
            self.max_request_frame_bytes,
            self.max_reply_frame_bytes,
        ):
            if type(bound) is not int or bound < 1:
                raise GlinerRefused("runtime bounds must be positive integers")
        if not math.isfinite(self.timeout_seconds) or self.timeout_seconds <= 0:
            raise GlinerRefused("timeout must be positive and finite")
        if not isinstance(self.artifact_hashes, tuple) or any(
            not isinstance(entry, tuple) for entry in self.artifact_hashes
        ):
            raise GlinerRefused("artifact hashes must be immutable tuples")
        names = {name for name, _ in self.artifact_hashes}
        required = {
            "config.json",
            "encoder_config/config.json",
            "model.safetensors",
            "tokenizer.json",
            "tokenizer_config.json",
        }
        if names != required or len(self.artifact_hashes) != len(required):
            raise GlinerRefused("profile requires exactly the five qualified snapshot artifacts")
        metadata = [
            str(self.snapshot),
            self.checkpoint,
            self.revision,
            self.version,
            *(part for entry in self.artifact_hashes for part in entry),
        ]
        if sum(len(value.encode()) for value in metadata) > self.max_metadata_bytes:
            raise GlinerRefused("profile metadata byte bound exceeded")
        for _, digest in self.artifact_hashes:
            if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                raise GlinerRefused("artifact identity must be SHA-256")

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
        }:
            raise GlinerRefused("pack requires a released identity and supported operation")
        declaration = json.loads(self.declaration_json)
        if not isinstance(declaration, dict):
            raise GlinerRefused("schema declaration must be an object")
        if self.version == "native-local-v1" and (
            declaration.get("structures")
            or not (declaration.get("entities") or declaration.get("relations"))
        ):
            raise GlinerRefused(
                "local packs require entity or relation questions without record structures"
            )
        for structure in declaration.get("structures", {}).values():
            names = [field["name"] for field in structure.get("fields", [])]
            if len(names) != len(set(names)):
                raise GlinerRefused("duplicate structure field names are unsupported")
            mode, anchor = structure.get("mode"), structure.get("anchor")
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


def effective_profile_fingerprint(effective_json: str) -> str:
    """Identify effective semantics while retaining loader locations only as provenance."""
    identity = json.loads(effective_json)
    identity.pop("snapshot", None)
    identity["config"].pop("_name_or_path", None)
    return _digest(identity)


def load_model(profile: GlinerProfile) -> tuple[Any, str]:
    profile.verify_artifacts()
    if importlib.metadata.version("gliner2") != "2.1.0":
        raise GlinerRefused("native adapter requires gliner2==2.1.0")
    import torch
    from gliner2 import AutoExtractor
    from gliner2.processing.word_splitter import WhitespaceTokenSplitter

    torch.set_num_threads(profile.threads)
    torch.set_num_interop_threads(1)
    model = AutoExtractor.from_pretrained(
        str(profile.snapshot),
        map_location="cpu",
        word_splitter=(
            UnicodeCodepointSplitter() if profile.version == CODEPOINT_PROFILE else "whitespace"
        ),
        attention_backend="standard",
    )
    model.eval()
    if any(p.device.type != "cpu" or p.dtype != torch.float32 for p in model.parameters()):
        raise GlinerRefused("resident weights are not FP32 CPU")
    expected_splitter = (
        UnicodeCodepointSplitter
        if profile.version == CODEPOINT_PROFILE
        else WhitespaceTokenSplitter
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
            "device": "cpu",
            "attention_backend": "standard",
            "threads": torch.get_num_threads(),
            "interop_threads": torch.get_num_interop_threads(),
            "versions": {
                name: importlib.metadata.version(name)
                for name in ("gliner2", "torch", "transformers", "tokenizers", "safetensors")
            },
        }
    )
    return model, effective
