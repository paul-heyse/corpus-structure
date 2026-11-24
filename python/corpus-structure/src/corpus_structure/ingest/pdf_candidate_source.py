"""Finite, source-qualified candidate pages with explicit Arrow and hydration reads.

The spool owner retains files through its last borrower. Batches own their immutable IPC
buffers, so a selected result remains usable after its reader and source have closed.
"""

from __future__ import annotations

from collections.abc import Collection, Iterable, Iterator, Mapping, Sequence
from typing import Any, Protocol, cast

import pyarrow as pa

from corpus_structure.semantic.pdf_payloads import (
    EncodedPagePayload,
    PreparedPayloadFamily,
    _from_arrow,
    prepare_payload_family,
    prepare_payload_schema,
    schema_dump,
    schema_load,
)

from .pdf_candidates import CandidatePage, InlineCandidate
from .pdf_stream_types import PdfReplayRef


class CandidatePageSource(Protocol):
    @property
    def payload_family(self) -> PreparedPayloadFamily: ...

    @property
    def page_nos(self) -> tuple[int, ...]: ...

    def iter_batches(
        self, page_nos: Collection[int] | None = None, columns: Sequence[str] | None = None
    ) -> Iterator[pa.RecordBatch]: ...

    def iter_pages(self, page_nos: Collection[int] | None = None) -> Iterator[CandidatePage]: ...

    def encoded(self, page_no: int) -> EncodedPagePayload: ...


def _replay_payload(replay: PdfReplayRef) -> EncodedPagePayload:
    if (
        replay.family != "candidate_payload"
        or replay.page_no is None
        or replay.schema_digest is None
        or replay.logical_digest is None
    ):
        raise ValueError("candidate replay lacks its released payload binding")
    return EncodedPagePayload(
        replay.read_bytes(), replay.schema_digest, replay.logical_digest, replay.page_no
    )


def _read_replay(
    replay: PdfReplayRef, family: PreparedPayloadFamily
) -> tuple[EncodedPagePayload, pa.RecordBatch]:
    encoded = _replay_payload(replay)
    batch = family.read_batch(
        encoded.content, schema_digest=encoded.schema_digest, logical_digest=encoded.logical_digest
    )
    if batch.column("page_no")[0].as_py() != replay.page_no:
        raise ValueError("candidate replay page binding differs")
    return encoded, batch


def encoded_replay(replay: PdfReplayRef, family: PreparedPayloadFamily) -> EncodedPagePayload:
    """Verify exact custody and released schema without reconstructing page mappings."""
    return _read_replay(replay, family)[0]


def candidate_from_payload(
    row: Mapping[str, Any], family: PreparedPayloadFamily | None = None
) -> InlineCandidate:
    """Hydrate one selected candidate using the codec's presence/numeric interpretation."""
    family = family or prepare_payload_family()
    schema = family.json_schema["properties"]["candidates"]["items"]
    value = _from_arrow(dict(row), schema, family.json_schema, "#/candidates/*")
    if not isinstance(value, dict):
        raise ValueError("selected candidate payload requires an object")
    return InlineCandidate.from_wire(value)


def _page(value: dict[str, Any]) -> CandidatePage:
    value["candidates"] = tuple(
        InlineCandidate.from_wire(row) for row in value.get("candidates", ())
    )
    value["ocr_regions"] = tuple(value.get("ocr_regions", ()))
    return CandidatePage(**value)


