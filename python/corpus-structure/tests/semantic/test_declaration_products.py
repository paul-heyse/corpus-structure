"""Controlled literal UD/SRL facts on current source and semantic member references."""

import json
from hashlib import sha256
from types import SimpleNamespace
from typing import Any

import pytest

from corpus_structure.methods.definition_declaration import (
    _declaration_chain_from_sentences,
    primary_declaration_component_products,
)
from corpus_structure.semantic.construction_products import CharacterizationSnapshot
from corpus_structure.semantic.constructions.layers import ConstructionLayer, ConstructionSource
from corpus_structure.semantic.constructions.retained_declarations import (
    DECLARATION_FAMILY,
    DeclarationNotQualified,
    declaration_sentences_products,
    populate_declaration_products,
)
from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.data_operation_partitions import partition_header
from corpus_structure.semantic.data_product_reference import (
    SemanticReference,
    read_semantic_reference,
)
from corpus_structure.semantic.declared_record_sources import (
    DeclaredRecordSource,
    DeclaredSourcePin,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.sentence_partitions import SentenceBlock, blocks_from_packets
from corpus_structure.semantic.source_products import native_projection_identity, source_subject
from corpus_structure.semantic.structural_products import StructuralPassage
from semantic.definition_component_members_support import unadmitted_component_members

# Each native UD/SRL fact is authored independently of the consumer's checks.
_ROWS = (
    (
        "Definition 1 Let X be a set.",
        ("Definition", "1", "Let", "X", "be", "a", "set", "."),
        ("definition", "1", "let", "X", "be", "a", "set", "."),
        (
            (0, "root"),
            (1, "nummod"),
            (1, "dep"),
            (7, "nsubj"),
            (7, "cop"),
            (7, "det"),
            (3, "ccomp"),
            (1, "punct"),
        ),
        ((("PRED", 4, 5), ("ARG1", 3, 4), ("ARG2", 5, 7)),),
        {4: "copular"},
    ),
    (
        "Let Y be a set that contains elements from the set of X.",
        (
            "Let",
            "Y",
            "be",
            "a",
            "set",
            "that",
            "contains",
            "elements",
            "from",
            "the",
            "set",
            "of",
            "X",
            ".",
        ),
        (
            "let",
            "Y",
            "be",
            "a",
            "set",
            "that",
            "contain",
            "element",
            "from",
            "the",
            "set",
            "of",
            "X",
            ".",
        ),
        (
            (0, "root"),
            (5, "nsubj"),
            (5, "cop"),
            (5, "det"),
            (1, "ccomp"),
            (7, "nsubj"),
            (5, "acl:relcl"),
            (7, "obj"),
            (11, "case"),
            (11, "det"),
            (7, "obl"),
            (13, "case"),
            (11, "nmod"),
            (1, "punct"),
        ),
        (
            (("PRED", 2, 3), ("ARG1", 1, 2), ("ARG2", 3, 13)),
            (("PRED", 6, 7), ("ARG0", 5, 6), ("ARG1", 7, 8)),
        ),
        {2: "copular", 6: "active"},
    ),
    (
        "The elements of Y are called samples.",
        ("The", "elements", "of", "Y", "are", "called", "samples", "."),
        ("the", "element", "of", "Y", "be", "call", "sample", "."),
        (
            (2, "det"),
            (6, "nsubj:pass"),
            (4, "case"),
            (2, "nmod"),
            (6, "aux:pass"),
            (0, "root"),
            (6, "xcomp"),
            (6, "punct"),
        ),
        ((("PRED", 5, 6), ("ARG1", 0, 4), ("ARG2", 6, 7)),),
        {5: "passive"},
    ),
)


def case():
    text = " ".join(row[0] for row in _ROWS)
    coordinate = {
        "document": "book",
        "document_subject": "original-document:book",
        "projection": sha256(text.encode()).hexdigest(),
        "section_pointer": "#/groups/0",
        "membership": "direct",
    }
    selectors = [{"projection": coordinate["projection"]}]
    selected = {
        "source": coordinate,
        "selectors": selectors,
        "text": text,
        "pieces": [
            {
                "kind": "native_text",
                "item_ref": "#/texts/0",
                "source_field": "text",
                "start": 0,
                "end": len(text),
            }
        ],
        "items": [{"self_ref": "#/texts/0", "text": text, "label": "text"}],
        "ancestors": [],
    }
    coordinate["projection"] = native_projection_identity(
        text, selected["pieces"], selected["items"]
    )
    selectors[0]["projection"] = coordinate["projection"]
    source = SimpleNamespace(value=selected, content=canonical_bytes(selected))
    context = SubjectContext(
        "p",
        source_subject(coordinate),
        "book",
        canonical_bytes({"source": coordinate, "selectors": selectors}),
        subject_definition="original-source-view",
    )
    pin = DeclaredRecordSource(
        "book",
        coordinate["projection"],
        "#/groups/0",
        "direct",
        context,
        "product:source",
        None,
        "kind:source",
    ).pin()
    native_products = (SimpleNamespace(source=DeclaredSourcePin(canonical_bytes(pin).decode())),)
    canonical_rows: list[dict[str, Any]] = []
    hanlp_rows: list[dict[str, Any]] = []
    block_id, extent = "#/texts/0", len(text)
    offset = token_ordinal = 0
    for number, (sentence, words, lemmas, arcs, groups, _voices) in enumerate(_ROWS):
        sentence_ref = SemanticReference.item(
            "canonical", "rows", block_id, ("sentence", number)
        ).values()
        references, cursor = [], offset
        for index, (word, lemma, (head, relation)) in enumerate(
            zip(words, lemmas, arcs, strict=True)
        ):
            start = text.index(word, cursor)
            end = cursor = start + len(word)
            reference = SemanticReference.item(
                "canonical", "rows", block_id, ("token", token_ordinal)
            ).values()
            references.append(reference)
            canonical_rows.append(
                dict(
                    record_type="token",
                    ordinal=token_ordinal,
                    start=start,
                    end=end,
                    extent=extent,
                    sentence=number,
                )
            )
            hanlp_rows.append(
                dict(
                    record_type="token",
                    sentence=sentence_ref,
                    token=reference,
                    ordinal=index,
                    sentence_ordinal=number,
                    lemma=lemma,
                    pos="NN",
                    dependency_head=head,
                    dependency_label=relation,
                )
            )
            token_ordinal += 1
        canonical_rows.append(
            dict(
                record_type="sentence",
                ordinal=number,
                start=offset,
                end=offset + len(sentence),
                extent=extent,
            )
        )
        for index, roles in enumerate(groups):
            hanlp_rows.append(
                dict(
                    record_type="srl_group",
                    sentence=sentence_ref,
                    ordinal=index,
                    sentence_ordinal=number,
                    roles=[
                        dict(label=role, start=a, end=b, tokens=references[a:b])
                        for role, a, b in roles
                    ],
                )
            )
        offset += len(sentence) + 1
    canonical = partitioned_snapshot(
        "product:canonical",
        dict(source=coordinate, selectors=selectors, outcome="complete"),
        block_id,
        extent,
        sorted(canonical_rows, key=lambda row: (row["record_type"], row["ordinal"])),
    )
    hanlp = partitioned_snapshot(
        "product:hanlp",
        dict(
            source=coordinate,
            selectors=selectors,
            canonical_input=SemanticReference.whole("canonical").values(),
            coverage=[
                dict(
                    family="hanlp." + family,
                    availability="available",
                    outcome="complete",
                    examined=[dict(projection=coordinate["projection"], start=0, end=extent)],
                    unexamined=[],
                )
                for family in ("tokens", "lemma", "pos", "dependency", "srl")
            ],
        ),
        block_id,
        extent,
        sorted(
            hanlp_rows,
            key=lambda row: (row["sentence_ordinal"], row["record_type"], row["ordinal"]),
        ),
    )
    return source, native_products, canonical, hanlp


def partitioned_snapshot(product_id, header, block, extent, rows):
    packet = SentenceBlock(block, 0, 0, extent, tuple(rows)).packet()
    return CharacterizationSnapshot(
        product_id,
        canonical_bytes(dict(header, rows=partition_header((packet,)))),
        (canonical_bytes(packet),),
    )


def produce(source, native_products, canonical, hanlp):
    builder = ConstructionLayer(
        source.value["source"],
        {"selectors": source.value["selectors"]},
        {"key": "text.constructions/source-native"},
        families=(DECLARATION_FAMILY,),
    )
    from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource

    frame = DeclaredNativeFrameSource.from_retained_record(
        source.content.decode(), canonical_bytes(native_products[0].source.values()).decode()
    )
    term_support = populate_declaration_products(
        builder,
        ConstructionSource.from_native(source),
        source,
        None,
        canonical,
        hanlp,
        source_frame=frame,
    )
    facts = builder.facts()
    return CharacterizationSnapshot(
        "product:declarations",
        canonical_bytes(
            {
                "source": source.value["source"],
                "selectors": source.value["selectors"],
                "coverage": facts["coverage"],
                "term_support": term_support,
                "members": [
                    {"member_id": row["local_id"], "body": {"record_type": tag, **row}}
                    for name, tag in (
                        ("terms", "term"),
                        ("annotations", "annotation"),
                        ("occurrences", "occurrence"),
                    )
                    for row in facts[name]
                ],
            }
        ),
    )


def passage(source):
    return StructuralPassage(
        passage_id="definition",
        source_ref="semantic-source",
        start=0,
        end=len(source.value["text"]),
        text=source.value["text"],
        scope="local",
    )


def test_declared_native_syntax_preserves_same_domain_chain_and_genuine_primary_refs():
    source, native, canonical, hanlp = case()
    product = produce(source, native, canonical, hanlp)
    sentences, evidence = declaration_sentences_products((product,), source, passage(source))
    chain = _declaration_chain_from_sentences(sentences, passage(source))
    assert chain.label.text == "Definition 1" and chain.term.text == "samples"
    assert {row.frame for row in chain.bindings} <= {
        sentence.reference.member_id for sentence in sentences
    }
    assert all(ref.values()["product_id"] == product.semantic_id for ref in evidence)
    supports = json.loads(product.content)["term_support"]
    assert len(supports) == 3
    for index, row in enumerate(supports):
        references = tuple(map(read_semantic_reference, row["references"]))
        assert all(
            ref.role == "hanlp"
            and ref.partition_key == "#/texts/0"
            and ref.item_key is not None
            and ref.item_key[0] == index
            for ref in references
        )
    assert b"source_view_id" not in product.content and b"task_id" not in product.content


def test_missing_native_premise_or_changed_canonical_association_cannot_become_empty():
    source, native, canonical, hanlp = case()
    product = produce(source, native, canonical, hanlp)
    body = json.loads(product.content)
    body["term_support"] = []
    unsupported = CharacterizationSnapshot(product.product_id, canonical_bytes(body))
    with pytest.raises(DeclarationNotQualified, match="support is unavailable"):
        declaration_sentences_products((unsupported,), source, passage(source))
    body = json.loads(hanlp.content)
    body["canonical_input"] = SemanticReference.whole("other").values()
    failed = produce(
        source,
        native,
        canonical,
        CharacterizationSnapshot(hanlp.product_id, canonical_bytes(body), hanlp.partitions),
    )
    assert all(
        row["outcome"] not in {"complete", "empty"}
        for row in json.loads(failed.content)["coverage"]
    )
    with pytest.raises(DeclarationNotQualified):
        declaration_sentences_products((failed,), source, passage(source))


def test_target_definition_component_retains_semantic_witness_and_independent_domain_result(
    monkeypatch,
):
    source, native, canonical, hanlp = case()
    product = produce(source, native, canonical, hanlp)
    import corpus_structure.semantic.constructions.retained_declarations as declaration_owner

    monkeypatch.setattr(
        declaration_owner,
        "_declared_sentences",
        lambda *_a, **_k: pytest.fail("consumer reran native syntax projection"),
    )
    monkeypatch.setattr(
        declaration_owner,
        "_facts",
        lambda *_a, **_k: pytest.fail("consumer recognized declaration syntax"),
    )
    component, evidence = primary_declaration_component_products(
        (product,),
        source,
        passage(source),
        source_pin=native[0].source.values(),
    )
    assert component.term.text == "samples" and component.basis == "declaration_chain"
    assert component.declaration_chain is not None
    witness = component.declaration_chain.model_dump(mode="json")
    assert "primary_evidence" not in witness
    assert evidence and all(
        reference.product.product_id == product.semantic_id for reference in evidence
    )
    assert "parser" not in witness and "task_id" not in canonical_bytes(witness).decode()
    assert component.content.text == (
        "Let X be a set. Let Y be a set that contains elements from the set of X. The elements of Y"
    )
    assert witness["version"] == "definition-declaration-chain-3"
    assert witness["naming_frame"] in {reference.member_id for reference in evidence}
    assert len(witness["bindings"]) == 1
    assert witness["bindings"][0]["subject_token"] == 3
    assert witness["bindings"][0]["use_token"] == 12


def applicability_case():
    from corpus_structure.semantic.contextual_links import RelationshipDecision, RelationshipEdge
    from corpus_structure.semantic.contextual_operations import ContextualRelationshipBinding
    from corpus_structure.semantic.contextual_retrieval import (
        semantic_target_groups,
    )
    from corpus_structure.semantic.contextual_target_products import component_target_values
    from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource
    from corpus_structure.semantic.declared_structural_references import (
        DeclaredComponentRef,
        DeclaredRelationshipRef,
        DeclaredStructuralSource,
    )
    from corpus_structure.semantic.source_contexts import (
        NativeSourceContext,
        PreparedNativeSources,
        evidence_anchor,
        source_slice,
    )
    from corpus_structure.semantic.structural_products import (
        DeclaredDefinitionComponentsProduct,
        DeclaredDefinitionComponentsReport,
        DeclaredStructuralInput,
        DeclaredStructuralInputPin,
    )

    source, native, canonical, hanlp = case()
    product = produce(source, native, canonical, hanlp)
    frame = DeclaredNativeFrameSource.from_retained_record(
        source.content.decode(), canonical_bytes(native[0].source.values()).decode()
    )
    source_ref = DeclaredStructuralSource.model_validate(frame.pin.values())
    target_passage = passage(source).model_copy(update={"source_ref": source_ref.identity})
    component, _evidence = primary_declaration_component_products(
        (product,), source, target_passage, source_pin=frame.pin.values()
    )
    source_pin = DeclaredStructuralInputPin(
        product_id=source_ref.source_product,
        member_id=source_ref.source_member,
        reference=source_ref.source,
        kind_contract=source_ref.kind_contract,
        project_id=source_ref.project_id,
        subject=source_ref.subject,
        original_source=source_ref.original_source,
        analyzed_scope_meaning=source_ref.analyzed_scope_meaning,
        subject_definition="original-source-view",
    )
    inputs = DeclaredStructuralInput(
        question="Read local definition",
        scope="local",
        inventory_id="selected",
        policy_id="retained-declaration-chain-v2",
        sources=(source_ref,),
        passages=(target_passage,),
        dependencies=(product.semantic_id,),
    )
    report = DeclaredDefinitionComponentsReport(
        inputs=inputs,
        members=unadmitted_component_members((component,)),
        definition_components=DeclaredDefinitionComponentsProduct(stages=()),
    )
    context = {
        key: getattr(source_pin, key)
        for key in (
            "kind_contract",
            "project_id",
            "subject",
            "subject_definition",
            "original_source",
            "analyzed_scope_meaning",
        )
    }
    component_ref = DeclaredComponentRef(
        product_id="product:component-report",
        structural_id=report.product_id,
        component_id=component.component_id,
        **context,
    )
    relationship_ref = DeclaredRelationshipRef(
        product_id="product:relationship", edge_id="edge:selected", **context
    )
    usage = target_passage.model_copy(
        update={
            "passage_id": "usage",
            "start": component.term.start,
            "end": component.term.end,
            "text": component.term.text,
        }
    )
    inputs = inputs.model_copy(update={"passages": (*inputs.passages, usage)})
    native_context = NativeSourceContext(
        frame,
        (),
        (source_slice(frame, usage.start, usage.end),),
        "usage",
        "fixture",
        "exact",
        max_chars=len(usage.text),
        max_pieces=256,
        max_sources=1,
        version=2,
        preparation=PreparedNativeSources((frame,), max_sources=1),
    )
    anchors = tuple(
        evidence_anchor(native_context, piece, native=True)[0]
        for piece in native_context.map_span(
            0, len(usage.text), literal=usage.text, allow_multiple=True
        )
    )
    target, meaning = component_target_values(
        report, component, original_source=component_ref.original_source
    )
    (group,) = semantic_target_groups((target,), {component.component_id: meaning})
    edge = RelationshipEdge(
        "edge:selected",
        "definition",
        "occurrence:usage",
        group.target_id,
        (component.component_id,),
        "defined-by",
        (),
        "forced",
    )
    decision = RelationshipDecision(
        "decision:selected",
        "candidates:usage",
        "occurrence:usage",
        "local",
        None,
        "introduction",
        "exclusions:none",
        "selected",
        (),
        (),
        (edge,),
        (),
        (),
        None,
        None,
        frame.pin.values()["source"],
        (),
    )
    binding = ContextualRelationshipBinding(
        decision, edge, group, (target,), frame.pin.values(), anchors
    )
    return inputs, report, component_ref, relationship_ref, binding, frame


def test_declared_applicability_preserves_unknown_transfer_and_explicit_introduction():
    from corpus_structure.semantic.definition_applicability_products import (
        selected_definition_applicability,
    )

    inputs, report, component, relationship, binding, frame = applicability_case()
    contextual = selected_definition_applicability(
        inputs, "usage", report, component, relationship, binding, usage_frame=frame
    )
    assert contextual.outcome == "unresolved"
    assert {row.dimension for row in contextual.premises if row.state == "unknown"} == {
        "parent",
        "parameterization",
        "convention",
    }
    introduced = selected_definition_applicability(
        inputs,
        "usage",
        report,
        component,
        relationship,
        binding,
        usage_frame=frame,
        defining_occurrence=True,
    )
    assert introduced.outcome == "applicable_definition"
    assert introduced.component_ref == {
        "variant": "member",
        "role": "components",
        "member_id": component.component_id,
    }
    assert introduced.link_ref == {
        "variant": "member",
        "role": "relationship",
        "member_id": relationship.edge_id,
    }
    assert all(row.state in {"compatible", "inapplicable"} for row in introduced.premises)


@pytest.mark.parametrize("change", ["carrier", "meaning", "usage", "edge"])
def test_declared_applicability_refuses_carrier_meaning_usage_or_edge_substitution(change):
    from dataclasses import replace

    from corpus_structure.semantic.definition_applicability_products import (
        selected_definition_applicability,
    )

    inputs, report, component, relationship, binding, frame = applicability_case()
    if change == "carrier":
        from corpus_structure.semantic.contextual_retrieval import target_representation

        actual = binding.representations[0]
        foreign = target_representation(
            actual.target_id,
            "another actual carrier",
            actual.label,
            actual.description,
            type_name="definition",
            scope=actual.scope,
        )
        binding = replace(binding, representations=(foreign,))
    elif change == "meaning":
        binding = replace(
            binding,
            target=replace(
                binding.target, meaning={**binding.target.meaning, "interpretation": "explanation"}
            ),
        )
    elif change == "usage":
        binding = replace(binding, anchors=())
    else:
        relationship = relationship.model_copy(update={"edge_id": "edge:other"})
    with pytest.raises(
        ValueError, match=r"component reference|meaning|physical occurrence|relationship edge"
    ):
        selected_definition_applicability(
            inputs, "usage", report, component, relationship, binding, usage_frame=frame
        )


@pytest.mark.parametrize(
    "failure", ["missing_declaration", "clipped_sentence", "changed_source", "unexamined"]
)
def test_current_declaration_reader_refuses_missing_or_substituted_semantic_scope(failure):
    source, native, canonical, hanlp = case()
    product = produce(source, native, canonical, hanlp)
    products, selected = (product,), passage(source)
    if failure == "missing_declaration":
        products = ()
    elif failure == "clipped_sentence":
        selected = selected.model_copy(update=dict(start=1, text=selected.text[1:]))
    else:
        body = json.loads(product.content)
        if failure == "changed_source":
            body["source"]["document"] = "another-book"
        else:
            body["coverage"][0]["unexamined"] = [
                dict(projection=source.value["source"]["projection"], start=0, end=1)
            ]
        products = (CharacterizationSnapshot(product.product_id, canonical_bytes(body)),)
    with pytest.raises(DeclarationNotQualified):
        declaration_sentences_products(products, source, selected)


@pytest.mark.parametrize("corruption", ["missing_column", "srl_support"])
def test_current_declaration_syntax_failure_preserves_healthy_siblings(corruption):
    source, native, canonical, hanlp = case()
    assert hanlp.partitions is not None
    (block,) = blocks_from_packets(tuple(json.loads(packet) for packet in hanlp.partitions))
    if corruption == "missing_column":
        token = next(row for row in block.rows if row["record_type"] == "token")
        assert isinstance(token, dict)
        del token["lemma"]
    else:
        group = next(row for row in block.rows if row["record_type"] == "srl_group")
        group["roles"][0]["tokens"] = []
    changed = partitioned_snapshot(
        hanlp.product_id, json.loads(hanlp.content), block.key, block.end, block.rows
    )
    product = produce(source, native, canonical, changed)
    facts = product.inventory()
    roots = [term for term in facts["terms"] if term["value"] == "declaration_sentence"]
    assert len(roots) == 2
    (coverage,) = [
        row
        for row in json.loads(product.content)["coverage"]
        if row["family"] == DECLARATION_FAMILY
    ]
    assert coverage["outcome"] == "partial"
    assert len(coverage["examined"]) == 2 and len(coverage["unexamined"]) == 1
    with pytest.raises(DeclarationNotQualified):
        declaration_sentences_products((product,), source, passage(source))


def test_current_healthy_chain_survives_unselected_malformed_sentence(monkeypatch):
    import sys

    selected_text = " ".join(row[0] for row in _ROWS)
    monkeypatch.setattr(sys.modules[__name__], "_ROWS", (*_ROWS, _ROWS[0]))
    source, native, canonical, hanlp = case()
    assert hanlp.partitions is not None
    (block,) = blocks_from_packets(tuple(json.loads(packet) for packet in hanlp.partitions))
    token = next(
        row for row in block.rows if row["record_type"] == "token" and row["sentence_ordinal"] == 3
    )
    assert isinstance(token, dict)
    del token["lemma"]
    changed = partitioned_snapshot(
        hanlp.product_id, json.loads(hanlp.content), block.key, block.end, block.rows
    )
    product = produce(source, native, canonical, changed)
    selected = passage(source).model_copy(update=dict(text=selected_text, end=len(selected_text)))
    component, _evidence = primary_declaration_component_products(
        (product,), source, selected, source_pin=native[0].source.values()
    )
    assert component.term.text == "samples"
    assert component.declaration_chain is not None
