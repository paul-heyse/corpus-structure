"""Shared controlled inputs and builders for scientific rule views support."""

from dataclasses import replace
from pathlib import Path

from corpus_structure.schema.rulelang import Vocabulary
from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.rule_views import RULE_VIEW_INPUT, build_rule_language
from corpus_structure.semantic.types import PreparedArtifact


def language():
    raw = (
        b"id: https://example.org/test\nname: test\n"
        b"prefixes: {ex: 'https://example.org/'}\ndefault_prefix: ex\n"
        b"types: {string: {base: str, uri: 'http://www.w3.org/2001/XMLSchema#string'}}\n"
        b"classes: {Thing: {attributes: {id: {identifier: true}}}}"
    )
    prepared = prepare_release(SourceBundle("test", (SourceArtifact("test", raw),)))
    view = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/rule-view.yaml"
    prepared = replace(
        prepared,
        artifacts=(*prepared.artifacts, PreparedArtifact(RULE_VIEW_INPUT, view.read_bytes())),
    )
    return build_rule_language(
        prepared,
        qprops={},
        builtins={},
        values={("Value", "t"): Vocabulary("kinds", frozenset({"text", "number"}))},
        arguments={},
    )
