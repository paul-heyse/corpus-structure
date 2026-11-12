"""Detached native annotation in the existing database-free CPU pool."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, TypeAdapter

from corpus_structure.core.work import PreparedWork
from corpus_structure.ingest.annotations import (
    AnnotationAvailability,
    AnnotationInput,
    AnnotationProduct,
    AnnotationProfile,
    AnnotationUnavailable,
    annotate,
)
from corpus_structure.ingest.sentences import SentenceConfigError

from .identity import canonical_bytes


class _AnnotationPacket(BaseModel):
    model_config = ConfigDict(extra="forbid")
    method: Literal["private.spacy_annotations"]
    request_id: str
    release_id: str
    claims: tuple[tuple[int, int, str], ...]
    inputs: tuple[AnnotationInput, ...]
    profile: AnnotationProfile
    require_complete: bool


@dataclass(frozen=True)
class AnnotationBatch:
    products: tuple[AnnotationProduct, ...] = ()
    unavailable_type: str | None = None
    message: str | None = None
    missing_components: tuple[str, ...] = ()
    availability: tuple[AnnotationAvailability, ...] = ()

    def require_available(self):
        if self.unavailable_type == "AnnotationUnavailable":
            raise AnnotationUnavailable(
                self.message or "native annotation unavailable",
                missing_components=self.missing_components,
                availability=self.availability,
            )
        if self.unavailable_type is not None:
            raise SentenceConfigError(self.message or "native annotation profile unavailable")
        return self.products


_BATCH = TypeAdapter(AnnotationBatch)


def compute_annotations(content: bytes, check_active: Callable[[], None]) -> bytes:
    packet = _AnnotationPacket.model_validate_json(content)
    from .cpu_execution import _WORKER_RELEASES

    if packet.release_id not in _WORKER_RELEASES:
        raise ValueError("annotation packet differs from initialized release")

    def checked_inputs():
        for item in packet.inputs:
            check_active()
            yield item

    products = []
    try:
        for product in annotate(
            checked_inputs(), packet.profile, require_complete=packet.require_complete
        ):
            check_active()
            products.append(product)
        result = AnnotationBatch(tuple(products))
    except AnnotationUnavailable as error:
        result = AnnotationBatch(
            tuple(products),
            "AnnotationUnavailable",
            str(error),
            error.missing_components,
            error.availability,
        )
    except (SentenceConfigError, OSError) as error:
        result = AnnotationBatch(tuple(products), type(error).__name__, str(error))
    check_active()
    return canonical_bytes(asdict(result))


def decode_annotation_reply(reply) -> AnnotationBatch:
    return _BATCH.validate_json(reply.content, strict=True, extra="forbid")


class _AnnotationHandle:
    def __init__(self, handle):
        self._handle = handle
        self.future = handle.future
        self._result = None

    def collect(self) -> AnnotationBatch:
        if self._result is None:
            self._result = decode_annotation_reply(self._handle.collect())
        return self._result

    def cancel(self) -> None:
        self._handle.cancel()

    def retire(self) -> bool:
        return self._handle.retire()


def annotation_work(
    execution,
    inputs: tuple[AnnotationInput, ...],
    profile: AnnotationProfile,
    check_active: Callable[[], None],
    *,
    require_complete: bool = False,
):
    """Only owned dataclass values cross spawn; Language.pipe stays n_process=1."""

    def try_submit():
        permit = execution.try_admit(check_active)
        if permit is None:
            return None
        try:
            content = canonical_bytes(
                dict(
                    method="private.spacy_annotations",
                    request_id=uuid4().hex,
                    release_id=execution.prepared.release_id,
                    claims=tuple(getattr(check_active, "active", ())),
                    inputs=[asdict(item) for item in inputs],
                    profile=profile.identity(),
                    require_complete=require_complete,
                )
            )
            return _AnnotationHandle(execution.submit(permit, content, {}, check_active))
        except BaseException:
            if not permit.submitted:
                execution.release_admission(permit)
            raise

    return PreparedWork(try_submit)
