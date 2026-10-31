"""Source-defined parsing contract, provenance and bounded native-reader examples."""

import base64
import json
from dataclasses import replace
from pathlib import Path

import pytest

from corpus_structure.semantic.contracts import compile_execution_model, trusted_execution_inputs
from corpus_structure.semantic.parsing_contracts import validate_parsing_contracts
from corpus_structure.semantic.parsing_products import (
    parsing_contract,
    prepare_parsing_product,
    representation_text,
)
from corpus_structure.semantic.types import PreparationError

from .test_parsing_products import _native_build, product_values


def test_actual_producer_operations_are_admitted_but_unbound_declarations_refuse():
    model = compile_execution_model(trusted_execution_inputs())
    names = (
        "prepare_parsing_text",
        "interpret_parsing_math",
        "assess_parsing_math",
        "retain_pdf_original",
        "prepare_native_document",
        "publish_native_document",
    )
    for name in names:
        assert model.require_operation(name).implementation == name
    operation = model.operation("assess_parsing_math")
    unbound = replace(
        model,
        operations=tuple(
            replace(o, implementation=None) if o.id == operation.id else o for o in model.operations
        ),
    )
    with pytest.raises(PreparationError, match="no qualified producer"):
        unbound.require_operation(operation.id)


def test_node_variants_derive_literal_tags_and_forbid_attribute_fields_on_elements():
    boundary = parsing_contract()
    schema = boundary.adapter("ParsingNode").json_schema()
    assert schema["discriminator"]["propertyName"] == "kind"
    assert "attribute" in schema["discriminator"]["mapping"]
    with pytest.raises(ValueError):
        boundary.validate_json(
            "ParsingNode",
            json.dumps(
                dict(
                    node_id="element",
                    kind="element",
                    origin="synthetic",
                    origin_reason="implied element",
                    attribute_outcome="retained",
                )
            ),
        )
    with pytest.raises(ValueError):
        boundary.validate_json(
            "ParsingNode",
            json.dumps(
                dict(
                    node_id="attribute",
                    kind="attribute",
                    origin="literal",
                    representation_id="decoded",
                    unit="codepoint",
                    start_offset=0,
                    end_offset=1,
                )
            ),
        )


def test_unsupported_role_cardinality_and_adapter_revision_refuse():
    model = compile_execution_model(trusted_execution_inputs())
    relation = next(r for r in model.relationships if r.id == "parsing_reference")
    changed = replace(
        relation, endpoints=(replace(relation.endpoints[0], maximum=2), relation.endpoints[1])
    )
    with pytest.raises(PreparationError, match="qualify endpoint support"):
        validate_parsing_contracts(
            replace(
                model,
                relationships=tuple(
                    changed if r.id == relation.id else r for r in model.relationships
                ),
            )
        )
    with pytest.raises(PreparationError, match="qualify.*producer profile"):
        validate_parsing_contracts(
            replace(
                model,
                parsing_adapters=(
                    replace(model.parsing_adapters[0], frontend_revision="unsupported"),
                ),
            )
        )


@pytest.mark.parametrize("case", range(5))
def test_archived_html_shape_survives_without_admitting_a_current_html_producer(case):
    archive = json.loads(
        (Path(__file__).with_name("fixtures") / "retained-html-inputs.json").read_bytes()
    )
    retained = archive["parsing"][case]
    raw = base64.b64decode(retained["original_base64"])
    values = retained["payload"]
    parsing_contract().validate_json("ParsingProduct", json.dumps(values))
    with pytest.raises(ValueError, match="adapter is not admitted"):
        prepare_parsing_product(values, raw)
    assert values["provenance_universe"] == "canonical_output"
    assert values["provenance_state"] == "complete"
    decoded = next(r for r in values["representations"] if r["kind"] == "decoded")
    if b"\x00" in raw:
        assert "\x00" in representation_text(decoded)
        assert "text_content" not in decoded


def test_self_copy_does_not_establish_original_provenance():
    p = product_values()
    p.update(
        provenance_state="complete",
        provenance_universe="canonical_output",
    )
    p["mappings"][0].update(operation="copy", fidelity="exact")
    p["mapping_endpoints"][0].update(representation_id="canonical", unit="codepoint", end_offset=3)
    with pytest.raises(ValueError, match="rooted in original bytes"):
        prepare_parsing_product(p, b"a\xc3\xa9 ")


def test_native_bounded_queries_retain_order_and_refuse_limits(
    semantic_db_engine, semantic_writer_engine, semantic_reader_engine, tmp_path
):
    from corpus_structure.semantic.parsing_products import store_parsing_product
    from corpus_structure.semantic.parsing_queries import (
        ParsingReadLimit,
        components,
        relationship_endpoints,
        trace_mapping,
        trace_origins,
    )

    from .test_operations import setup

    prepared = setup(semantic_db_engine, observations=True, composed=True)
    original = b"a\xc3\xa9 "
    with semantic_writer_engine.begin() as conn:
        _, task, attempt, _ = _native_build(conn, prepared, original, tmp_path)
        store_parsing_product(
            conn,
            task_id=task,
            attempt=attempt,
            holder="fixture",
            product=prepare_parsing_product(product_values(), original),
        )
    with semantic_reader_engine.begin() as conn:
        assert [
            r.component_id
            for r in components(conn, task_id=task, representation_id="canonical", start=0, end=3)
        ] == ["c0", "c1"]
        assert components(conn, task_id=task, representation_id="canonical", start=1, end=1) == ()
        assert (
            trace_mapping(conn, task_id=task, representation_id="canonical", start=1, end=1) == ()
        )
        with pytest.raises(ParsingReadLimit):
            components(conn, task_id=task, representation_id="canonical", start=0, end=3, limit=1)
        assert [
            r.role for r in relationship_endpoints(conn, task_id=task, relationship_id="parallel1")
        ] == ["source", "target"]
        trace = trace_mapping(conn, task_id=task, representation_id="canonical", start=0, end=1)
        assert [(r.representation_id, r.start_offset, r.end_offset) for r in trace[0].source] == [
            ("raw", 0, 4)
        ]
        assert (
            trace_origins(conn, task_id=task, representation_id="canonical", start=0, end=1).outcome
            == "partial"
        )
