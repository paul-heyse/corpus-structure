"""Owned CPU contextual encoding. Source addresses and rendered inputs remain separate.

No knowledge or canonical identity is established by these derived vectors. The caller owns
source admission, task fencing and publication; this operation owns its sole native child.
"""

from __future__ import annotations

import importlib
import json
import math
import struct
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from functools import lru_cache
from hashlib import file_digest, sha256
from pathlib import Path
from threading import Event
from time import monotonic
from typing import Literal

from corpus_structure.semantic.identity import canonical_bytes


def identity(kind: str, value: object) -> str:
    return kind + ":" + sha256(canonical_bytes(value)).hexdigest()


def numeric_identity(kind: str, value: object) -> str:
    """Canonical numeric report identity survives PostgreSQL JSONB exponent rewriting."""

    def normalize(value):
        if type(value) in {int, float}:
            return {"native_float64": struct.pack(">d", value).hex()}
        if isinstance(value, dict):
            return {key: normalize(item) for key, item in value.items()}
        if isinstance(value, (tuple, list)):
            return [normalize(item) for item in value]
        return value

    return identity(kind, normalize(value))


@dataclass(frozen=True)
class EncoderProfile:
    model: str
    revision: str
    dimension: int
    query_prompt: str
    document_prompt: str
    pooling: Literal["mean", "lasttoken"]
    max_tokens: int = 512
    batch_size: int = 16
    max_items: int = 256
    max_input_bytes: int = 1048576
    timeout_seconds: float = 300.0
    recipe: str = "located-context-1"
    sentence_transformers_version: str = "6.2.0"
    transformers_version: str = "5.22.1"
    torch_version: str = "2.15.0+cu132"
    tokenizers_version: str = "0.23.3"

    def __post_init__(self):
        if len(self.revision) != 40 or any(c not in "0123456789abcdef" for c in self.revision):
            raise ValueError("encoder requires an immutable model revision")
        for bound in (
            self.dimension,
            self.max_tokens,
            self.batch_size,
            self.max_items,
            self.max_input_bytes,
        ):
            if type(bound) is not int or bound <= 0:
                raise ValueError("encoder bounds must be positive integers")
        if not math.isfinite(self.timeout_seconds) or self.timeout_seconds <= 0:
            raise ValueError("encoder timeout must be positive and finite")
        if not self.model or self.pooling not in {"mean", "lasttoken"}:
            raise ValueError("encoder requires a model and declared pooling")

    @property
    def semantic_configuration(self):
        meaning = asdict(self)
        for key in ("max_items", "max_input_bytes", "timeout_seconds"):
            del meaning[key]
        return meaning

    @property
    def profile_id(self) -> str:
        return identity("encoder-profile", self.semantic_configuration)


def verify_encoder_implementation(profile: EncoderProfile):
    """The loaded implementations, including Torch build, must match the declared space."""
    expected = (
        ("sentence_transformers", profile.sentence_transformers_version),
        ("transformers", profile.transformers_version),
        ("torch", profile.torch_version),
        ("tokenizers", profile.tokenizers_version),
    )
    actual = tuple((name, importlib.import_module(name).__version__) for name, _ in expected)
    if actual != expected:
        raise ValueError("loaded encoder implementation versions differ from declared profile")
    return actual


E5 = EncoderProfile(
    "intfloat/e5-small-v2",
    "ffb93f3bd4047442299a41ebb6fa998a38507c52",
    384,
    "query: ",
    "passage: ",
    "mean",
)
QWEN = EncoderProfile(
    "Qwen/Qwen3-Embedding-0.6B",
    "97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3",
    1024,
    ("Instruct: Retrieve source-grounded definitions explaining this usage.\nQuery: "),
    "",
    "lasttoken",
    batch_size=4,
)


