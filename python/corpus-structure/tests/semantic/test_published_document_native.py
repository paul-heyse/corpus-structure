"""Actual exact-pin selected report and ancestry projections on a small publication."""

from copy import deepcopy
from hashlib import sha256
from importlib.resources import files

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.ingest.pdf_section_views import published_section_drafts
from corpus_structure.semantic.pdf_record_reader import published_record_reader
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.source_views import load_source_view, store_source_view

from .native_record_fixtures import publish_native_record_fixture
from .pdf_staging_support import private_build as private_build
from .test_pdf_inline_reports import example as inline_report_example
from .test_selected_source_native import deploy_selected, publish_selected


def test_selected_pin_ancestry_source_view_replay_and_empty_array_scope(
    private_build, semantic_db_engine, semantic_writer_engine, semantic_reader_engine, tmp_path
):
    deploy_selected(semantic_db_engine)
    published = publish_selected(semantic_writer_engine, private_build, tmp_path / "source")
    with semantic_writer_engine.begin() as conn:
        task = conn.execute(
            text("SELECT run_id,unit_id,attempt,claimed_by FROM ops.task WHERE id=:task"),
            dict(task=private_build.task_id),
        ).one()
        reader = published_record_reader(
            conn,
            ProductReference(private_build.task_id, "selected", published.logical_digest),
            projection_context=open_release(conn, private_build.release_id),
        )
        assert reader is not None
        drafts = published_section_drafts(
            reader,
            document_id=task.unit_id,
            selections=("Selected chapter",),
            membership="direct",
            scope=None,
            consumer_release=private_build.release_id,
        )
        assert [draft.section_pointer for draft in drafts] == ["#/groups/1", "#/groups/2"]
        for position, draft in enumerate(drafts):
            parameters = dict(
                run_id=task.run_id,
                task_id=private_build.task_id,
                attempt=task.attempt,
                holder=task.claimed_by,
                draft=draft,
                position=position,
            )
            identity = store_source_view(conn, **parameters)
            assert store_source_view(conn, **parameters) == identity
            retained = load_source_view(conn, identity, analysis=False)
            assert retained.text == draft.text
            assert retained.ref.native_product == draft.native_product
            placement = conn.execute(
                text("SELECT native_build_id,native_revision_id FROM kb.source_view WHERE id=:id"),
                dict(id=identity),
            ).one()
            assert tuple(placement) == (private_build.build_id, private_build.build_id)
    with semantic_reader_engine.connect() as conn:
        context = open_release(conn, private_build.release_id)
        reader = published_record_reader(
            conn,
            ProductReference(private_build.task_id, "selected", published.logical_digest),
            projection_context=context,
        )
        assert reader is not None
        assert [row["pointer"] for row in reader.item_ancestors("#/texts/1")] == [
            "#/body",
            "#/groups/0",
            "#/groups/1",
            "#/groups/2",
            "#/texts/1",
        ]
        assert reader.selected_item_reports(("#/texts/1",)) == []
        assert reader.selected_item_reports(("#/texts/1",), kinds=("derivation_mappings",)) == []
        assert reader.selected_item_reports(()) == []
        assert reader.selected_regions(()) == []
        assert reader.item_ancestors("#/missing") == []
        assert conn.scalar(text("SELECT to_regclass('kb.native_document_derivation')")) is None
        assert conn.scalar(text("SELECT to_regclass('ops.pdf_published_derivation')")) is None
    with semantic_reader_engine.connect() as conn, pytest.raises(DBAPIError):
        conn.execute(
            text(
                "SELECT * FROM ops.read_pdf_published_region_batch(:task,'selected',:digest,NULL)"
            ),
            dict(task=private_build.task_id, digest=published.logical_digest),
        ).all()


