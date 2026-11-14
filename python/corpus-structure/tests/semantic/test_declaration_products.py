"""Independent native UD/SRL fixture on semantic source/product references."""

import json
from hashlib import sha256
from types import SimpleNamespace

import pytest

from corpus_structure.methods.definition_declaration import _declaration_chain_from_sentences
from corpus_structure.semantic.construction_products import CharacterizationSnapshot
from corpus_structure.semantic.constructions.layers import ConstructionLayer, ConstructionSource
from corpus_structure.semantic.constructions.retained_declarations import (
    DECLARATION_FAMILY, DeclarationNotQualified, declaration_sentences_products,
    populate_declaration_products,
)
from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.declared_record_sources import DeclaredRecordSource, DeclaredSourcePin
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.source_products import source_subject
from corpus_structure.semantic.structural_products import StructuralPassage
from methods.test_definition_declaration_primary import _ROWS


def case():
    text = " ".join(row[0] for row in _ROWS)
    coordinate = {"document": "book", "document_subject": "original-document:book", "projection": sha256(text.encode()).hexdigest(), "section_pointer": "#/groups/0", "membership": "direct"}
    selectors = [{"projection": coordinate["projection"]}]
    selected = {"source": coordinate, "selectors": selectors, "text": text,
                "pieces": [{"kind": "native_text", "item_ref": "#/texts/0", "source_field": "text", "start": 0, "end": len(text)}],
                "items": [{"self_ref": "#/texts/0", "text": text, "label": "text"}], "ancestors": []}
    source = SimpleNamespace(value=selected, content=canonical_bytes(selected))
    context = SubjectContext("p", source_subject(coordinate), "book", canonical_bytes({"source": coordinate, "selectors": selectors}))
    pin = DeclaredRecordSource("book", coordinate["projection"], "#/groups/0", "direct", context, "product:source", None, "kind:source").pin()
    native_products = (SimpleNamespace(source=DeclaredSourcePin(canonical_bytes(pin).decode())),)
    canonical, hanlp, offset = [], [], 0
    for number, (sentence, words, lemmas, arcs, groups, _voices) in enumerate(_ROWS):
        sentence_id = "sentence:" + str(number)
        sentence_ref = {"product_id": "product:canonical", "member_id": sentence_id}
        references, cursor = [], offset
        for index, (word, lemma, (head, relation)) in enumerate(zip(words, lemmas, arcs, strict=True)):
            start = text.index(word, cursor)
            end, cursor = start + len(word), start + len(word)
            token_id = "token:" + str(number) + ":" + str(index)
            reference = {"product_id": "product:canonical", "member_id": token_id}
            references.append(reference)
            canonical.append({"member_id": token_id, "body": {"record_type": "token", "local_id": token_id, "start": start, "end": end}})
            hanlp.append({"member_id": "hanlp:" + token_id, "body": {"record_type": "token", "local_id": "hanlp:" + token_id, "sentence": sentence_ref, "token": reference, "ordinal": index, "lemma": lemma, "pos": "NN", "dependency_head": head, "dependency_label": relation}})
        canonical.append({"member_id": sentence_id, "body": {"record_type": "sentence", "local_id": sentence_id, "start": offset, "end": offset + len(sentence), "token_ids": [ref["member_id"] for ref in references]}})
        for index, roles in enumerate(groups):
            identifier = "srl:" + str(number) + ":" + str(index)
            hanlp.append({"member_id": identifier, "body": {"record_type": "srl_group", "local_id": identifier, "sentence": sentence_ref, "ordinal": index, "roles": [{"label": role, "start": a, "end": b, "tokens": references[a:b]} for role, a, b in roles]}})
        offset += len(sentence) + 1
    canonical = CharacterizationSnapshot("product:canonical", canonical_bytes({"source": coordinate, "selectors": selectors, "outcome": "complete", "members": canonical}))
    hanlp = CharacterizationSnapshot("product:hanlp", canonical_bytes({"source": coordinate, "selectors": selectors, "canonical": {"product_id": canonical.semantic_id}, "coverage": [{"family": "hanlp." + family, "availability": "available", "outcome": "complete", "examined": [{"projection": coordinate["projection"], "start": 0, "end": len(text)}], "unexamined": []} for family in ("tokens", "lemma", "pos", "dependency", "srl")], "members": hanlp}))
    return source, native_products, canonical, hanlp


def produce(source, native_products, canonical, hanlp):
    builder = ConstructionLayer(source.value["source"], {"selectors": source.value["selectors"]}, {"key": "text.constructions/source-native"}, semantic=True, families=(DECLARATION_FAMILY,))
    populate_declaration_products(builder, ConstructionSource.from_native(source), source, object(), canonical, hanlp, annotation_products=native_products)
    facts = builder.facts()
    return CharacterizationSnapshot("product:declarations", canonical_bytes({"source": source.value["source"], "selectors": source.value["selectors"], "coverage": facts["coverage"], "members": [{"member_id": row["local_id"], "body": {"record_type": tag, **row}} for name, tag in (("terms", "term"), ("annotations", "annotation"), ("occurrences", "occurrence")) for row in facts[name]]}))


def passage(source):
    return StructuralPassage(passage_id="definition", source_ref="semantic-source", start=0, end=len(source.value["text"]), text=source.value["text"], scope="local")


def test_declared_native_syntax_preserves_same_domain_chain_and_genuine_primary_refs():
    source, native, canonical, hanlp = case()
    product = produce(source, native, canonical, hanlp)
    sentences, evidence = declaration_sentences_products((product,), source, passage(source), supporting=(hanlp,))
    chain = _declaration_chain_from_sentences(sentences, passage(source))
    assert chain.label.text == "Definition 1" and chain.term.text == "samples"
    assert [row.frame for row in chain.bindings] and all("member:" in row.frame for row in chain.bindings)
    assert all(ref.values()["product_id"] == product.semantic_id for ref in evidence)
    assert b"source_view_id" not in product.content and b"task_id" not in product.content


def test_missing_native_premise_or_changed_canonical_association_cannot_become_empty():
    source, native, canonical, hanlp = case()
    product = produce(source, native, canonical, hanlp)
    with pytest.raises(DeclarationNotQualified, match="support is unavailable"):
        declaration_sentences_products((product,), source, passage(source), supporting=())
    body = json.loads(hanlp.content)
    body["canonical"] = {"product_id": "product:other"}
    failed = produce(source, native, canonical, CharacterizationSnapshot(hanlp.product_id, canonical_bytes(body)))
    assert all(row["outcome"] not in {"complete", "empty"} for row in json.loads(failed.content)["coverage"])
    with pytest.raises(DeclarationNotQualified):
        declaration_sentences_products((failed,), source, passage(source), supporting=(hanlp,))
