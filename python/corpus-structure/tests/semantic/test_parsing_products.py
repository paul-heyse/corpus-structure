"""Independent source-defined parsing products, native custody and restricted publication."""

from copy import deepcopy
from hashlib import sha256
from types import SimpleNamespace

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.parsing_products import (
    PARSING_CONTRACT_DIGEST,
    prepare_parsing_product,
    read_parsing_product,
    store_parsing_product,
)


def product_values(original=b"a\xc3\xa9 "):
    # Four original bytes versus three Unicode codepoints. Whitespace is retained separately.
    return dict(
        recipe="source-products-v1",
        artifact_digest=sha256(original).hexdigest(),
        lifecycle="available",
        semantic_state="ok",
        provenance_state="partial",
        representations=[
            dict(
                representation_id="raw",
                kind="original",
                unit="byte",
                extent_length=len(original),
                partition_state="complete",
                recognition_state="complete",
            ),
            dict(
                representation_id="canonical",
                kind="canonical",
                unit="codepoint",
                extent_length=3,
                text_content="aé ",
                partition_state="complete",
                recognition_state="complete",
            ),
        ],
        components=[
            dict(
                component_id="r0",
                representation_id="raw",
                unit="byte",
                start_offset=0,
                end_offset=3,
                ordinal=0,
                category="text",
            ),
            dict(
                component_id="r1",
                representation_id="raw",
                unit="byte",
                start_offset=3,
                end_offset=4,
                ordinal=1,
                category="whitespace",
            ),
            dict(
                component_id="c0",
                representation_id="canonical",
                unit="codepoint",
                start_offset=0,
                end_offset=2,
                ordinal=0,
                category="text",
            ),
            dict(
                component_id="c1",
                representation_id="canonical",
                unit="codepoint",
                start_offset=2,
                end_offset=3,
                ordinal=1,
                category="whitespace",
            ),
        ],
        nodes=[
            dict(
                node_id="implied",
                kind="element",
                origin="synthetic",
                origin_reason="HTML5 implied element",
            )
        ],
        relationships=[
            dict(relationship_id="parallel1", kind="reference"),
            dict(relationship_id="parallel2", kind="reference"),
        ],
        endpoints=[
            dict(relationship_id=key, ordinal=i, role=role, component_id="c0")
            for key in ("parallel1", "parallel2")
            for i, role in enumerate(("source", "target"))
        ],
        mappings=[
            dict(
                mapping_id="unavailable",
                operation="decode",
                reason="decoder origins not qualified",
                fidelity="unknown",
            )
        ],
        mapping_endpoints=[
            dict(
                mapping_id="unavailable",
                side="source",
                ordinal=0,
                representation_id="raw",
                unit="byte",
                start_offset=0,
                end_offset=4,
            ),
            dict(
                mapping_id="unavailable",
                side="target",
                ordinal=0,
                representation_id="canonical",
                unit="codepoint",
                start_offset=0,
                end_offset=3,
            ),
        ],
    )


def test_model_derived_shapes_and_immutable_transport():
    raw = b"a\xc3\xa9 "
    values = product_values(raw)
    product = prepare_parsing_product(values, raw)
    values["components"][0]["category"] = "invented"
    assert product.values()["components"][0]["category"] == "text"
    with pytest.raises(ValueError, match=r"ComponentCategory|literal_error|Input should"):
        prepare_parsing_product(values, raw)
    assert product.original == raw


@pytest.mark.parametrize(
    "change",
    [
        lambda p: p["components"][0].update(unit="codepoint"),
        lambda p: p["components"][1].update(start_offset=2),
        lambda p: p["components"].pop(),
        lambda p: p["components"].append(deepcopy(p["components"][0])),
        lambda p: p["endpoints"][0].update(component_id="missing"),
        lambda p: p["endpoints"][0].update(target_task_id=7),
        lambda p: p["endpoints"][0].update(ordinal=8),
        lambda p: p.update(provenance_state="complete"),
        lambda p: p["nodes"][0].update(start_offset=0),
    ],
)
def test_independent_invalid_products_refuse(change):
    values = product_values()
    change(values)
    with pytest.raises(ValueError):
        prepare_parsing_product(values, b"a\xc3\xa9 ")


