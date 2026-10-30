"""Independent common-layer invariants and protected publication with exact source custody."""

from copy import deepcopy

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.ingest.text_product import text_product_payload
from corpus_structure.semantic.parsing_products import (
    PreparedParsingProductSet,
    ProductReference,
    prepare_layered_product,
    prepare_parsing_product,
    read_layered_product,
    select_layered_products,
    store_layered_products,
    store_parsing_product,
)

from .test_operations import setup
from .test_parsing_products import _native_build, product_values


def text_product(root):
    return text_product_payload("aé ", root=root.values())


def test_common_layer_shape_and_deep_immutability():
    root = ProductReference(7, "source", "a" * 64)
    values = text_product(root)
    result = prepare_layered_product(values)
    values["components"][0]["start_offset"] = 55
    assert result.values()["components"][0]["start_offset"] == 0
    assert PreparedParsingProductSet((result,), required=("text",)).products == (result,)
    with pytest.raises(ValueError, match="missing"):
        PreparedParsingProductSet((result,), required=("assessment",))


@pytest.mark.parametrize(
    "change",
    [
        lambda p: p["mapping_endpoints"][0].pop("dependency_name"),
        lambda p: p["mapping_endpoints"][0].update(target_product_key="other"),
        lambda p: p["components"][0].update(unit="byte"),
        lambda p: p["components"][0].update(start_offset=1),
        lambda p: p["dependencies"][0].update(kind="artifact"),
        lambda p: p.update(kind="assessment"),
    ],
)
def test_layered_independent_invalid_examples(change):
    values = text_product(ProductReference(7, "source", "a" * 64))
    change(values)
    with pytest.raises(ValueError):
        prepare_layered_product(values)


def test_native_layered_common_registry_custody_replay_and_readback(
    semantic_db_engine, semantic_writer_engine, semantic_reader_engine, tmp_path
):
    prepared = setup(semantic_db_engine, observations=True, composed=True)
    source = prepare_parsing_product(product_values(), b"a\xc3\xa9 ")
    with semantic_writer_engine.begin() as conn:
        run, task, attempt, rendition = _native_build(conn, prepared, source.original, tmp_path)
        store_parsing_product(conn, task_id=task, attempt=attempt, holder="fixture", product=source)
        root = ProductReference(task, "source", source.digest)
        layer = prepare_layered_product(text_product(root))
        values = PreparedParsingProductSet((layer,), required=("text",))
        refs = store_layered_products(
            conn, task_id=task, attempt=attempt, holder="fixture", products=values
        )
        assert (
            store_layered_products(
                conn, task_id=task, attempt=attempt, holder="fixture", products=values
            )
            == refs
        )
        assert read_layered_product(conn, refs[0]) == layer
        assert read_layered_product(conn, root) == source
        with pytest.raises(DBAPIError), conn.begin_nested():
            store_layered_products(
                conn, task_id=task, attempt=attempt + 1, holder="fixture", products=values
            )
        bad = deepcopy(layer.values())
        bad["mapping_endpoints"][0]["target_content_digest"] = "f" * 64
        from corpus_structure.semantic.identity import canonical_bytes

        with pytest.raises(DBAPIError), conn.begin_nested():
            conn.execute(
                text(
                    "SELECT ops.publish_layered_parsing_product("
                    ":task,:attempt,'fixture',:contract,:payload)"
                ),
                dict(
                    task=task,
                    attempt=attempt,
                    contract=layer.contract_digest,
                    payload=canonical_bytes(bad),
                ),
            )
    with semantic_reader_engine.begin() as conn:
        selected = select_layered_products(conn, run_id=run, rendition_id=rendition)
        assert {s.kind for s in selected} == {"source", "text"}
        assert read_layered_product(conn, refs[0]) == layer
        with pytest.raises(DBAPIError), conn.begin_nested():
            conn.execute(text("UPDATE ops.parsing_layer_product SET coverage='complete'"))
