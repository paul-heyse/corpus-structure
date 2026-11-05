"""Prepared native matchers over retained source-bound annotations.

Matches are attributed proposals, never semantic admission. Overlaps and ordered
dependency nodes survive; no exclusive ``Doc.ents`` projection is used.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from spacy.matcher import DependencyMatcher, Matcher, PhraseMatcher
from spacy.tokens import Doc
from spacy.vocab import Vocab

from corpus_structure.ingest.annotation_views import AnnotationView
from corpus_structure.ingest.annotations import AnnotationUnavailable


@dataclass(frozen=True)
class AnnotationRuleMatch:
    rule: str
    mechanism: str
    nodes: tuple[int, ...]
    extents: tuple[tuple[int, int], ...]
    piece_indices: tuple[int, ...]
    sentences: tuple[int | None, ...]
    dependency_digest: str


class PreparedAnnotationRules:
    """Compile declared patterns once per caller-owned vocabulary/recipe lifetime."""

    def __init__(
        self,
        vocab: Vocab,
        *,
        token_rules: Mapping[str, Sequence[list[dict[str, Any]]]] | None = None,
        phrase_rules: Mapping[str, Sequence[Sequence[str]]] | None = None,
        dependency_rules: Mapping[str, Sequence[list[dict[str, Any]]]] | None = None,
    ) -> None:
        self.vocab = vocab
        self.tokens = Matcher(vocab, validate=True)
        self.phrases = PhraseMatcher(vocab, attr="LOWER", validate=True)
        self.dependencies = DependencyMatcher(vocab, validate=True)
        for name, patterns in (token_rules or {}).items():
            self.tokens.add(name, list(patterns))
        for name, patterns in (phrase_rules or {}).items():
            self.phrases.add(name, [Doc(vocab, words=list(words)) for words in patterns])
        for name, patterns in (dependency_rules or {}).items():
            self.dependencies.add(name, list(patterns))

    def match(self, view: AnnotationView) -> tuple[AnnotationRuleMatch, ...]:
        view.check_layout()
        if view.doc.vocab is not self.vocab:
            raise ValueError("prepared rules and native view require the same vocabulary")
        product = view.product
        if len(self.dependencies) and not any(
            column.attribute == "DEP" and column.status == "complete"
            for column in product.availability
        ):
            raise AnnotationUnavailable(
                "dependency matching requires complete retained dependencies"
            )
        results = []

        def add(label: int, mechanism: str, nodes: tuple[int, ...]) -> None:
            rows = [product.tokens[index] for index in nodes]
            results.append(
                AnnotationRuleMatch(
                    self.vocab.strings[label],
                    mechanism,
                    nodes,
                    tuple(sorted({(row.start, row.end) for row in rows})),
                    tuple(sorted({index for row in rows for index in row.piece_indices})),
                    tuple(row.sentence for row in rows),
                    product.dependency_digest,
                )
            )

        for mechanism, matcher in (("token", self.tokens), ("phrase", self.phrases)):
            for label, start, end in matcher(view.doc):
                add(label, mechanism, tuple(range(start, end)))
        for label, indices in self.dependencies(view.doc):
            add(label, "dependency", tuple(indices))
        return tuple(results)
