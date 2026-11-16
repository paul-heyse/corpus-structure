"""Literal unadmitted source/column inputs through the current nominal producers.

These pure fixtures create no execution episode, native receipt or admission standing.
Consumers receive the actual annotation and construction products explicitly.
"""

from dataclasses import asdict
from functools import lru_cache
from hashlib import sha256
from pathlib import Path

from spacy.lang.en import English

from corpus_structure.ingest.annotation_views import annotation_view
from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.composed import data_operation_dependencies
from corpus_structure.semantic.construction_products import (
    PreparedConstructionProfile,
    construction_product_inputs,
)
from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.declared_record_sources import (
    DeclaredNativeFrameSource,
    DeclaredRecordSource,
)
from corpus_structure.semantic.formal_evidence import grammar_identity
from corpus_structure.semantic.formal_products import (
    FormalEvidenceOptions,
    formal_operation_sources,
    prepare_formal_evidence,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.sentence_products import (
    _blocks,
    source_annotation_packets,
    spacy_family_coverage,
    validate_source_annotations,
)
from corpus_structure.semantic.source_products import FrozenNativeSource, source_subject
from corpus_structure.semantic.types import PreparationProfile, ResolvedDependencies


@lru_cache(maxsize=1)
def profiles():
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    bundle = construction_product_inputs(
        SourceBundle("core", (SourceArtifact("core", core.read_bytes()),))
    )
    prepared = prepare_release(
        bundle,
        data_operation_dependencies(
            ResolvedDependencies(), python_sources=formal_operation_sources()
        ),
        PreparationProfile(version="semantic-2"),
    )
    model = bound_data_operation_model(prepared)
    return prepare_formal_evidence(
        prepared, model, grammar=grammar_identity()
    ), PreparedConstructionProfile(prepared, model)


def selected_source(text, *, pieces=None, items=None, recognition=()):
    formal, _construction = profiles()
    pieces = (
        pieces
        if pieces is not None
        else [
            dict(
                kind="native_text",
                start=0,
                end=len(text),
                item_ref="#/texts/0",
                source_field="text",
            )
        ]
    )
    items = (
        items
        if items is not None
        else [dict(self_ref="#/texts/0", label="text", text=text, orig=text)]
    )
    source = FrozenNativeSource.from_projection(
        formal.prepared,
        document="unadmitted:literal-document",
        section_pointer="#/body",
        membership="descendants",
        text=text,
        pieces=pieces,
        items=items,
        recognition=recognition,
    )
    coordinate = source.value["source"]
    context = SubjectContext(
        "unadmitted:project",
        source_subject(coordinate),
        coordinate["document"],
        canonical_bytes(dict(source=coordinate, selectors=source.value["selectors"])),
        subject_definition="original-source-view",
    )
    address = DeclaredRecordSource(
        coordinate["document"],
        coordinate["projection"],
        coordinate["section_pointer"],
        coordinate["membership"],
        context,
        "unadmitted:source:" + sha256(source.content).hexdigest(),
        "unadmitted:source-member",
        "unadmitted:original-source-kind",
    )
    frame = DeclaredNativeFrameSource(
        source.content.decode(), canonical_bytes(address.pin()).decode()
    )
    return source, frame, context


def retained_products(source, frame, context, products, profile):
    """Validate literal columns and execute the genuine formal/construction kernels."""
    from corpus_structure.ingest.annotations import AnnotationProduct

    formal, construction = profiles()
    products = (products,) if isinstance(products, AnnotationProduct) else tuple(products)

    def present(value):
        if isinstance(value, dict):
            return {key: present(item) for key, item in value.items() if item is not None}
        if isinstance(value, (tuple, list)):
            return [present(item) for item in value]
        return value

    records, availability = [], []
    for product in products:
        if product.source != frame.pin:
            raise ValueError("fixture annotation differs from the selected source carrier")
        view = annotation_view(
            product,
            frame.text[product.block_start : product.block_end],
            English().vocab,
            required=(),
        )
        body = present(asdict(product))
        body["source"] = frame.pin.values()
        body["display_spans"] = [dict(start=start, end=end) for start, end in product.display_spans]
        lexemes = [
            dict(
                lower=token.lower_,
                is_alpha=token.is_alpha,
                is_space=token.is_space,
                is_punct=token.is_punct,
                is_quote=token.is_quote,
                like_num=token.like_num,
                sent_start=token.is_sent_start,
            )
            for token in view.doc
        ]
        first = product.native_pieces[0]
        offset = next(
            index
            for index, piece in enumerate(source.value["pieces"])
            if piece["start"] == first.start
            and piece["end"] == first.end
            and piece.get("item_ref") == first.item_ref
        )
        records.append(dict(annotation=body, lexemes=lexemes, piece_offset=offset))
        availability.append(
            dict(
                block_id=product.block_id,
                start=product.block_start,
                end=product.block_end,
                attributes={column.attribute: column.status for column in product.availability},
            )
        )
    _population, coverage = _blocks(source)
    value = dict(
        source=source.value["source"],
        selectors=source.value["selectors"],
        configuration=profile.configuration.model_dump(mode="json"),
        execution_profile=profile.execution_profile,
        block_coverage=coverage,
        coverage=spacy_family_coverage(source.value, coverage, availability),
        blocks=records,
    )
    value["outcome"] = (
        "complete"
        if all(row["outcome"] in {"complete", "empty"} for row in value["coverage"])
        else "partial"
    )
    value["members"] = source_annotation_packets(construction.prepared, construction.model, value)
    native = validate_source_annotations(
        construction.prepared,
        construction.model,
        value,
        source,
        configuration=profile.configuration,
        subject_context=context,
    )
    primary = formal.run(source, FormalEvidenceOptions(), subject_context=context)
    return native, construction.run(source, (primary,), sentences=native, subject_context=context)


def source_readings(text, profile, *, heading=None, change=None):
    """Use the selected annotation producer, without an old Reader or layer restoration."""
    from dataclasses import replace

    from corpus_structure.ingest.annotations import annotate
    from corpus_structure.ingest.sentences import pipeline
    from corpus_structure.methods.source_preparation import annotation_inputs
    from corpus_structure.semantic.m1_products import NativeCandidateData

    body = text
    items = [
        dict(self_ref="#/groups/1", label="section"),
        dict(
            self_ref="#/texts/1", label="text", text=body, orig=body, parent={"$ref": "#/groups/1"}
        ),
    ]
    offset = 0
    pieces = []
    if heading is not None:
        offset = len(heading) + 1
        text = heading + "\n" + text
        items.insert(
            1,
            dict(
                self_ref="#/texts/0",
                label="section_header",
                text=heading,
                orig=heading,
                parent={"$ref": "#/groups/1"},
            ),
        )
        pieces.extend(
            [
                dict(
                    kind="native_text",
                    start=0,
                    end=len(heading),
                    item_ref="#/texts/0",
                    source_field="text",
                ),
                dict(kind="synthetic_separator", start=len(heading), end=offset),
            ]
        )
    pieces.append(
        dict(
            kind="native_text",
            start=offset,
            end=len(text),
            item_ref="#/texts/1",
            source_field="text",
        )
    )
    source, frame, context = selected_source(text, pieces=pieces, items=items)
    native_profile = pipeline(profile.configuration).selection().native
    profile = replace(profile, execution_profile=native_profile.fingerprint)
    products = tuple(
        annotate(
            annotation_inputs(
                NativeCandidateData.from_frame(frame), profile=profile, source_frame=frame
            ),
            profile,
        )
    )
    if change is not None:
        products = tuple(change(product) for product in products)
    native, primary = retained_products(source, frame, context, products, profile)
    return frame, products, (primary,), native