@dataclass(frozen=True)
class ContextInput:
    object_id: str
    source_binding: str
    role: Literal["query", "document"]
    literal: str
    context: str
    start: int
    end: int
    heading: str = ""
    parent: str = ""
    type_name: str | None = None
    representation_digest: str = ""
    query_context: str | None = None

    def __post_init__(self):
        if not self.object_id or not self.source_binding or not self.literal:
            raise ValueError("context requires object, source binding and literal")
        if self.role not in {"query", "document"}:
            raise ValueError("unsupported encoder role")
        if not 0 <= self.start < self.end <= len(self.context):
            raise ValueError("context occurrence is outside its source")
        if self.context[self.start : self.end] != self.literal:
            raise ValueError("context occurrence must reconstruct its exact source literal")
        if self.query_context is not None and (
            self.role != "query" or not self.query_context or not self.representation_digest
        ):
            raise ValueError("located query context requires its own representation identity")


@dataclass(frozen=True)
class RenderedInput:
    object_id: str
    source_binding: str
    role: Literal["query", "document"]
    text: str
    final_input_digest: str
    truncated: bool
    representation_digest: str = ""


class ContextCoreLimited(ValueError):
    """The exact literal and required context do not fit the selected encoder."""


_CONTEXT_STEP = 16


def _context_core(item: ContextInput) -> str:
    core = f"Mention: {item.literal}\nType: {item.type_name or 'unknown'}"
    if item.parent:
        core += f"\nParent: {item.parent}"
    if item.heading:
        core += f"\nHeading: {item.heading}"
    if item.query_context is not None:
        core += "\n" + item.query_context
    return core + "\nContext: "


def verify_retained_rendering(
    item: ContextInput, profile: EncoderProfile, retained: RenderedInput
) -> None:
    """Authenticate captured input bytes and source window without claiming token-budget replay."""
    core = _context_core(item)
    prompt = profile.query_prompt if item.role == "query" else profile.document_prompt
    if (
        (retained.object_id, retained.source_binding, retained.role, retained.representation_digest)
        != (item.object_id, item.source_binding, item.role, item.representation_digest)
        or type(retained.text) is not str
        or not retained.text.startswith(core)
        or retained.final_input_digest != sha256((prompt + retained.text).encode()).hexdigest()
    ):
        raise ValueError("retained contextual rendering differs from its source and signal")
    window = retained.text[len(core) :]
    if type(retained.truncated) is not bool or retained.truncated != (window != item.context):
        raise ValueError("retained contextual window has inconsistent truncation")
    if not retained.truncated:
        return
    extra = len(window) - len(item.literal)
    near = min(item.start, len(item.context) - item.end)
    radius = extra // 2 if extra < 2 * near else extra - near
    left, right = max(0, item.start - radius), min(len(item.context), item.end + radius)
    if extra < 0 or radius % _CONTEXT_STEP or window != item.context[left:right]:
        raise ValueError("retained contextual window is outside the source rendering recipe")


def render_context(
    item: ContextInput, profile: EncoderProfile, token_count: Callable[[str], int]
) -> RenderedInput:
    """Keep occurrence and discriminating metadata; trim only surrounding context.

    The count includes role prefix and tokenizer special tokens. Native encoding must not
    truncate the admitted string again. Source coordinates are never coordinates in this text.
    """
    prompt = profile.query_prompt if item.role == "query" else profile.document_prompt
    core = _context_core(item)
    minimum = core + item.literal
    if token_count(prompt + minimum) > profile.max_tokens:
        raise ContextCoreLimited("occurrence and discriminating context exceed encoder token bound")
    full = core + item.context
    if token_count(prompt + full) <= profile.max_tokens:
        text = full
    else:
        # Expand a centered real substring; every accepted candidate is counted with the
        # actual tokenizer. No assumption that token count is monotonic in character length.
        text = minimum
        left, right = item.start, item.end
        while left > 0 or right < len(item.context):
            next_left = max(0, left - _CONTEXT_STEP)
            next_right = min(len(item.context), right + _CONTEXT_STEP)
            candidate = core + item.context[next_left:next_right]
            if token_count(prompt + candidate) > profile.max_tokens:
                break
            left, right, text = next_left, next_right, candidate
    return RenderedInput(
        item.object_id,
        item.source_binding,
        item.role,
        text,
        sha256((prompt + text).encode()).hexdigest(),
        text != full,
        item.representation_digest,
    )


@dataclass(frozen=True)
class EncodedVector:
    vector_id: str
    object_id: str
    source_binding: str
    profile_id: str
    input_digest: str
    values: tuple[float, ...]
    representation_digest: str = ""