def test_exact_copy_checks_contents_and_complete_origin_universe():
    p = product_values()
    p["mappings"] = [dict(mapping_id="copy", operation="copy", reason="identity", fidelity="exact")]
    p["mapping_endpoints"] = [
        dict(
            mapping_id="copy",
            side=side,
            ordinal=0,
            representation_id="canonical",
            unit="codepoint",
            start_offset=0,
            end_offset=3,
        )
        for side in ("source", "target")
    ]
    assert prepare_parsing_product(p, b"a\xc3\xa9 ")
    p["provenance_state"] = "complete"
    with pytest.raises(ValueError, match="qualified decoding"):
        prepare_parsing_product(p, b"a\xc3\xa9 ")
    p["provenance_state"] = "partial"
    p["mapping_endpoints"][0]["start_offset"] = 1
    with pytest.raises(ValueError, match="content differs"):
        prepare_parsing_product(p, b"a\xc3\xa9 ")
    p = product_values()
    p["representations"] = p["representations"][:1]
    with pytest.raises(ValueError, match="canonical"):
        prepare_parsing_product(p, b"a\xc3\xa9 ")


def _native_build(conn, prepared, original, tmp_path, *, hash_suffix="one", content=None):
    from corpus_structure.core.evidence import RenditionContent, Segment
    from corpus_structure.core.vocab import SegmentKind
    from corpus_structure.semantic.operations import (
        OperationBinding,
        claim_tasks,
        create_run,
        create_task,
        record_method,
        register_document,
        store_rendition,
    )

    run = create_run(
        conn,
        project_id="p",
        binding=OperationBinding(prepared.release_id, "z", 0, b"{}"),
        kind="full",
        options={},
        code_commit="parsing-test",
    )
    from pydantic import create_model

    config = record_method(
        conn,
        SimpleNamespace(
            name="ingest.fixture",
            version="1",
            family="ingest",
            tier="deterministic",
            confidence_source=None,
            unit_type="document",
            Config=create_model("FixtureConfig"),
        ),
        "default",
        {},
        "parsing-fixture",
    )
    original_path = tmp_path / "source.html"
    original_path.write_bytes(original)
    doc = register_document(
        conn,
        project_id="p",
        source_uri="file:parsing",
        original_path=str(original_path),
        original=original,
     mime='text/html')
    task = create_task(
        conn,
        run_id=run,
        config_id=config,
        stage="ingest",
        unit_type="document",
        unit_id=doc,
        input_hash=hash_suffix,
    )
    claim = claim_tasks(conn, run_id=run, config_id=config, holder="fixture")[0]
    if content is None:
        content = RenditionContent(
            canonical_text="aé ", document=Segment(kind=SegmentKind.DOCUMENT, start=0, end=3)
        )
    rendition = store_rendition(
        conn,
        run_id=run,
        document_id=doc,
        content=content,
        task_id=task,
        config_id=config,
        parse_detail={},
        prepared=prepared,
    )
    return run, task, claim.attempt, rendition


