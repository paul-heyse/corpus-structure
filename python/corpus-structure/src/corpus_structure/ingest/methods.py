"""The ingest methods (ingest and math §3.6, P0-I-1b; D4 M01 to M03): `ingest.html` with its
`segment.sentences` step, and `profile.segments`, under the method contract (`core.method`).

- `ingest.html` (M01 with M03): unit document; `input_digest` the document key (project, source
  URI and the original bytes' hash); writes, through O1's `write_result`, the rendition by content
  and its build (`store_rendition`, with `parse_detail`) and `author_markup` observations.
- `profile.segments` (M02): unit rendition; `input_digest` the rendition's content digest; writes
  `segment.*` measurements.
- `segment.sentences` (M03): no units and no writes. It is a step of `ingest.html`'s task,
  registered so its named configurations resolve into `ingest.html`'s.

**`ingest.html`.** Its `Config` names a source profile (`SourceProfileRef`) and a sentence
configuration (`ConfigRef`), both resolved into its hash by the registry, so a run's configuration
is the resolved profile and sentence step. Its units are the run's corpus documents. Each original
is read from its registered path and checked against the document's content hash; the pure
`build_rendition` then gives the content, the markup drafts and the build's diagnostics. The
digest is the document key, which hashes the project, the source URI and the bytes' hash: the
markup drafts name their segments by key on this rendition, and a segment key depends on the
document key (D1 §10.1), so the output depends on all three. A document the profile does not apply
to, an original that changed, or an exception while building fails that document's task; the
other units of the batch are unaffected. A result with no markup is `empty`, and O1 writes an ingest
task with its rendition `done` either way (D3 §8).

The `author_markup` drafts carry their spans where the markup has one (a `dfn` term, a link) and
otherwise lie on the rendition; every value names its segment by key (`segment`), and a
synthesized claim's enclosing unit by key beside its locator (`unit`).

**`profile.segments`.** Its units are the run's renditions (`kb.run_rendition`); it reads the
stored content through the run's reader and returns M02's features as measurements scoped to
each segment's id and key. A measurement-only result is `empty`.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict
from sqlalchemy import text

from corpus_structure.core.canonical import canonical_json
from corpus_structure.core.evidence import segment_key
from corpus_structure.core.method import (
    ConfigRef,
    Digest,
    MethodContext,
    ObservationDraft,
    Resources,
    RunView,
    SourceProfileRef,
    UnitRef,
    UnitResult,
    UnitView,
)
from corpus_structure.core.payloads import AuthorMarkupPayload
from corpus_structure.core.vocab import (
    ConfidenceSource,
    MethodFamily,
    MethodTier,
    ObservationKind,
    ObservationOutcome,
    TaskUnitType,
)
from corpus_structure.ingest.html import IngestResult, build_rendition
from corpus_structure.ingest.profile import CompiledProfile, SourceProfile, compile_profile
from corpus_structure.ingest.profile_segments import measurements
from corpus_structure.ingest.sentences import SentenceConfig

VERSION = "1"
AUTHOR_MARKUP_VERSION = "1"


class MethodRefused(RuntimeError):
    """A method called with what it cannot use (an unresolved configuration, a direct run)."""


# --- segment.sentences ---------------------------------------------------------------------------


class SegmentSentences:
    """`segment.sentences` (M03): its configurations only; it runs inside `ingest.html`'s task."""

    name = "segment.sentences"
    version = VERSION
    family = MethodFamily.INGEST
    unit_type = TaskUnitType.RENDITION
    tier = MethodTier.DETERMINISTIC
    confidence_source: ConfidenceSource | None = None
    Config = SentenceConfig
    resources = Resources()

    def select(self, run: RunView, cfg: SentenceConfig) -> Iterable[UnitRef]:
        return ()

    def input_digest(self, unit: UnitView, cfg: SentenceConfig) -> Digest:
        raise MethodRefused("segment.sentences is a step of ingest.html's task (D4 M03)")

    def run(
        self, units: Sequence[UnitView], cfg: SentenceConfig, ctx: MethodContext
    ) -> Sequence[UnitResult]:
        raise MethodRefused("segment.sentences is a step of ingest.html's task (D4 M03)")


# --- ingest.html ---------------------------------------------------------------------------------


