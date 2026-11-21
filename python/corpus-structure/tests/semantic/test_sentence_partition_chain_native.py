"""Actual annotation and canonical projection through native custody."""

from contextlib import ExitStack, contextmanager
from dataclasses import replace
from types import SimpleNamespace

import pytest

from corpus_structure.schema.model_change import native_model_inputs
from corpus_structure.semantic import migrations
from corpus_structure.semantic.canonical_sentences import canonical_sentence_operation_sources
from corpus_structure.semantic.composed import data_operation_dependencies
from corpus_structure.semantic.data_operation_values import decode_semantic_value
from corpus_structure.semantic.demand_results import read_demand_result, stream_selected_support
from corpus_structure.semantic.metadata import get_metadata
from corpus_structure.semantic.primary_operations import combine_primary_sources
from corpus_structure.semantic.sentence_products import sentence_product_inputs
from corpus_structure.semantic.target_installation import capture_target_installation
from native_test_support import principal_engine
from semantic.current_pdf_source_support import (
    PROJECT,
    ROOT,
    PdfSourceScenario,
    admit_current_target,
    build_pdf_source,
    current_pdf_recipe,
    section_content,
)
from semantic.data_operation_kernel_support import (
    CapturedKernelInputs,
    execute_captured_kernel_demand,
    split_captured_operations,
)
from semantic.structural_production_native_support import (
    produce_source_reports,
    selected_for_source,
)
from semantic.test_target_installation_native import install_target_root


def _recipe(directory, *, declaration=False):
    original = current_pdf_recipe(directory)
    captured = original.captured_inputs
    assert captured is not None
    dependencies, declarations, sources = split_captured_operations(captured)
    if declaration:
        from corpus_structure.semantic.declaration_products import (
            declaration_inputs,
            declaration_operation_sources,
        )
        from corpus_structure.semantic.hanlp_products import (
            hanlp_operation_sources,
            prepare_hanlp_selection,
        )

        bundle = declaration_inputs(captured.bundle)
        operations = combine_primary_sources(
            hanlp_operation_sources(prepare_hanlp_selection()), declaration_operation_sources()
        )
    else:
        bundle = sentence_product_inputs(captured.bundle)
        operations = canonical_sentence_operation_sources()
    return replace(
        original,
        name="hanlp-declaration-partition-chain"
        if declaration
        else "annotation-canonical-partition-chain",
        captured_inputs=CapturedKernelInputs(
            bundle,
            data_operation_dependencies(
                dependencies,
                declarations,
                combine_primary_sources(sources, operations),
            ),
            captured.profile,
        ),
    )


@contextmanager
def _private_source(admin, native_settings, tmp_path, monkeypatch, text):
    epoch = capture_target_installation(get_metadata(), logical_sources=native_model_inputs(ROOT))
    *_, revision_path = install_target_root(admin, epoch, tmp_path)
    monkeypatch.setattr(migrations, "ALEMBIC_DIR", revision_path)
    inputs = tmp_path / "capture"
    inputs.mkdir()
    scenario = PdfSourceScenario(
        section_content((("text", text, text, None),)), ("#/groups/0",), False
    )
    with ExitStack() as resources:
        purposes = {}

        def purpose(name):
            if name not in purposes:
                engine = principal_engine(native_settings, name, admin.url.database)
                resources.callback(engine.dispose)
                purposes[name] = engine
            return purposes[name]

        stage = build_pdf_source(scenario, admin, purpose("write"), inputs, purpose_engine=purpose)
        yield stage.acquired(SimpleNamespace(admin=admin, purpose=purpose))


@pytest.mark.gpu
@pytest.mark.provider_evidence
def test_actual_annotation_partition_proof_and_canonical_chain(
    semantic_bare_engine, native_settings, tmp_path, monkeypatch
):
    text = "Ada acts. Bob waits."
    target = "segment.sentences/canonical-projection"
    namespace = "https://corpus-structure.dev/semantic/data-operation-sentences/"
    with _private_source(
        semantic_bare_engine, native_settings, tmp_path, monkeypatch, text
    ) as source:
        kernel = admit_current_target(source, _recipe(tmp_path / "recipe"), tmp_path / "target")
        retained, original, products, _ = produce_source_reports(source, kernel, target, text=text)
        (annotation,) = selected_for_source(
            kernel, products, namespace + "DdoSourceAnnotations", original
        )
        (canonical,) = selected_for_source(
            kernel, products, namespace + "DdoCanonicalSentences", original
        )
        demand_id = retained["demand_id"]
        with kernel.purpose("read").begin() as connection:
            page = read_demand_result(connection, demand_id, project_id=PROJECT, limit=1000)
            packets = {
                (row["product_id"], row["partition_key"]): row
                for entry in stream_selected_support(connection, page, whole_read=True)
                if entry["relation"] == "kb.data_product_partition"
                and (row := entry["record"])["product_id"]
                in {canonical.row["product_id"], annotation.row["product_id"]}
            }
        assert len(packets) == 2
        (annotated,) = [
            row for (parent, _), row in packets.items() if parent == annotation.row["product_id"]
        ]
        projected = packets[canonical.row["product_id"], annotated["partition_key"]]
        annotation_rows = decode_semantic_value(annotated["body"])
        canonical_rows = decode_semantic_value(projected["body"])
        start = annotated["placement"]["start"]
        sentences = [row for row in annotation_rows if row["record_type"] == "sentence"]
        assert [text[start + row["start"] : start + row["end"]] for row in sentences] == [
            "Ada acts.",
            "Bob waits.",
        ]
        assert [
            (row["start"], row["end"]) for row in canonical_rows if row["record_type"] == "token"
        ] == [(0, 3), (4, 8), (8, 9), (10, 13), (14, 19), (19, 20)]
        assert all(
            row["annotation"]
            == {
                "variant": "partition-item",
                "role": "inventory",
                "collection": "rows",
                "partition_key": annotated["partition_key"],
                "item_key": [
                    {"kind": "text", "text": row["record_type"]},
                    {"kind": "integer", "integer": row["ordinal"]},
                ],
            }
            for row in canonical_rows
        )
        repeated = execute_captured_kernel_demand(kernel, demand_id)
        assert repeated.receipt_count == 0


@pytest.mark.gpu
@pytest.mark.provider_evidence
def test_actual_hanlp_declaration_binds_the_historical_canonical_input(
    semantic_bare_engine, native_settings, tmp_path, monkeypatch
):
    from corpus_structure.semantic.constructions.retained_declarations import DECLARATION_FAMILY

    text = "The mean is 2."
    target = "text.declaration_syntax/source-native"
    namespace = "https://corpus-structure.dev/semantic/"
    with _private_source(
        semantic_bare_engine, native_settings, tmp_path, monkeypatch, text
    ) as source:
        kernel = admit_current_target(
            source, _recipe(tmp_path / "recipe", declaration=True), tmp_path / "target"
        )
        retained, original, products, _ = produce_source_reports(source, kernel, target, text=text)
        (hanlp,) = selected_for_source(
            kernel, products, namespace + "data-operation-hanlp/DdoHanlpInventory", original
        )
        (syntax,) = selected_for_source(
            kernel,
            products,
            namespace + "data-operation-constructions/DdoDeclarationSyntaxProduct",
            original,
        )
        assert hanlp.body["outcome"] == "complete"
        assert any(row["family"] == DECLARATION_FAMILY for row in syntax.body["coverage"])
        repeated = execute_captured_kernel_demand(kernel, retained["demand_id"])
        assert repeated.receipt_count == 0