class ReplayCandidatePageSource:
    def __init__(
        self,
        replays: Mapping[int, PdfReplayRef],
        payload_family: PreparedPayloadFamily | None = None,
    ) -> None:
        self.replays = dict(replays)
        self.payload_family = payload_family or prepare_payload_family()
        self._admitted: dict[int, PdfReplayRef] = {}

    def __getstate__(self) -> dict[str, Any]:
        # Validators/registries hold local callables. Transfer only the admitted schema
        # and owned replay locators; the receiving DB-free child prepares its own codec.
        return {"replays": self.replays, "schema": schema_dump(self.payload_family.json_schema)}

    def __setstate__(self, state: dict[str, Any]) -> None:
        self.replays = state["replays"]
        self.payload_family = prepare_payload_schema(schema_load(state["schema"]))
        self._admitted = {}

    @property
    def page_nos(self) -> tuple[int, ...]:
        return tuple(sorted(self.replays))

    def encoded(self, page_no: int) -> EncodedPagePayload:
        replay, value = self._acquire(page_no)
        if self._admitted.get(page_no) != replay:
            self._admit(replay, value)
        return value

    def _acquire(self, page_no: int) -> tuple[PdfReplayRef, EncodedPagePayload]:
        replay = self.replays[page_no]
        encoded = _replay_payload(replay)
        if encoded.page_no != page_no:
            raise ValueError("candidate source page binding differs")
        return replay, encoded

    def _admit(self, replay: PdfReplayRef, encoded: EncodedPagePayload) -> pa.RecordBatch:
        batch = self.payload_family.read_batch(
            encoded.content,
            schema_digest=encoded.schema_digest,
            logical_digest=encoded.logical_digest,
        )
        if batch.column("page_no")[0].as_py() != encoded.page_no:
            raise ValueError("candidate replay page binding differs")
        self._admitted[encoded.page_no] = replay
        return batch

    def iter_batches(self, page_nos=None, columns=None) -> Iterator[pa.RecordBatch]:
        if columns is not None and (
            not columns
            or len(set(columns)) != len(columns)
            or set(columns) - set(self.payload_family.arrow_schema.names)
        ):
            raise ValueError("candidate projection requires distinct released columns")
        for number in self.page_nos:
            if page_nos is not None and number not in page_nos:
                continue
            replay, encoded = self._acquire(number)
            if self._admitted.get(number) != replay:
                batch = self._admit(replay, encoded)
            else:
                physical = columns
                if columns is not None and "page_no" not in columns:
                    physical = (*columns, "page_no")
                batch = self.payload_family.read_batch(
                    encoded.content, schema_digest=encoded.schema_digest, columns=physical
                )
                if batch.column("page_no")[0].as_py() != number:
                    raise ValueError("candidate replay page binding differs")
            yield batch.select(columns) if columns is not None else batch

    def iter_pages(self, page_nos=None) -> Iterator[CandidatePage]:
        for batch in self.iter_batches(page_nos):
            yield _page(self.payload_family.decode_batch(batch))


class InMemoryCandidatePageSource:
    def __init__(
        self, pages: Iterable[CandidatePage], payload_family: PreparedPayloadFamily | None = None
    ) -> None:
        self.pages = {page.page_no: page for page in pages}
        self._payload_family = payload_family

    def __getstate__(self) -> dict[str, Any]:
        return {
            "pages": self.pages,
            "schema": (
                schema_dump(self._payload_family.json_schema)
                if self._payload_family is not None
                else None
            ),
        }

    def __setstate__(self, state: dict[str, Any]) -> None:
        self.pages = state["pages"]
        self._payload_family = (
            prepare_payload_schema(schema_load(state["schema"]))
            if state["schema"] is not None
            else None
        )

    @property
    def payload_family(self) -> PreparedPayloadFamily:
        if self._payload_family is None:
            self._payload_family = prepare_payload_family()
        return self._payload_family

    @property
    def page_nos(self) -> tuple[int, ...]:
        return tuple(sorted(self.pages))

    def encoded(self, page_no: int) -> EncodedPagePayload:
        return self.payload_family.encode_page(self.pages[page_no].to_wire())

    def iter_batches(self, page_nos=None, columns=None) -> Iterator[pa.RecordBatch]:
        for page in self.iter_pages(page_nos):
            batch = self.payload_family.batch(page.to_wire())
            yield batch.select(columns) if columns is not None else batch

    def iter_pages(self, page_nos=None) -> Iterator[CandidatePage]:
        for number in self.page_nos:
            if page_nos is None or number in page_nos:
                yield self.pages[number]


class OverlayCandidatePageSource:
    """Keep unchanged pages borrowed; rediscovery replaces only its selected pages."""

    def __init__(self, base: CandidatePageSource, overrides: Mapping[int, CandidatePage]) -> None:
        self.base = base
        self.overrides = InMemoryCandidatePageSource(overrides.values(), base.payload_family)
        self.payload_family = base.payload_family

    def __getstate__(self) -> dict[str, Any]:
        return {"base": self.base, "overrides": self.overrides}

    def __setstate__(self, state: dict[str, Any]) -> None:
        self.base = state["base"]
        self.overrides = state["overrides"]
        self.payload_family = self.base.payload_family

    @property
    def page_nos(self) -> tuple[int, ...]:
        return tuple(sorted(set(self.base.page_nos) | set(self.overrides.page_nos)))

    def _source(self, number: int) -> CandidatePageSource:
        return self.overrides if number in self.overrides.pages else self.base

    def encoded(self, page_no: int) -> EncodedPagePayload:
        return self._source(page_no).encoded(page_no)

    def iter_batches(self, page_nos=None, columns=None) -> Iterator[pa.RecordBatch]:
        for number in self.page_nos:
            if page_nos is None or number in page_nos:
                yield from self._source(number).iter_batches((number,), columns)

    def iter_pages(self, page_nos=None) -> Iterator[CandidatePage]:
        for number in self.page_nos:
            if page_nos is None or number in page_nos:
                yield from self._source(number).iter_pages((number,))


def as_candidate_source(
    value: CandidatePageSource | Iterable[CandidatePage],
) -> CandidatePageSource:
    if hasattr(value, "iter_batches") and hasattr(value, "iter_pages"):
        return cast(CandidatePageSource, value)
    return InMemoryCandidatePageSource(cast(Iterable[CandidatePage], value))
