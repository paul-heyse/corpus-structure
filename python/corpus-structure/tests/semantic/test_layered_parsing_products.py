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


def mathematical_products(root, text_reference):
    from corpus_structure.methods.math.prepared import PreparedMathInput
    from corpus_structure.methods.math.products import (
        assessment_product_payload,
        interpretation_product_payload,
    )
    from corpus_structure.semantic.analysis_contracts import prepare_interpretation_context

    operand = PreparedMathInput(
        prepare_interpretation_context(macros={}, kind="formula"),
        "a",
        source_text="aé ",
        source_start=0,
        parse_start=0,
    )
    reading = interpretation_product_payload(
        operand, root=root, text_product=text_reference, source_node_id="view:0"
    )
    interpreted = prepare_layered_product(reading)
    assessment = assessment_product_payload(
        operand,
        operand.assess("free_symbols"),
        root=root,
        interpretation_product=ProductReference(
            root.task_id, interpreted.product_key, interpreted.digest
        ),
    )
    return reading, assessment


@pytest.mark.parametrize("field", ["occurrence_ids", "evidence_ids", "interpretation_ids"])
def test_semantic_records_reject_dangling_local_and_unqualified_references(field):
    root = ProductReference(7, "source", "a" * 64)
    reading, assessment = mathematical_products(root, ProductReference(7, "text", "b" * 64))
    values = reading if field == "occurrence_ids" else assessment
    record = values["interpretations" if field == "occurrence_ids" else "assessments"][0]
    record[field] = ["missing"]
    with pytest.raises(ValueError, match="reference"):
        prepare_layered_product(values)


def test_native_semantic_references_resolve_actual_typed_dependency_targets(
    semantic_db_engine, semantic_writer_engine, tmp_path
):
    from corpus_structure.semantic.identity import canonical_bytes

    prepared = setup(semantic_db_engine, observations=True, composed=True)
    source = prepare_parsing_product(product_values(), b"a\xc3\xa9 ")
    with semantic_writer_engine.begin() as conn:
        _, task, attempt, _ = _native_build(conn, prepared, source.original, tmp_path)
        store_parsing_product(conn, task_id=task, attempt=attempt, holder="fixture", product=source)
        root = ProductReference(task, "source", source.digest)
        text_value = text_product_payload(
            "aé ", root=root.values(), math_ranges=[(0, 1, None, None)]
        )
        captured = prepare_layered_product(text_value)
        text_reference = store_layered_products(
            conn,
            task_id=task,
            attempt=attempt,
            holder="fixture",
            products=PreparedParsingProductSet((captured,)),
        )[0]
        reading, assessment = mathematical_products(root, text_reference)
        for field in ("occurrence_ids", "evidence_ids", "interpretation_ids"):
            if field == "evidence_ids":
                interpreted = prepare_layered_product(reading)
                store_layered_products(
                    conn,
                    task_id=task,
                    attempt=attempt,
                    holder="fixture",
                    products=PreparedParsingProductSet((interpreted,)),
                )
            values = deepcopy(reading if field == "occurrence_ids" else assessment)
            record = values["interpretations" if field == "occurrence_ids" else "assessments"][0]
            record[field] = ["missing"]
            with pytest.raises(DBAPIError, match="reference"), conn.begin_nested():
                conn.execute(
                    text(
                        "SELECT ops.publish_layered_parsing_product("
                        ":task,:attempt,'fixture',:contract,:payload)"
                    ),
                    dict(
                        task=task,
                        attempt=attempt,
                        contract=captured.contract_digest,
                        payload=canonical_bytes(values),
                    ),
                )
        interpreted = prepare_layered_product(reading)
        store_layered_products(
            conn,
            task_id=task,
            attempt=attempt,
            holder="fixture",
            products=PreparedParsingProductSet((interpreted,)),
        )
        # A real structural node with the same spelling is insufficient: the named dependency
        # must contain an actual interpretation record, enforced at the native trust boundary.
        forged = deepcopy(assessment)
        forged["dependencies"][1].update(
            target_product_key="text", target_content_digest=captured.digest
        )
        forged["endpoints"][1].update(
            target_product_key="text", target_content_digest=captured.digest, node_id="view:0"
        )
        forged["assessments"][0]["interpretation_ids"] = ["view:0"]
        unchecked_target = prepare_layered_product(forged)
        with (
            pytest.raises(DBAPIError, match="qualified interpretation custody"),
            conn.begin_nested(),
        ):
            store_layered_products(
                conn,
                task_id=task,
                attempt=attempt,
                holder="fixture",
                products=PreparedParsingProductSet((unchecked_target,)),
            )
        checked = prepare_layered_product(assessment)
        refs = store_layered_products(
            conn,
            task_id=task,
            attempt=attempt,
            holder="fixture",
            products=PreparedParsingProductSet((checked,)),
        )
        assert read_layered_product(conn, refs[0]) == checked


def test_native_macro_event_metadata_preserves_typed_policy_and_rejects_invalid_ranges(
    semantic_db_engine, semantic_writer_engine, tmp_path
):
    from corpus_structure.ingest.macros import MacroSource, read_macros
    from corpus_structure.ingest.text_product import text_product_artifacts
    from corpus_structure.semantic.identity import canonical_bytes

    prepared = setup(semantic_db_engine, observations=True, composed=True)
    source = prepare_parsing_product(product_values(), b"a\xc3\xa9 ")
    with semantic_writer_engine.begin() as conn:
        _, task, attempt, _ = _native_build(conn, prepared, source.original, tmp_path)
        store_parsing_product(conn, task_id=task, attempt=attempt, holder="fixture", product=source)
        root = ProductReference(task, "source", source.digest)
        definitions = r"\newcommand{\f}{xy}"
        payload = text_product_payload(
            "aé ",
            root=root.values(),
            macro_sources=[
                MacroSource("defs", definitions, read_macros(definitions, source_ref="defs"))
            ],
        )
        product = prepare_layered_product(payload)
        artifacts = text_product_artifacts(payload)
        changes = (
            lambda n: n.pop("macro_event"),
            lambda n: n["macro_event"].update(status="invented"),
            lambda n: n["macro_event"].update(selected="true"),
            lambda n: n["macro_event"].update(status="ignored", selected=True),
            lambda n: n["macro_event"]["body_ranges"][0].update(end_offset=n["end_offset"] + 1),
            lambda n: n["macro_event"]["body_ranges"].reverse(),
            lambda n: n["macro_event"]["body_ranges"][0].update(end_offset=16),
        )
        for change in changes:
            invalid = deepcopy(product.values())
            event = next(n for n in invalid["nodes"] if n["kind"] == "macro_event")
            change(event)
            with pytest.raises(DBAPIError), conn.begin_nested():
                conn.execute(
                    text(
                        "SELECT ops.publish_layered_parsing_product("
                        ":task,:attempt,'fixture',:contract,:payload,:artifacts)"
                    ),
                    dict(
                        task=task,
                        attempt=attempt,
                        contract=product.contract_digest,
                        payload=canonical_bytes(invalid),
                        artifacts=list(artifacts),
                    ),
                )
        reference = store_layered_products(
            conn,
            task_id=task,
            attempt=attempt,
            holder="fixture",
            products=PreparedParsingProductSet((product,), artifacts=artifacts),
        )[0]
        assert read_layered_product(conn, reference) == product
