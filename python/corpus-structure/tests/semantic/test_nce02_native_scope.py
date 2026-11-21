"""Current predicate scope: literal scientific controls and genuine native source products.

Controlled columns below carry no native/provider standing. The two publication
journeys execute the actual sentence/construction/predicate producers and project
only their exact returned products; retired run/LayerReport SQL is not exercised.
"""

from dataclasses import replace

import pytest

from corpus_structure.ingest import annotations
from corpus_structure.ingest.annotations import AnnotationProfile
from corpus_structure.methods.predicate_contributions import declared_predicate_evidence
from corpus_structure.methods.predicate_frames import predicate_frames
from corpus_structure.semantic.declared_record_sources import (
    DeclaredNativeFrameSource,
    DeclaredRecordSource,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.source_contexts import (
    NativeSourceContext,
    PreparedNativeSources,
    source_slice,
)
from corpus_structure.semantic.structural_products import StructuralPassage
from semantic.current_pdf_source_support import (
    current_pdf_source_factory as current_pdf_source_factory,
)


def passage(spelling, start=0, end=None):
    end = len(spelling) if end is None else end
    return StructuralPassage(
        passage_id="scope",
        scope="scope",
        source_ref="fixture",
        start=start,
        end=end,
        text=spelling[start:end],
    )


def authored_product(monkeypatch, spelling, columns):
    """Native lexical positions with independent POS/dependency/lemma expectations."""
    from annotation_support import ControlledPipeline, item
    from methods.declared_primary_fixture import retained_products, selected_source

    from corpus_structure.ingest.pdf_hierarchy import ProjectedPiece

    controlled = ControlledPipeline()
    monkeypatch.setattr(annotations, "pipeline", lambda _: controlled)
    source, frame, context = selected_source(spelling)
    profile = AnnotationProfile(execution_profile=controlled.selection().native.fingerprint)
    selected = replace(
        item(
            controlled,
            spelling,
            start=0,
            block_id="#/texts/0",
            pieces=(
                ProjectedPiece("#/texts/0", 0, len(spelling), "native_text", source_field="text"),
            ),
        ),
        source=frame.pin,
    )
    (product,) = annotations.annotate((selected,), profile)
    assert len(product.tokens) == len(columns)
    product = replace(
        product,
        tokens=tuple(
            replace(token, pos=pos, dependency=dep, head=head, lemma=lemma)
            for token, (pos, dep, head, lemma) in zip(product.tokens, columns, strict=True)
        ),
    )
    _native, primary = retained_products(source, frame, context, product, profile)
    return product, primary


def actual_basis(kernel, original, products):
    """Restore only authenticated current products returned by the native selected read."""
    from corpus_structure.semantic.construction_products import CharacterizationSnapshot
    from corpus_structure.semantic.demand_results import CutSelection, selected_record_index
    from corpus_structure.semantic.sentence_products import (
        retained_source_annotation_products,
        validate_source_annotations,
    )
    from corpus_structure.semantic.source_products import FrozenNativeSource
    from semantic.structural_production_native_support import selected_for_source

    source = FrozenNativeSource.acquire(kernel.prepared, original.body)
    coordinate = source.value["source"]
    address = DeclaredRecordSource(
        coordinate["document"],
        coordinate["projection"],
        coordinate["section_pointer"],
        coordinate["membership"],
        original.context,
        original.row["product_id"],
        original.row["member_id"],
        original.row["kind_contract"],
    )
    frame = DeclaredNativeFrameSource(
        canonical_bytes(original.body).decode(), canonical_bytes(address.pin()).decode()
    )
    (sentences,) = selected_for_source(
        kernel,
        products,
        "https://corpus-structure.dev/semantic/data-operation-sentences/DdoSourceAnnotations",
        original,
    )
    read = sentences.read
    cut = CutSelection(read.cut_canonical_json.encode())
    with (
        kernel.purpose("read").begin() as connection,
        selected_record_index(
            connection,
            read.demand_id,
            project_id=read.project_id,
            read_id=read.read_id,
            expected_cut=read.cut_id,
            scope=cut.record["scope"],
        ) as (_, index),
    ):
        partitions = tuple(
            canonical_bytes(row)
            for row in index.rows_for(
                "kb.data_product_partition",
                product_id=sentences.row["product_id"],
                collection="rows",
            )
        )
    native = validate_source_annotations(
        kernel.prepared,
        kernel.model,
        sentences.body,
        source,
        subject_context=sentences.context,
        partitions=partitions,
    )
    assert native.semantic_id == sentences.row["product_id"]
    (construction,) = selected_for_source(
        kernel,
        products,
        "https://corpus-structure.dev/semantic/data-operation-constructions/DdoPrimaryConstructionProduct",
        original,
    )
    primary = CharacterizationSnapshot(
        construction.row["product_id"], canonical_bytes(construction.body)
    )
    return frame, retained_source_annotation_products(source, native), (primary,)


def scoped_evidence(frame, products, primary, start=0, end=None):
    end = len(frame.text) if end is None else end
    context = NativeSourceContext(
        frame,
        (),
        (source_slice(frame, start, end),),
        "exact native cut",
        "retained-primary-source-readings-v1",
        "selected original",
        version=2,
        preparation=PreparedNativeSources((frame,), max_sources=1),
    )
    return declared_predicate_evidence(
        frame,
        context,
        products,
        dependency="native-selected-annotation-product",
        primary_products=primary,
        passages=(passage(frame.text, start, end),),
    )


def frame_rows(evidence):
    return [
        row["component"]
        for row in evidence.contributions
        if row.get("component", {}).get("kind") == "predicate_frame"
    ]


def test_current_native_clipped_role_population_detects_omitted_roles(
    current_pdf_source_factory, tmp_path
):
    from semantic.current_pdf_source_support import admit_current_target
    from semantic.structural_production_native_support import (
        PREDICATES,
        produce_source_reports,
        recipe,
    )

    spelling = "The analyst records the input."
    with current_pdf_source_factory((("text", spelling, spelling, None),)) as source:
        kernel = admit_current_target(source, recipe(tmp_path / "recipe"), tmp_path / "consumer")
        _, original, products, _ = produce_source_reports(source, kernel, PREDICATES, text=spelling)
        frame, annotations_, primary = actual_basis(kernel, original, products)
        whole = scoped_evidence(frame, annotations_, primary)
        (reading,) = frame_rows(whole)
        members = {member["role"]: member for member in reading["frame_members"]}
        assert members["actor"]["token_indices"] == (0, 1)
        assert members["object"]["token_indices"] == (3, 4)
        start = spelling.index("records")
        (clipped,) = frame_rows(
            scoped_evidence(frame, annotations_, primary, start, start + len("records"))
        )
        assert clipped["unlocated_roles"] == (
            dict(role="actor", head_token=1, token_indices=(0, 1), reason="outside_selection"),
            dict(role="object", head_token=4, token_indices=(3, 4), reason="outside_selection"),
        )
        (partial,) = frame_rows(
            scoped_evidence(frame, annotations_, primary, start, spelling.index("input"))
        )
        assert partial["unlocated_roles"] == (clipped["unlocated_roles"][0],)
        (object_,) = [member for member in partial["frame_members"] if member["role"] == "object"]
        assert object_["token_indices"] == (3,) and object_["outcome"] == "partial"
        # A changed source projection cannot reuse the authentic selected annotation/construction basis.
        changed = replace(
            frame,
            pin_content=canonical_bytes(
                {**frame.pin.values(), "projection_digest": "f" * 64}
            ).decode(),
            source_content=canonical_bytes(
                {**frame.value, "source": {**frame.value["source"], "projection": "f" * 64}}
            ).decode(),
        )
        with pytest.raises(ValueError, match=r"bound source product|original source"):
            scoped_evidence(changed, annotations_, primary)


def list_content():
    from pdf_controlled_support import ControlledPdfContent

    "Controlled Docling decoding only; every downstream producer executes normally."
    from docling_core.types.doc import DocItemLabel, DoclingDocument, GroupLabel, Size

    document = DoclingDocument(name="Independent list membership")
    document.add_page(page_no=1, size=Size(width=200, height=300))
    section = document.add_group(label=GroupLabel.SECTION, name="Selected list")
    document.add_text(label=DocItemLabel.TEXT, text=LIST_INTRO, parent=section)
    group = document.add_group(label=GroupLabel.LIST, name="Selected children", parent=section)
    document.add_list_item(text="The analyst records the input.", parent=group)
    document.add_list_item(text="The reviewer checks the result.", parent=group)
    return ControlledPdfContent.from_document(document)


LIST_INTRO = "For each of the following, assume that all inputs are valid:"


def test_current_native_list_host_requires_exact_selected_membership(
    scenario_seeds, tmp_path, monkeypatch
):
    from semantic.current_pdf_source_support import _current_pdf_source, admit_current_target
    from semantic.structural_production_native_support import (
        PREDICATES,
        produce_source_reports,
        recipe,
    )

    spelling = LIST_INTRO + "\nThe analyst records the input.\nThe reviewer checks the result."
    with _current_pdf_source(
        scenario_seeds, tmp_path, content=list_content(), sections=("#/groups/0",)
    ) as source:
        kernel = admit_current_target(source, recipe(tmp_path / "recipe"), tmp_path / "consumer")
        _, original, products, _ = produce_source_reports(source, kernel, PREDICATES, text=spelling)
        frame, annotations_, primary = actual_basis(kernel, original, products)
        whole = scoped_evidence(frame, annotations_, primary)

        def hosts(evidence):
            rows = {row["contribution_id"]: row for row in evidence.contributions}
            selected = {}
            for row in evidence.contributions:
                attachment = row.get("component", {})
                if "host_witness" not in attachment:
                    continue
                assert attachment["host_witness"] == dict(
                    kind="list_intro", list_group="#/groups/1"
                )
                host = rows[attachment["host_contribution_id"]]["component"]
                (predicate,) = [
                    member for member in host["frame_members"] if member["role"] == "predicate"
                ]
                selected.update(
                    {
                        spelling[extent["start"] : extent["end"]]: host
                        for extent in predicate["extents"]
                    }
                )
            return selected

        assert set(hosts(whole)) == {"records", "checks"}
        clipped = scoped_evidence(frame, annotations_, primary, 0, spelling.index("\nThe reviewer"))
        assert set(hosts(clipped)) == {"records"}


def test_attribution_requires_an_eligible_reporting_governor(monkeypatch):
    spelling = "Suppose we wait."
    for pos, expected in (("VERB", "reference"), ("NOUN", "unresolved")):
        product, primary = authored_product(
            monkeypatch,
            spelling,
            (
                (pos, "ROOT", 0, "suppose"),
                ("PRON", "nsubj", 2, "we"),
                ("VERB", "ccomp", 0, "wait"),
                ("PUNCT", "punct", 2, "."),
            ),
        )
        result = predicate_frames(spelling, (product,), primary_products=(primary,))
        assert not result.issues
        (frame,) = [f for f in result.frames if f.predicate.tokens == (2,)]
        assert frame.interpretation == expected
        assert frame.voice == "active" and frame.polarity == "positive"


def test_block_negation_preserves_direct_and_shared_scope(monkeypatch):
    for connector, expected in (
        ("and", {2: "negative_scope_unresolved", 4: "negative_scope_unresolved"}),
        ("but", {2: "negative", 4: "positive"}),
    ):
        spelling = f"Do not heat {connector} stir"
        product, primary = authored_product(
            monkeypatch,
            spelling,
            (
                ("AUX", "aux", 2, "do"),
                ("PART", "neg", 2, "not"),
                ("VERB", "ROOT", 2, "heat"),
                ("CCONJ", "cc", 2, connector),
                ("VERB", "conj", 2, "stir"),
            ),
        )
        result = predicate_frames(spelling, (product,), primary_products=(primary,))
        assert not result.issues
        assert {f.predicate.tokens[0]: f.polarity for f in result.frames} == expected


def test_example_cue_uses_one_governor_and_refuses_numbered_reference(monkeypatch):
    cases = (
        (
            "For example, permutations are",
            (
                ("ADP", "prep", 3, "for"),
                ("NOUN", "pobj", 0, "example"),
                ("PUNCT", "punct", 3, ","),
                ("NOUN", "nsubj", 4, "permutation"),
                ("AUX", "ROOT", 4, "be"),
            ),
            4,
            "example",
        ),
        (
            "Figure Tree for Example 4.25",
            (
                ("VERB", "ROOT", 0, "figure"),
                ("NOUN", "appos", 0, "tree"),
                ("ADP", "prep", 1, "for"),
                ("PROPN", "pobj", 2, "example"),
                ("NUM", "nummod", 3, "4.25"),
            ),
            0,
            "unresolved",
        ),
    )
    for spelling, columns, host, expected in cases:
        product, primary = authored_product(monkeypatch, spelling, columns)
        result = predicate_frames(spelling, (product,), primary_products=(primary,))
        assert not result.issues
        (frame,) = [f for f in result.frames if f.predicate.tokens == (host,)]
        assert frame.interpretation == expected
        if expected == "example":
            assert len([f for f in result.frames if f.interpretation == "example"]) == 1