def validate_vector(values: Sequence[float], dimension: int) -> tuple[float, ...]:
    result = tuple(float(value) for value in values)
    if len(result) != dimension or any(not math.isfinite(value) for value in result):
        raise ValueError("vector has invalid dimension or nonfinite values")
    norm = math.sqrt(sum(value * value for value in result))
    if norm == 0 or not math.isfinite(norm) or not math.isclose(norm, 1, abs_tol=1e-5):
        raise ValueError("vector must be nonzero and L2-normalized")
    return result


@dataclass(frozen=True)
class EncoderResult:
    profile_id: str
    inputs: tuple[RenderedInput, ...]
    vectors: tuple[EncodedVector, ...]
    implementation: tuple[tuple[str, str], ...]
    reused_vector_ids: tuple[str, ...] = ()
    limited_query_ids: tuple[str, ...] = ()


class EncoderCancelled(RuntimeError):
    """Cancelled native work; never a completed empty vector population."""


class EncoderLimited(RuntimeError):
    """Declared encoder bound or deadline exceeded."""


@lru_cache(maxsize=1)
def _owned_cpu_encoder(profile_content, model_path, artifact_hashes):
    """Reuse immutable acquired model resources inside the existing CPU worker."""
    profile = EncoderProfile(**json.loads(profile_content))
    root = Path(model_path)
    observations = ()
    if artifact_hashes:
        if not root.is_dir() or any(
            Path(name).is_absolute() or ".." in Path(name).parts for name, _ in artifact_hashes
        ):
            raise ValueError("encoder acquisition escapes its selected model directory")
        if {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()} != {
            name for name, _ in artifact_hashes
        }:
            raise ValueError("encoder model file population differs from acquired artifacts")
        observations = tuple((name, (root / name).stat()) for name, _ in artifact_hashes)
        for name, digest in artifact_hashes:
            with (root / name).open("rb") as source:
                if file_digest(source, "sha256").hexdigest() != digest:
                    raise ValueError("encoder model bytes differ from acquired artifacts")
        _verify_cpu_artifacts(model_path, observations)
    from sentence_transformers import SentenceTransformer
    from sentence_transformers.sentence_transformer.modules import Pooling

    implementation = verify_encoder_implementation(profile)
    model = SentenceTransformer(
        model_path,
        revision=profile.revision,
        device="cpu",
        trust_remote_code=False,
        local_files_only=True,
    )
    model.float()
    model.max_seq_length = profile.max_tokens
    model.tokenizer.padding_side = "left" if profile.pooling == "lasttoken" else "right"
    poolings = [module for module in model if isinstance(module, Pooling)]
    if len(poolings) != 1 or poolings[0].get_config_dict().get("pooling_mode") != profile.pooling:
        raise ValueError("loaded model pooling differs from declared profile")
    return model, implementation, observations


def _verify_cpu_artifacts(model_path, observations):
    root = Path(model_path)
    if observations and {
        path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()
    } != {name for name, _ in observations}:
        raise ValueError("resident encoder model file population changed")
    for name, prior in observations:
        current = (Path(model_path) / name).stat()
        if (
            current.st_dev,
            current.st_ino,
            current.st_size,
            current.st_mtime_ns,
            current.st_ctime_ns,
        ) != (prior.st_dev, prior.st_ino, prior.st_size, prior.st_mtime_ns, prior.st_ctime_ns):
            raise ValueError("resident encoder acquisition changed after verified loading")