class IngestConfig(BaseModel):
    """`ingest.html/<name>`: a source profile and a sentence configuration, each named and
    resolved into the configuration (D2 §12.1)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_profile: Annotated[str | SourceProfile, SourceProfileRef()] = "siegrist"
    sentences: Annotated[str | SentenceConfig, ConfigRef("segment.sentences")] = (
        "segment.sentences/default"
    )

    def resolved(self) -> tuple[SourceProfile, SentenceConfig]:
        if not isinstance(self.source_profile, SourceProfile) or not isinstance(
            self.sentences, SentenceConfig
        ):
            raise MethodRefused("ingest.html runs only under a resolved configuration")
        return self.source_profile, self.sentences


def _documents(conn: Any, ids: Sequence[int]) -> dict[int, Any]:
    rows = conn.execute(
        text(
            "SELECT id, key, source_uri, content_hash, original_path FROM kb.document "
            "WHERE id = ANY(:ids)"
        ),
        {"ids": list(ids)},
    )
    return {int(r.id): r for r in rows}


class IngestHtml:
    """`ingest.html` (M01 with M03; module doc)."""

    name = "ingest.html"
    version = VERSION
    family = MethodFamily.INGEST
    unit_type = TaskUnitType.DOCUMENT
    tier = MethodTier.DETERMINISTIC
    confidence_source: ConfidenceSource | None = ConfidenceSource.AUTHOR_MARKUP
    Config = IngestConfig
    resources = Resources(worker="cpu", batch_size=4)

    def select(self, run: RunView, cfg: IngestConfig) -> Iterable[UnitRef]:
        corpus = run.options.get("corpus")
        listed = corpus.get("documents") if isinstance(corpus, dict) else None
        keys = [str(k) for k in listed] if isinstance(listed, list) else []
        with run.reader.connection() as conn:
            rows = conn.execute(
                text(
                    "SELECT d.id, d.key FROM kb.document d JOIN ops.run r ON r.project_id = "
                    "d.project_id WHERE r.id = :r AND d.key = ANY(:k) ORDER BY d.key"
                ),
                {"r": run.run_id, "k": keys},
            )
            return [UnitRef(TaskUnitType.DOCUMENT, int(r.id), str(r.key)) for r in rows]

    def input_digest(self, unit: UnitView, cfg: IngestConfig) -> Digest:
        if unit.ref.unit_key is None:
            raise MethodRefused(f"document unit {unit.ref.unit_id} carries no document key")
        return Digest(canonical_json({"document": unit.ref.unit_key}))

    def run(
        self, units: Sequence[UnitView], cfg: IngestConfig, ctx: MethodContext
    ) -> Sequence[UnitResult]:
        profile, sentences = cfg.resolved()
        compiled = compile_profile(profile)
        with ctx.reader.connection() as conn:
            documents = _documents(conn, [u.ref.unit_id for u in units if u.ref.unit_id])
        out = []
        for unit in units:
            row = documents.get(unit.ref.unit_id or -1)
            if row is None:
                out.append(_failed(unit, f"no document {unit.ref.unit_id}"))
                continue
            try:
                built = _build(row, compiled, sentences)
            except Exception as error:  # the document's task fails with the error (§3.3)
                ctx.logger.warning("ingest.html: %s: %s", row.source_uri, error)
                out.append(_failed(unit, f"{type(error).__name__}: {error}"))
                continue
            out.append(_result(unit, built))
        return out


def _build(row: Any, compiled: CompiledProfile, sentences: SentenceConfig) -> IngestResult:
    raw = Path(row.original_path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != row.content_hash:
        raise MethodRefused(f"{row.original_path} no longer holds the document's original bytes")
    return build_rendition(
        raw, compiled, sentences, source_uri=row.source_uri, document_key=row.key
    )


def _failed(unit: UnitView, error: str) -> UnitResult:
    return UnitResult(ref=unit.ref, outcome=ObservationOutcome.FAILED, error=error)


def _result(unit: UnitView, built: IngestResult) -> UnitResult:
    drafts = tuple(
        ObservationDraft(
            kind=ObservationKind.AUTHOR_MARKUP,
            payload=d.payload,
            payload_class=AuthorMarkupPayload,
            payload_version=AUTHOR_MARKUP_VERSION,
            span=d.span,
        )
        for d in built.markup
    )
    return UnitResult(
        ref=unit.ref,
        outcome=ObservationOutcome.PRODUCED if drafts else ObservationOutcome.EMPTY,
        observations=drafts,
        rendition=built.content,
        parse_detail=built.parse_detail.to_json(),
    )


# --- profile.segments ----------------------------------------------------------------------------


class ProfileSegmentsConfig(BaseModel):
    """`profile.segments/<name>`: phase 0 computes the character and math features (D4 M02)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    features: Literal["chars_math"] = "chars_math"


class ProfileSegments:
    """`profile.segments` (M02; module doc)."""

    name = "profile.segments"
    version = VERSION
    family = MethodFamily.PROFILE
    unit_type = TaskUnitType.RENDITION
    tier = MethodTier.DETERMINISTIC
    confidence_source: ConfidenceSource | None = None
    Config = ProfileSegmentsConfig
    resources = Resources(worker="cpu", batch_size=8)

    def select(self, run: RunView, cfg: ProfileSegmentsConfig) -> Iterable[UnitRef]:
        return [
            UnitRef(TaskUnitType.RENDITION, r.rendition_id, r.document_key)
            for r in run.reader.renditions()
        ]

    def input_digest(self, unit: UnitView, cfg: ProfileSegmentsConfig) -> Digest:
        with unit.run.reader.connection() as conn:
            digest = conn.execute(
                text("SELECT content_digest FROM kb.rendition WHERE id = :r"),
                {"r": unit.ref.unit_id},
            ).scalar_one()
        return Digest(canonical_json({"rendition": str(digest)}))

    def run(
        self, units: Sequence[UnitView], cfg: ProfileSegmentsConfig, ctx: MethodContext
    ) -> Sequence[UnitResult]:
        out = []
        for unit in units:
            rendition = unit.ref.unit_id
            if rendition is None:
                out.append(_failed(unit, "a rendition unit names no rendition"))
                continue
            content = ctx.reader.content(rendition)
            ids = ctx.reader.segments(rendition)
            with ctx.reader.connection() as conn:
                key = str(
                    conn.execute(
                        text("SELECT key FROM kb.rendition WHERE id = :r"), {"r": rendition}
                    ).scalar_one()
                )
            drafts = measurements(
                content, lambda s, key=key: segment_key(key, s.kind, s.start, s.end), ids
            )
            out.append(
                UnitResult(
                    ref=unit.ref, outcome=ObservationOutcome.EMPTY, measurements=tuple(drafts)
                )
            )
        return out


METHODS = (IngestHtml(), SegmentSentences(), ProfileSegments())