def test_native_restricted_publication_build_identity_and_retained_original(
    semantic_db_engine, semantic_writer_engine, semantic_reader_engine, tmp_path
):
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.operations import BoundReader

    from .test_operations import setup

    p = setup(semantic_db_engine, observations=True, composed=True)
    original = b"a\xc3\xa9 "
    product = prepare_parsing_product(product_values(original), original)
    with semantic_writer_engine.begin() as c:
        run, task, attempt, rendition = _native_build(c, p, original, tmp_path)
        assert (
            store_parsing_product(
                c, task_id=task, attempt=attempt, holder="fixture", product=product
            )
            == product.digest
        )
        assert (
            store_parsing_product(
                c, task_id=task, attempt=attempt, holder="fixture", product=product
            )
            == product.digest
        )
    with semantic_reader_engine.begin() as c:
        retained = read_parsing_product(c, task_id=task)
        assert retained == product
        assert BoundReader(c, run, p).parsing_product(rendition) == product
        assert c.execute(
            select(table("kb.parsing_relationship").c.relationship_id)
        ).scalars().all() == ["parallel1", "parallel2"]
        with pytest.raises(DBAPIError), c.begin_nested():
            c.execute(text("UPDATE kb.source_artifact SET content=''::bytea"))
    with semantic_writer_engine.begin() as c:
        _, second, attempt2, rendition2 = _native_build(c, p, original, tmp_path, hash_suffix="two")
        assert rendition2 == rendition
        values = product_values(original)
        values["semantic_state"] = "ambiguous"
        values["dependencies"] = [
            dict(
                name="definition", target_task_id=task, artifact_digest=sha256(original).hexdigest()
            )
        ]
        values["endpoints"][1].update(target_task_id=task, dependency_name="definition")
        other = prepare_parsing_product(values, original)
        store_parsing_product(c, task_id=second, attempt=attempt2, holder="fixture", product=other)
        assert read_parsing_product(c, task_id=task) == product
        assert read_parsing_product(c, task_id=second) == other
        with pytest.raises(DBAPIError), c.begin_nested():
            store_parsing_product(c, task_id=task, attempt=attempt, holder="fixture", product=other)
        with pytest.raises(DBAPIError), c.begin_nested():
            c.execute(text("INSERT INTO kb.source_artifact VALUES('fake','fake'::bytea)"))
        with pytest.raises(DBAPIError), c.begin_nested():
            store_parsing_product(
                c, task_id=task, attempt=attempt + 1, holder="fixture", product=product
            )


def test_native_refuses_invalid_foreign_keys_units_scope_and_claims(
    semantic_db_engine, semantic_writer_engine, tmp_path
):
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.metadata import table

    from .test_operations import setup

    p = setup(semantic_db_engine, observations=True, composed=True)
    original = b"a\xc3\xa9 "
    with semantic_writer_engine.begin() as c:
        _, task, attempt, _ = _native_build(c, p, original, tmp_path)
        changes = [
            lambda p: p["components"][0].update(unit="codepoint"),
            lambda p: p["components"][1].update(start_offset=2),
            lambda p: p["endpoints"][0].update(component_id="missing"),
            lambda p: p["endpoints"][0].update(target_task_id=12345, dependency_name="undeclared"),
            lambda p: p["representations"][1].update(text_content="bad"),
            lambda p: p.update(provenance_state="complete"),
            lambda p: p["components"][0].update(invented="discard me"),
            lambda p: p["components"][0].update(start_offset="0"),
        ]
        for change in changes:
            values = product_values(original)
            change(values)
            with pytest.raises(DBAPIError), c.begin_nested():
                c.execute(
                    text(
                        "SELECT ops.publish_parsing_product("
                        ":task,:attempt,'fixture',:contract,:payload,:original)"
                    ),
                    dict(
                        task=task,
                        attempt=attempt,
                        contract=PARSING_CONTRACT_DIGEST,
                        payload=canonical_bytes(values),
                        original=original,
                    ),
                )
            assert (
                c.execute(
                    select(table("ops.parsing_product").c.task_id).where(
                        table("ops.parsing_product").c.task_id == task
                    )
                ).first()
                is None
            )
        # A self-consistent artifact from another acquisition cannot impersonate the build.
        wrong = b"xxxx"
        values = product_values(wrong)
        with pytest.raises(DBAPIError), c.begin_nested():
            c.execute(
                text(
                    "SELECT ops.publish_parsing_product("
                    ":task,:attempt,'fixture',:contract,:payload,:original)"
                ),
                dict(
                    task=task,
                    attempt=attempt,
                    contract=PARSING_CONTRACT_DIGEST,
                    payload=canonical_bytes(values),
                    original=wrong,
                ),
            )


def test_original_acquisition_survives_decode_failure_without_a_rendition(
    semantic_db_engine, semantic_writer_engine, semantic_reader_engine, tmp_path
):
    from corpus_structure.semantic.operations import read_original, register_document

    from .test_operations import setup

    setup(semantic_db_engine)
    original = b"\xff\xfe\x00broken"
    path = tmp_path / "invalid-encoding.html"
    path.write_bytes(original)
    with semantic_writer_engine.begin() as c:
        doc = register_document(
            c, project_id="p", source_uri="file:broken", original_path=str(path), original=original
        , mime='text/html')
    path.unlink()
    with semantic_reader_engine.connect() as c:
        assert read_original(c, doc) == original
