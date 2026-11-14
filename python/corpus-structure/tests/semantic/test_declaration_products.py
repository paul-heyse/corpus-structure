"""Independent native UD/SRL fixture on semantic source/product references."""

import json
from hashlib import sha256
from types import SimpleNamespace

import pytest
from methods.test_definition_declaration_primary import _ROWS

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
from corpus_structure.semantic.declared_record_sources import (
    DeclaredRecordSource,
    DeclaredSourcePin,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.source_products import native_projection_identity, source_subject
from corpus_structure.semantic.structural_products import StructuralPassage


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
    canonical, hanlp, offset = [], [], 0
    for number, (sentence, words, lemmas, arcs, groups, _voices) in enumerate(_ROWS):
        sentence_id = "sentence:" + str(number)
        sentence_ref = {"product_id": "product:canonical", "member_id": sentence_id}
        references, cursor = [], offset
        for index, (word, lemma, (head, relation)) in enumerate(
            zip(words, lemmas, arcs, strict=True)
        ):
            start = text.index(word, cursor)
            end, cursor = start + len(word), start + len(word)
            token_id = "token:" + str(number) + ":" + str(index)
            reference = {"product_id": "product:canonical", "member_id": token_id}
            references.append(reference)
            canonical.append(
                {
                    "member_id": token_id,
                    "body": {
                        "record_type": "token",
                        "local_id": token_id,
                        "start": start,
                        "end": end,
                    },
                }
            )
            hanlp.append(
                {
                    "member_id": "hanlp:" + token_id,
                    "body": {
                        "record_type": "token",
                        "local_id": "hanlp:" + token_id,
                        "sentence": sentence_ref,
                        "token": reference,
                        "ordinal": index,
                        "lemma": lemma,
                        "pos": "NN",
                        "dependency_head": head,
                        "dependency_label": relation,
                    },
                }
            )
        canonical.append(
            {
                "member_id": sentence_id,
                "body": {
                    "record_type": "sentence",
                    "local_id": sentence_id,
                    "start": offset,
                    "end": offset + len(sentence),
                    "token_ids": [ref["member_id"] for ref in references],
                },
            }
        )
        for index, roles in enumerate(groups):
            identifier = "srl:" + str(number) + ":" + str(index)
            hanlp.append(
                {
                    "member_id": identifier,
                    "body": {
                        "record_type": "srl_group",
                        "local_id": identifier,
                        "sentence": sentence_ref,
                        "ordinal": index,
                        "roles": [
                            {"label": role, "start": a, "end": b, "tokens": references[a:b]}
                            for role, a, b in roles
                        ],
                    },
                }
            )
        offset += len(sentence) + 1
    canonical = CharacterizationSnapshot(
        "product:canonical",
        canonical_bytes(
            {
                "source": coordinate,
                "selectors": selectors,
                "outcome": "complete",
                "members": canonical,
            }
        ),
    )
    hanlp = CharacterizationSnapshot(
        "product:hanlp",
        canonical_bytes(
            {
                "source": coordinate,
                "selectors": selectors,
                "canonical": {"product_id": canonical.semantic_id},
                "coverage": [
                    {
                        "family": "hanlp." + family,
                        "availability": "available",
                        "outcome": "complete",
                        "examined": [
                            {"projection": coordinate["projection"], "start": 0, "end": len(text)}
                        ],
                        "unexamined": [],
                    }
                    for family in ("tokens", "lemma", "pos", "dependency", "srl")
                ],
                "members": hanlp,
            }
        ),
    )
    return source, native_products, canonical, hanlp


def produce(source, native_products, canonical, hanlp):
    builder = ConstructionLayer(
        source.value["source"],
        {"selectors": source.value["selectors"]},
        {"key": "text.constructions/source-native"},
        semantic=True,
        families=(DECLARATION_FAMILY,),
    )
    from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource

    frame = DeclaredNativeFrameSource(
        source.content.decode(), canonical_bytes(native_products[0].source.values()).decode()
    )
    populate_declaration_products(
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
    sentences, evidence = declaration_sentences_products(
        (product,), source, passage(source), supporting=(hanlp,)
    )
    chain = _declaration_chain_from_sentences(sentences, passage(source))
    assert chain.label.text == "Definition 1" and chain.term.text == "samples"
    assert [row.frame for row in chain.bindings] and all(
        "member:" in row.frame for row in chain.bindings
    )
    assert all(ref.values()["product_id"] == product.semantic_id for ref in evidence)
    assert b"source_view_id" not in product.content and b"task_id" not in product.content


def test_missing_native_premise_or_changed_canonical_association_cannot_become_empty():
    source, native, canonical, hanlp = case()
    product = produce(source, native, canonical, hanlp)
    with pytest.raises(DeclarationNotQualified, match="support is unavailable"):
        declaration_sentences_products((product,), source, passage(source), supporting=())
    body = json.loads(hanlp.content)
    body["canonical"] = {"product_id": "product:other"}
    failed = produce(
        source, native, canonical, CharacterizationSnapshot(hanlp.product_id, canonical_bytes(body))
    )
    assert all(
        row["outcome"] not in {"complete", "empty"}
        for row in json.loads(failed.content)["coverage"]
    )
    with pytest.raises(DeclarationNotQualified):
        declaration_sentences_products((failed,), source, passage(source), supporting=(hanlp,))


def test_target_definition_component_retains_semantic_witness_and_independent_domain_result():
    source, native, canonical, hanlp = case()
    product = produce(source, native, canonical, hanlp)
    component = primary_declaration_component_products(
        (product,),
        source,
        passage(source),
        supporting=(hanlp,),
        source_pin=native[0].source.values(),
    )
    assert component.term.text == "samples" and component.basis == "declaration_chain"
    assert component.declaration_chain is not None
    witness = component.declaration_chain.model_dump(mode="json")
    assert witness["primary_evidence"] and all(
        reference["product_id"] == product.semantic_id and reference["member_id"]
        for reference in witness["primary_evidence"]
    )
    assert "parser" not in witness and "task_id" not in canonical_bytes(witness).decode()


def applicability_case():
    from corpus_structure.semantic.contextual_links import RelationshipDecision, RelationshipEdge
    from corpus_structure.semantic.contextual_operations import ContextualRelationshipBinding
    from corpus_structure.semantic.contextual_retrieval import (
        SemanticTargetGroup,
        target_representation,
    )
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
    from corpus_structure.semantic.structural_admission import structural_statement
    from corpus_structure.semantic.structural_products import (
        DeclaredDefinitionComponentsProduct,
        DeclaredDefinitionComponentsReport,
        DeclaredStructuralInput,
        DeclaredStructuralInputPin,
    )

    source, native, canonical, hanlp = case()
    product = produce(source, native, canonical, hanlp)
    frame = DeclaredNativeFrameSource(
        source.content.decode(), canonical_bytes(native[0].source.values()).decode()
    )
    source_ref = DeclaredStructuralSource.model_validate(frame.pin.values())
    target_passage = passage(source).model_copy(update={"source_ref": source_ref.identity})
    component = primary_declaration_component_products(
        (product,), source, target_passage, supporting=(hanlp,), source_pin=frame.pin.values()
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
    )
    inputs = DeclaredStructuralInput(
        question="Read local definition",
        scope="local",
        inventory_id="selected",
        policy_id="retained-declaration-chain-v2",
        sources=(source_ref,),
        passages=(target_passage,),
        dependencies=(product.semantic_id, hanlp.semantic_id),
    )
    report = DeclaredDefinitionComponentsReport(
        inputs=inputs,
        definition_components=DeclaredDefinitionComponentsProduct(
            components=(component,), stages=()
        ),
        sources_input=(source_pin,),
    )
    context = {
        key: getattr(source_pin, key)
        for key in (
            "kind_contract",
            "project_id",
            "subject",
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
    target = target_representation(
        component.component_id,
        canonical_bytes(component_ref.model_dump(mode="json", exclude_none=True)).decode(),
        component.term.text,
        component.content.text,
        type_name="definition",
        scope=component.scope,
    )
    meaning = structural_statement(report, component.component_id)["definition_component"]
    group = SemanticTargetGroup("semantic-target:selected", (component.component_id,), meaning)
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
    assert introduced.component_ref == component and introduced.link_ref == relationship
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
