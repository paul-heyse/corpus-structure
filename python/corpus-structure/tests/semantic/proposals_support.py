"""Shared controlled inputs and builders for proposals support."""

from functools import cache
from pathlib import Path
from typing import Any

import yaml

from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.proposals import ProposalFrame, ProposalSentence, proposal_inputs


@cache
def prepared(*, composed=True):
    path = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    domain = {
        "id": "https://example.org/domain",
        "name": "domain",
        "prefixes": {"ex": "https://example.org/"},
        "default_prefix": "ex",
        "imports": ["core"],
        "classes": {
            "Person": {
                "is_a": "Entity",
                "attributes": {"name": {"range": "string"}, "friend": {"range": "Person"}},
            },
            "Machine": {"is_a": "Entity", "attributes": {"serial": {"range": "string"}}},
        },
    }
    source = SourceBundle(
        "domain",
        (
            SourceArtifact("core", path.read_bytes()),
            SourceArtifact("domain", yaml.safe_dump(domain).encode()),
        ),
    )
    if composed:
        from corpus_structure.semantic.composed import composed_dependencies
        from corpus_structure.semantic.types import PreparationProfile, ResolvedDependencies

        return prepare_release(
            proposal_inputs(source),
            composed_dependencies(ResolvedDependencies()),
            PreparationProfile(version="semantic-2"),
        )
    return prepare_release(proposal_inputs(source))


def batch() -> dict[str, Any]:
    return {
        "unit_ref": "page#one",
        "entities": [{"id": "p", "class_iri": "https://example.org/Person", "label": "Alice"}],
        "statements": [{"id": "s", "kind": "narrative", "anchor": "page#one"}],
        "claims": [
            {
                "id": "c1",
                "subject": "p",
                "predicate": "https://example.org/name",
                "object": {"kind": "text", "text": "Alice"},
                "qualification": {"modality": "asserted", "polarity": True},
                "establishment": "stated",
                "statement": "s",
                "statement_role": "conclusion",
                "evidence": [{"sentence": "s1", "quote": "Alice is here.", "role": "primary"}],
            }
        ],
        "alternatives": [],
        "unsupported": [],
    }


def frame():
    return ProposalFrame(
        "page#one", "😀 Alice is here.", (ProposalSentence("s1", "page#sentence1", 2, 16),)
    )


def native_frame(original=None):
    """An explicitly authored native frame with the original scientific sentence spans."""
    from dataclasses import replace
    from hashlib import sha256

    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.product_reference import ProductReference
    from corpus_structure.semantic.proposals import NativeProposalFrame, native_address

    original = frame() if original is None else original
    context = dict(
        pieces=[dict(kind="native_text", item_ref="#/texts/0", start=0, end=len(original.text))],
        items=[dict(self_ref="#/texts/0")], ancestors=[], health={},
    )
    value = NativeProposalFrame(
        original.unit_ref, original.text, (), 1, ProductReference(1, "native", "a" * 64),
        "#/groups/0", "direct", sha256(canonical_bytes(context)).hexdigest(), "b" * 64,
        canonical_bytes(context).decode(),
    )
    return replace(value, sentences=tuple(
        replace(sentence, locator=native_address(value, start=sentence.start, end=sentence.end))
        for sentence in original.sentences
    ))