def _encode_owned_cpu(profile, items, cached_vectors, *, model_path, artifact_hashes, check_active):
    model, implementation, observations = _owned_cpu_encoder(
        canonical_bytes(profile.semantic_configuration), model_path, artifact_hashes
    )
    _verify_cpu_artifacts(model_path, observations)
    check_active()
    rendered, limited_queries = [], []
    for item in items:
        check_active()
        try:
            rendered.append(
                render_context(
                    item,
                    profile,
                    lambda text: len(model.tokenizer.encode(text, truncation=False)),
                )
            )
        except ContextCoreLimited:
            if item.query_context is None:
                raise
            limited_queries.append(item.object_id)
    cached_by_object = {value.object_id: value for value in cached_vectors}
    reused = {}
    for i, item in enumerate(rendered):
        cached = cached_by_object.get(item.object_id)
        if (
            item.role == "document"
            and cached is not None
            and (
                cached.source_binding == item.source_binding
                and cached.profile_id == profile.profile_id
                and cached.representation_digest == item.representation_digest
                and cached.input_digest == item.final_input_digest
            )
        ):
            validate_vector(cached.values, profile.dimension)
            reused[i] = cached.vector_id
    vectors = []
    for role in ("query", "document"):
        check_active()
        positions = [i for i, item in enumerate(rendered) if item.role == role and i not in reused]
        if not positions:
            continue
        encode = model.encode_query if role == "query" else model.encode_document
        prompt = profile.query_prompt if role == "query" else profile.document_prompt
        values = encode(
            [rendered[i].text for i in positions],
            prompt=prompt,
            normalize_embeddings=True,
            precision="float32",
            batch_size=profile.batch_size,
            show_progress_bar=False,
        )
        for i, value in zip(positions, values, strict=True):
            item = rendered[i]
            vector = validate_vector(value, profile.dimension)
            vector_id = identity(
                "context-vector",
                [
                    item.object_id,
                    item.source_binding,
                    profile.profile_id,
                    item.final_input_digest,
                    item.representation_digest,
                ],
            )
            vectors.append(
                (
                    i,
                    EncodedVector(
                        vector_id,
                        item.object_id,
                        item.source_binding,
                        profile.profile_id,
                        item.final_input_digest,
                        vector,
                        item.representation_digest,
                    ),
                )
            )
    result = EncoderResult(
        profile.profile_id,
        tuple(rendered),
        tuple(value for _, value in sorted(vectors)),
        implementation,
        tuple(reused[i] for i in sorted(reused)),
        tuple(limited_queries),
    )
    check_active()
    _verify_cpu_artifacts(model_path, observations)
    return result


def encode_contexts(
    items: Sequence[ContextInput],
    profile: EncoderProfile = E5,
    *,
    cancel: Event | None = None,
    local_files_only: bool = True,
    check_active: Callable[[], None] | None = None,
    cached_vectors: Sequence[EncodedVector] = (),
    model_path: str | None = None,
    artifact_hashes: tuple[tuple[str, str], ...] = (),
) -> EncoderResult:
    """Run original CPU inference under the caller's existing physical process owner.

    Acquired DDO calls supply their exact local model artifacts. No inner process,
    executor or provider lifecycle is created here.
    """
    items = tuple(items)
    cached_vectors = tuple(cached_vectors)
    if len(cached_vectors) > profile.max_items or len({v.object_id for v in cached_vectors}) != len(
        cached_vectors
    ):
        raise EncoderLimited(
            "cached vector population exceeds declared bound or duplicates objects"
        )
    for cached in cached_vectors:
        validate_vector(cached.values, profile.dimension)
    if not items or len(items) > profile.max_items:
        raise EncoderLimited("encoder item bound exceeded or empty request")
    if (
        len(
            canonical_bytes(
                [
                    {
                        key: value
                        for key, value in asdict(item).items()
                        if key != "query_context" or value is not None
                    }
                    for item in items
                ]
            )
        )
        > profile.max_input_bytes
    ):
        raise EncoderLimited("encoder request byte bound exceeded")
    if len({item.object_id for item in items}) != len(items):
        raise ValueError("duplicate encoded object identity")
    if cancel is not None and cancel.is_set():
        raise EncoderCancelled("encoding cancelled before model allocation")
    if local_files_only is not True:
        raise ValueError("contextual encoder requires explicitly acquired offline resources")

    deadline = monotonic() + profile.timeout_seconds

    def active():
        if monotonic() >= deadline:
            raise EncoderLimited("encoder deadline exceeded")
        if cancel is not None and cancel.is_set():
            raise EncoderCancelled("encoding cancelled during native work")
        if check_active is not None:
            check_active()

    active()
    return _encode_owned_cpu(
        profile,
        items,
        cached_vectors,
        model_path=profile.model if model_path is None else model_path,
        artifact_hashes=artifact_hashes,
        check_active=active,
    )
