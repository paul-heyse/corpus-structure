"""Independently supplied current structural addresses and literal native projections.

These pure fixtures establish no native publication or admission standing.
"""

from corpus_structure.semantic.data_operation_model import json_context_meaning
from corpus_structure.semantic.declared_structural_references import DeclaredStructuralSource
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.original_documents import original_document_subject
from corpus_structure.semantic.source_products import native_projection_identity, source_subject
from corpus_structure.semantic.structural_products import DeclaredStructuralInput, StructuralPassage


def _native_value(document, passages):
    text, pieces, items = "", [], []
    for passage in sorted(passages, key=lambda row: (row["start"], row["passage_id"])):
        start, literal = passage["start"], passage["text"]
        if start < len(text):
            raise ValueError("literal fixture passages overlap within one original")
        if start > len(text):
            pieces.append(dict(kind="synthetic_separator", start=len(text), end=start))
            text += " " * (start - len(text))
        pointer = "#/texts/" + passage["passage_id"]
        pieces.append(
            dict(
                kind="native_text",
                item_ref=pointer,
                source_field="text",
                start=start,
                end=start + len(literal),
            )
        )
        items.append(dict(self_ref=pointer, label="text", text=literal))
        text += literal
    projection = native_projection_identity(text, pieces, items)
    coordinate = dict(
        document=document,
        document_subject=original_document_subject(document),
        section_pointer="#/groups/0",
        membership="descendants",
        projection=projection,
    )
    return dict(
        source=coordinate,
        text=text,
        pieces=pieces,
        items=items,
        ancestors=[],
        recognition=[],
        selectors=[dict(projection=projection, start=0, end=len(text))],
    )


def input_from_passages(passages, *, question="compare source clauses", scope="scope"):
    """Construct pins from the literal original inputs before invoking any producer."""
    grouped = {}
    for passage in passages:
        grouped.setdefault(passage["document"], []).append(passage)
    sources, references = [], {}
    for document, rows in grouped.items():
        native = _native_value(document, rows)
        coordinate = native["source"]
        product = "fixture:native-source:" + document
        address = DeclaredStructuralSource(
            source=canonical_bytes([product, None]).decode(),
            source_product=product,
            kind_contract="kind:fixture-native-source",
            subject=source_subject(coordinate),
            subject_definition="original-source-view",
            document=document,
            original_source=document,
            projection_digest=coordinate["projection"],
            section_pointer=coordinate["section_pointer"],
            membership="descendants",
            project_id=document,
            analyzed_scope_meaning=json_context_meaning(
                canonical_bytes(dict(source=coordinate, selectors=native["selectors"]))
            ).decode(),
        )
        sources.append(address)
        references[document] = address.identity
    return DeclaredStructuralInput(
        question=question,
        scope=scope,
        inventory_id="inventory",
        policy_id="literal-fields-1",
        sources=tuple(sources),
        passages=tuple(
            StructuralPassage(
                passage_id=row["passage_id"],
                source_ref=references[row["document"]],
                start=row["start"],
                end=row["start"] + len(row["text"]),
                text=row["text"],
                scope=row.get("scope", scope),
                effective_version=row.get("effective_version"),
                parent=row.get("parent"),
            )
            for row in passages
        ),
        dependencies=("input-policy:1", "component-product"),
    )


def inputs(left="hello", right="world", *, starts=(0, 10), scope="scope"):
    return input_from_passages(
        (
            dict(passage_id="a", document="book-a", text=left, start=starts[0]),
            dict(passage_id="b", document="book-b", text=right, start=starts[1]),
        ),
        scope=scope,
    )


def native_source(prepared, value, source):
    from corpus_structure.semantic.source_products import FrozenNativeSource

    passages = [
        dict(passage_id=row.passage_id, start=row.start, text=row.text)
        for row in value.passages
        if row.source_ref == source.identity
    ]
    native = _native_value(source.document, passages)
    if canonical_bytes(native["source"]) != source.coordinate:
        raise ValueError("literal fixture passages differ from their current source projection pin")
    return FrozenNativeSource.acquire(prepared, native)


def root_references(value):
    """Supplied qualified pure inputs, without native admission or issuer standing."""
    from corpus_structure.semantic.declared_structural_references import (
        DeclaredComponentRef,
        DeclaredStructuralRef,
    )

    source = value.sources[0]
    header = dict(
        product_id="fixture:definition-product",
        kind_contract="kind:fixture-definition",
        project_id=source.project_id,
        subject=source.subject,
        subject_definition=source.subject_definition,
        original_source=source.original_source,
        analyzed_scope_meaning=source.analyzed_scope_meaning,
        structural_id="fixture:definition-report",
    )
    return DeclaredComponentRef(**header, component_id="1" * 64), DeclaredStructuralRef(**header)