def test_selected_reports_use_valid_original_parent_candidate_geometry_and_prose_ancestry(
    private_build, semantic_writer_engine, semantic_reader_engine, tmp_path, monkeypatch
):
    from docling_core.types.doc import (
        BoundingBox,
        DocItemLabel,
        DoclingDocument,
        GroupLabel,
        PageItem,
        ProvenanceItem,
        Size,
    )

    from corpus_structure.ingest.pdf import PdfConversion, publication_payload
    from corpus_structure.ingest.pdf_hierarchy import snapshot
    from corpus_structure.semantic.pdf_contracts import pdf_context_for_task, prepare_pdf_product
    from corpus_structure.serve.native_source import (
        NativeSourceRequest,
        _published_alignment_reports,
        _published_parent_product,
        inspect_native_source,
    )

    with semantic_reader_engine.connect() as conn:
        original = bytes(
            conn.scalar(
                text("SELECT content FROM kb.source_artifact WHERE artifact_digest=:digest"),
                dict(digest=private_build.source_digest),
            )
        )
        recipe = bytes(
            conn.scalar(
                text("SELECT content FROM kb.source_artifact WHERE artifact_digest=:digest"),
                dict(digest=private_build.recipe_digest),
            )
        )
        context = pdf_context_for_task(conn, private_build.task_id)
    schema = (
        files("corpus_structure")
        .joinpath("model/semantic/docling-validation.schema.json")
        .read_bytes()
    )
    document = DoclingDocument(name="Retained source diagnostic ancestry")
    document.pages[1] = PageItem(page_no=1, size=Size(width=200, height=300))
    section = document.add_group(label=GroupLabel.SECTION, name="Selected")
    prose = document.add_text(
        label=DocItemLabel.TEXT,
        text="x=1",
        orig="x=1",
        parent=section,
        prov=ProvenanceItem(
            page_no=1,
            bbox=BoundingBox(l=26, t=40, r=66, b=60, coord_origin="TOPLEFT"),
            charspan=(0, 3),
        ),
    )
    outside = document.add_text(
        label=DocItemLabel.TEXT,
        text="other",
        orig="other",
        prov=ProvenanceItem(
            page_no=1,
            bbox=BoundingBox(l=100, t=130, r=180, b=160, coord_origin="TOPLEFT"),
            charspan=(0, 5),
        ),
    )
    pages = inline_report_example()["inline_candidate_pages"]
    second = deepcopy(pages[0]["candidates"][0])
    second.update(left=140, right=145, top=140, bottom=145)
    pages[0]["candidates"].append(second)

    def payload(key):
        conversion = PdfConversion(
            sha256(original).hexdigest(), recipe, snapshot(document), "success", (), (), (), None
        )
        value = publication_payload(
            conversion, product_key=key, schema_digest=sha256(schema).hexdigest()
        )
        value["inline_candidate_pages"] = deepcopy(pages)
        return value

    raw = prepare_pdf_product(payload("raw"), original, schema, recipe, context=context)
    original_pin = publish_native_record_fixture(
        semantic_writer_engine,
        tmp_path / "original",
        task_id=private_build.task_id,
        attempt=private_build.attempt,
        holder=private_build.holder,
        product=raw,
        document=document,
    )
    formula = document.add_formula(text="x=1", orig="x=1", parent=prose)
    values = payload("derived")
    values.update(
        parent_task_id=private_build.task_id,
        parent_product_key="raw",
        parent_digest=original_pin.logical_digest,
    )
    values["inline_alignment_reports"] = [
        dict(
            page_no=1,
            candidate_index=0,
            item_pointers=[prose.self_ref],
            outcome="unresolved",
            basis="unmatched-native-text",
            detail="Retained ancestor prose diagnostic \x00é🙂",
        ),
        dict(
            page_no=1,
            candidate_index=1,
            item_pointers=[outside.self_ref],
            outcome="unresolved",
            basis="unmatched-native-text",
            detail="Retained outside prose diagnostic",
        ),
    ]
    values["derivation_mappings"] = [
        dict(
            pointer=formula.self_ref,
            origin_pointer=prose.self_ref,
            source_field="text",
            start=0,
            end=3,
            kind="native_text_range",
        )
    ]
    derived = prepare_pdf_product(values, original, schema, recipe, context=context)
    selected = publish_native_record_fixture(
        semantic_writer_engine,
        tmp_path / "derived",
        task_id=private_build.task_id,
        attempt=private_build.attempt,
        holder=private_build.holder,
        product=derived,
        document=document,
    )
    with semantic_reader_engine.connect() as conn:
        reader = published_record_reader(
            conn,
            ProductReference(private_build.task_id, "derived", selected.logical_digest),
            projection_context=open_release(conn, private_build.release_id),
        )
        assert reader is not None
        scans = []
        original_rows = reader.iter_rows

        def observed_rows(family, filters=None, **kwargs):
            if (filters or {}).get("kind") == "inline_alignment_reports" and kwargs.get(
                "batch_size"
            ) != 1:
                scans.append(filters)
            yield from original_rows(family, filters, **kwargs)

        monkeypatch.setattr(reader, "iter_rows", observed_rows)
        reports = reader.selected_item_reports((formula.self_ref,))
        assert {row["local_id"] for row in reports} == {
            "inline_alignment_reports:0",
            "derivation_mappings:0",
        }
        assert _published_alignment_reports(reader, formula.self_ref) == [
            dict(values["inline_alignment_reports"][0], candidate_basis="native-vector-gap-v1")
        ]
        decorated = _published_alignment_reports(reader, formula.self_ref)
        assert decorated is not None
        decorated[0]["detail"] = "caller decoration"
        assert _published_alignment_reports(reader, formula.self_ref) == [
            dict(values["inline_alignment_reports"][0], candidate_basis="native-vector-gap-v1")
        ]
        assert len(scans) == 1
        assert _published_parent_product(reader) == dict(
            task_id=private_build.task_id,
            product_key="raw",
            content_digest=original_pin.logical_digest,
        )
        assert reader.selected_item_reports(()) == []
        run_id = conn.scalar(
            text("SELECT run_id FROM ops.task WHERE id=:task"),
            dict(task=private_build.task_id),
        )
        response = inspect_native_source(
            conn,
            NativeSourceRequest(
                run_id=run_id,
                task_id=private_build.task_id,
                product_key="derived",
                content_digest=selected.logical_digest,
                view="item",
                pointer=formula.self_ref,
            ),
        )
        assert response.rows[0]["inline_alignment_reports"] == [
            dict(
                values["inline_alignment_reports"][0],
                candidate_basis="native-vector-gap-v1",
                source_product=dict(
                    task_id=private_build.task_id,
                    product_key="raw",
                    content_digest=original_pin.logical_digest,
                ),
            )
        ]
