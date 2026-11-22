"""Bounded real-book projections for provider mechanisms, without DDO admission claims.

HTML paragraph/table text is an explicitly authored projection of retained originals.
The unadmitted frame references carry coordinates only: no native selected proof,
source registration, publication, assessment or historical runtime is manufactured.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import cache
from hashlib import sha256
from html.parser import HTMLParser
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource
    from corpus_structure.semantic.model_characterization import ModelScope
    from corpus_structure.semantic.source_products import FrozenNativeSource

ROOT = Path(__file__).resolve().parents[4]
BOOK = ROOT / "docs/statistics_corpus/corpus/siegrist_random/random"
QWEN_SNAPSHOT = (
    Path.home()
    / ".cache/huggingface/hub/models--Qwen--Qwen3-Embedding-0.6B/snapshots/97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3"
)
SOURCES = (
    ("foundations/Sets.html", "p", "In contrast to a universal set", "empty set"),
    ("foundations/Functions.html", "p", "A function", "function"),
    ("special/Normal.html", "p", "The normal distribution holds", "Gaussian distribution"),
    ("foundations/Structures.html", "table", "Sampling formulas", "Sampling formulas"),
)


class _Excerpts(HTMLParser):
    def __init__(self, tag):
        super().__init__(convert_charrefs=True)
        self.tag = tag
        self.depth = 0
        self.parts: list[str] = []
        self.rows: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == self.tag:
            if self.depth == 0:
                self.parts = []
            self.depth += 1
        if self.depth and tag in {"p", "tr", "td", "th", "br"}:
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if self.depth and tag in {"p", "tr", "td", "th"}:
            self.parts.append(" ")
        if tag == self.tag and self.depth:
            self.depth -= 1
            if self.depth == 0:
                self.rows.append(re.sub(r"\s+", " ", "".join(self.parts)).strip())

    def handle_data(self, data):
        if self.depth:
            self.parts.append(data)


def missing_snapshot(directory, required):
    directory = Path(directory)
    paths = {directory / name for name in required}
    missing = []
    for path in sorted(paths):
        if not path.is_file():
            missing.append(f"provider panel requires {path}")
        else:
            with path.open("rb") as stream:
                if stream.readline(128).strip() == b"version https://git-lfs.github.com/spec/v1":
                    missing.append(f"provider panel requires Git LFS hydration of {path}")
    return "; ".join(missing) if missing else None


def missing_qwen_snapshot():
    return missing_snapshot(
        QWEN_SNAPSHOT,
        (
            "config.json",
            "modules.json",
            "model.safetensors",
            "tokenizer.json",
            "1_Pooling/config.json",
        ),
    )


def missing_gliner_snapshot():
    import json

    selected = json.loads((ROOT / "domains/statistics/profiles/gliner.json").read_bytes())
    return missing_snapshot(selected["assets"], tuple(selected["profile"]["artifacts"]))


def missing_book_panel():
    return missing_snapshot(BOOK, tuple(row[0] for row in SOURCES))


@cache
def panel_release():
    from methods.record_assembly_support import bundle

    from corpus_structure.methods import model_observation
    from corpus_structure.semantic.interpretation_questions import (
        characterization_question_dependencies,
    )
    from corpus_structure.semantic.prepare import prepare_release
    from corpus_structure.semantic.types import ResolvedDependencies, SourceArtifact

    dependencies = characterization_question_dependencies(
        ResolvedDependencies(
            (
                SourceArtifact(
                    model_observation.DECLARED_MODEL_OBSERVATION_INPUT,
                    Path(model_observation.__file__)
                    .with_name("model_observation.json")
                    .read_bytes(),
                ),
            )
        )
    )
    return prepare_release(bundle(), dependencies)


@dataclass(frozen=True)
class BookProjection:
    path: str
    original_digest: str
    selector: str
    literal: str
    native: FrozenNativeSource
    frame: DeclaredNativeFrameSource
    scope: ModelScope


def book_panel(prepared):
    from corpus_structure.semantic.data_operation_model import SubjectContext
    from corpus_structure.semantic.declared_record_sources import (
        DeclaredNativeFrameSource,
        DeclaredRecordSource,
    )
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.model_characterization import prepare_model_scope
    from corpus_structure.semantic.source_products import FrozenNativeSource, source_subject

    result = []
    for relative, tag, prefix, literal in SOURCES:
        path = BOOK / relative
        original = path.read_bytes()
        parser = _Excerpts(tag)
        parser.feed(original.decode())
        matches = [
            (index, text) for index, text in enumerate(parser.rows) if text.startswith(prefix)
        ]
        assert len(matches) == 1, (relative, prefix, matches)
        index, text = matches[0]
        assert literal in text
        pointer = f"#/{tag}/{index}"
        digest = sha256(original).hexdigest()
        native = FrozenNativeSource.from_projection(
            prepared,
            document=path.as_uri(),
            section_pointer=pointer,
            membership="direct",
            text=text,
            pieces=[
                dict(
                    kind="native_text",
                    item_ref=pointer,
                    source_field="text",
                    start=0,
                    end=len(text),
                )
            ],
            items=[dict(self_ref=pointer, label="text", text=text)],
        )
        coordinate = native.value["source"]
        context = SubjectContext(
            "unadmitted:provider-book-panel",
            source_subject(coordinate),
            path.as_uri(),
            canonical_bytes(dict(source=coordinate, selectors=native.value["selectors"])),
            subject_definition="original-source-view",
        )
        pin = DeclaredRecordSource(
            coordinate["document"],
            coordinate["projection"],
            pointer,
            "direct",
            context,
            "unadmitted:book-projection:" + sha256(native.content).hexdigest(),
            None,
            "unadmitted:native-source-kind",
        ).pin()
        frame = DeclaredNativeFrameSource.from_retained_record(
            canonical_bytes(native.value).decode(), canonical_bytes(pin).decode()
        )
        scope = prepare_model_scope(frame, (0, len(text)), (0, len(text)))
        result.append(BookProjection(relative, digest, pointer, literal, native, frame, scope))
    return tuple(result)


def encoder_items(panel):
    from corpus_structure.methods.contextual_embeddings import ContextInput
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.source_products import source_subject

    items = []
    for projection in panel[:3]:
        text = projection.native.value["text"]
        start = text.index(projection.literal)
        for role in ("query", "document"):
            items.append(
                ContextInput(
                    f"book-panel:{projection.path}:{projection.selector}:{role}",
                    source_subject(projection.native.value["source"]),
                    role,
                    projection.literal,
                    text,
                    start,
                    start + len(projection.literal),
                    representation_digest=sha256(
                        canonical_bytes(
                            [projection.original_digest, projection.selector, role, text]
                        )
                    ).hexdigest(),
                )
            )
    return tuple(items)
