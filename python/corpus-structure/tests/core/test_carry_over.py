"""Q-6 as unit tests (foundations §3.6; ADR-0023 T8): carry-over completeness and scheme stability.

- Carry-over from scheme 1 to a synthetic scheme 2 over the `fixtures/s0` batches is complete: the
  batches are parsed onto their production renditions (A0's `parse`), carried into candidate sets
  by T2's declaration, and keyed under both schemes. Every scheme 1 key maps to exactly one scheme 2
  key, and no two scheme 1 keys map to one: no key is ambiguous.
- Conformance vector v1 keys alike in two processes with different `PYTHONHASHSEED`s, so no key
  depends on string hashing or set order.

Scheme 2 here is synthetic, a key-derivation change of the kind a scheme moves for: a
statement's first-sentence ordinal counts from 0, not 1. That is a bijection within each anchor, so
every statement key and every key that names a statement move without merging, and the map must
carry each of them.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any
from unittest import mock

import pytest

from corpus_structure.core import keys as keys_module
from corpus_structure.core import tex
from corpus_structure.core.batch import AuthoredBatch, CitationFrame
from corpus_structure.core.candidates import KeyedCandidateSet
from corpus_structure.core.evidence import content_digest, document_key, rendition_key
from corpus_structure.core.keys import (
    KeyContext,
    Keys,
    KeySchema,
    LabelRules,
    carry_over,
    key_claims,
)
from corpus_structure.ingest.html import build_rendition
from corpus_structure.ingest.profile import compile_profile, load_profile
from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.methods.llm.parse import RenditionView, parse
from corpus_structure.schema.lookup import build_lookup, compile_key_schema, name_map
from corpus_structure.schema.pack import load_pack

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
S0 = REPO / "fixtures/s0"
CORPUS = REPO / "fixtures/trace/corpus/siegrist_random/random"
ROOT = "siegrist_random/random"
RULES = LabelRules()


def _load(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


candidate_set = _load("translate").candidate_set


@pytest.fixture(scope="module")
def pack() -> tuple[KeySchema, dict[str, str]]:
    packs = [load_pack(REPO / "domains/statistics")]
    return compile_key_schema(build_lookup(packs), 1), dict(name_map(packs).to_prefixed)


@pytest.fixture(scope="module")
def inputs(pack) -> list[tuple[str, KeyedCandidateSet, KeyContext]]:
    """Every s0 batch on its production rendition, as a keyed candidate set and its context."""
    _, names = pack
    profile = compile_profile(load_profile("siegrist"))
    contexts: dict[str, tuple[RenditionView, KeyContext]] = {}
    out = []
    for path in sorted(S0.glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        page = raw["provenance"]["rendition"]["page"]
        if page not in contexts:
            body = (CORPUS / page).read_bytes()
            uri = f"{ROOT}/{page}"
            content = build_rendition(body, profile, SentenceConfig(), source_uri=uri).content
            doc = document_key("statistics", uri, hashlib.sha256(body).hexdigest())
            macros = tex.effective_macros(content.macros, {})
            view = RenditionView(content, page, rendition_key(doc, content_digest(content)), macros)
            contexts[page] = (view, KeyContext(doc, content, page, macros))
        view, ctx = contexts[page]
        parsed = parse(view, AuthoredBatch.model_validate(raw["batch"]),
                       CitationFrame.model_validate(raw["frame"]), names)  # fmt: skip
        out.append((path.stem, candidate_set(parsed.stored), ctx))
    return out


def scheme_2_anchor(statement: Any, ctx: KeyContext) -> tuple[Any, int]:
    """Scheme 2's statement anchor: scheme 1's, with the ordinal counted from 0."""
    anchor, ordinal = SCHEME_1_ANCHOR(statement, ctx)
    return anchor, ordinal - 1


SCHEME_1_ANCHOR = keys_module.statement_anchor


def keyer(schema: KeySchema, anchor: Any = None):
    """A scheme's key function over a candidate set and its context."""

    def key(cands: KeyedCandidateSet, ctx: KeyContext) -> Keys:
        if anchor is None:
            return key_claims(cands, ctx, schema, RULES)
        with mock.patch.object(keys_module, "statement_anchor", anchor):
            return key_claims(cands, ctx, schema, RULES)

    return key


def all_keys(keys: Keys) -> list[str]:
    return [*keys.entities.values(), *keys.statements.values(), *keys.references.values(),
            *keys.claims.values()]  # fmt: skip


def test_carry_over_from_scheme_1_to_2_over_the_s0_batches_is_complete(pack, inputs) -> None:
    one, _ = pack
    old_keyer = keyer(one)
    new_keyer = keyer(one.model_copy(update={"key_scheme": 2}), scheme_2_anchor)
    assert len(inputs) == 13
    old = {name: old_keyer(c, x) for name, c, x in inputs}
    new = {name: new_keyer(c, x) for name, c, x in inputs}
    old_keys = {k for keys in old.values() for k in all_keys(keys)}
    assert len(old_keys) > 100  # the batches key, not just parse
    moved = old_keys - {k for keys in new.values() for k in all_keys(keys)}
    assert moved, "scheme 2 must move some keys, or the map is trivially complete"
    for name in old:  # both schemes drop the same items
        assert old[name].dropped.keys() == new[name].dropped.keys(), name
    result = carry_over(old_keys, [(c, x) for _, c, x in inputs], old_keyer, new_keyer)
    assert (result.from_scheme, result.to_scheme) == (1, 2)
    assert result.missing == frozenset()  # every old key maps
    assert result.split == {}  # no old key maps to two new keys
    assert set(result.mapping) == old_keys
    assert len(set(result.mapping.values())) == len(result.mapping)  # nor two old keys to one


SCRIPT = """
import importlib.util, json, sys
spec = importlib.util.spec_from_file_location("conformance", sys.argv[1])
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
keys = m.key_claims(m.candidates(), m.CTX, m.SCHEMA, m.RULES)
print(json.dumps({"entities": keys.entities, "statements": keys.statements,
                  "references": keys.references, "claims": keys.claims}, sort_keys=True))
"""


def keys_in_a_process(seed: str) -> dict[str, dict[str, str]]:
    env = {**os.environ, "PYTHONHASHSEED": seed}
    out = subprocess.run(
        [sys.executable, "-c", SCRIPT, str(HERE / "test_conformance.py")],
        capture_output=True, text=True, check=True, env=env, cwd=HERE,
    )  # fmt: skip
    return json.loads(out.stdout)


def test_vector_v1_keys_alike_under_different_hash_seeds() -> None:
    first, second = keys_in_a_process("0"), keys_in_a_process("1234567")
    assert first == second
    vector = _load("test_conformance")
    assert first["claims"] == vector.CLM  # and both are the hand-written answers
    assert first["references"] == {"xr": vector.XRF}
