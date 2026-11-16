"""Actual selected sentence/native custody and independent whole-block spaCy questions.

Only source document decoding is controlled. The sentence provider, native claims,
receipts, protected C snapshot and selected reads are genuine. These literal cases
check transport/scoring; they establish no population-level linguistic accuracy.
"""

from dataclasses import replace
from typing import Any, cast

import pytest

from corpus_structure.evaluate.selected_references import (
    ReferenceApplicability,
    SelectedReferenceEvaluationRequest,
    author_selected_references,
    evaluate_selected_references,
)
from corpus_structure.semantic.composed import data_operation_dependencies, read_data_operation_inputs
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_model import SubjectContext, json_context_meaning
from corpus_structure.semantic.data_operation_service import execute_data_demand
from corpus_structure.semantic.data_operation_support import authored_fact_selection
from corpus_structure.semantic.demand_results import read_demand_result
from corpus_structure.semantic.observations import source_value
from corpus_structure.semantic.primary_operations import combine_primary_sources
from corpus_structure.semantic.selected_reference_sources import (
    selected_reference_inputs,
    selected_reference_operation_sources,
)
from corpus_structure.semantic.sentence_products import sentence_operation_sources, sentence_product_inputs
from corpus_structure.semantic.types import ResolvedDependencies
from semantic.current_pdf_source_support import (
    PROJECT, ROOT, admit_current_target, current_pdf_recipe,
    current_pdf_source_factory as current_pdf_source_factory,
)
from semantic.data_operation_kernel_support import CapturedKernelInputs
from semantic.structural_admission_native_support import request
from semantic.structural_production_native_support import produce_source_reports

TEXT = "Ada acts."
SENTENCES = "segment.sentences/source-native"
NAMESPACE = "https://corpus-structure.dev/semantic/data-operation-sentences/"


def scoring_recipe(directory):
    original = current_pdf_recipe(directory)
    captured = original.captured_inputs
    assert captured is not None
    inputs = read_data_operation_inputs(captured.dependencies)
    assert inputs is not None and inputs[1] is not None
    declarations, sources = inputs
    assert sources is not None
    dependencies = ResolvedDependencies(
        tuple(item for item in captured.dependencies.artifacts
              if not item.name.startswith("data-operations/")),
        captured.dependencies.vocabularies, captured.dependencies.ontology_sources,
    )
    return replace(original, name="selected-native-scoring", captured_inputs=CapturedKernelInputs(
        selected_reference_inputs(sentence_product_inputs(captured.bundle)),
        data_operation_dependencies(dependencies, declarations, combine_primary_sources(
            sources, sentence_operation_sources(), selected_reference_operation_sources(),
        )), captured.profile,
    ))


def test_native_whole_block_questions_keep_exact_custody_and_missing_populations(
    current_pdf_source_factory, tmp_path,
):
    with current_pdf_source_factory((("text", TEXT, TEXT, None),)) as source:
        kernel = admit_current_target(source, scoring_recipe(tmp_path / "recipe"), tmp_path / "target")
        retained, original, products, _ = produce_source_reports(source, kernel, SENTENCES, text=TEXT)
        (annotations,) = [item for item in products
                          if item.row["kind_contract"] == kernel.identities[NAMESPACE + "DdoSourceAnnotations", "kind"]
                          and item.body["source"] == original.body["source"]]
        (block,) = [packet for packet in annotations.body["members"]
                    if packet["body"]["record_type"] == "native_block"]
        assert (block["body"]["start"], block["body"]["end"]) == (0, 9)
        with kernel.purpose("evaluate").begin() as connection:
            selected = read_demand_result(connection, retained["demand_id"], project_id=PROJECT, limit=1000)
        source_member = dict(
            product_id=original.row["product_id"], member_id=original.row["member_id"],
            **{name: original.row[name] for name in
               ("subject", "subject_definition", "original_source", "kind_contract")},
            analyzed_scope_meaning=json_context_meaning(json_bytes(original.row["analyzed_scope"])).decode(),
        )
        gold = dict(kind="tokenization", text=TEXT,
                    words=["Ada", "acts", "."], spaces=[True, False, False])
        scope = dict(projection=original.body["source"]["projection"], start=0, end=9)
        questions = {
            "tokens": gold,
            "uninspected": {**gold, "inspected": False},
            "categories": {**gold, "kind": "categories", "labels": ["positive", "negative"],
                           "cats": {"positive": 1.0, "negative": 0.0}, "multi_label": False},
        }
        body = dict(
            reference_name="independent-whole-block", author="independent native question author",
            pass_kind="C", direction="output_first",
            source_demand_id=retained["demand_id"], source_read_id=selected.cut.record["read_id"],
            source_cut_id=selected.cut.identity, source_cut=source_value(selected.cut.record),
            source_release_id=kernel.prepared.release_id, source_runtime_id=kernel.runtime,
            source_members=[source_member],
            output_members=[dict(product_id=annotations.row["product_id"], member_id=block["member_id"])],
            cases=[dict(case_id=name, opportunity_id="literal-block", question=name,
                        source_members=[source_member], matcher="spacy_native",
                        expected=source_value({**scope, "reference": native}), judgment="supported")
                   for name, native in questions.items()],
            retained_correspondence=source_value(None),
        )
        context = SubjectContext(PROJECT, "reference:native-block", source.document_key, b"{}",
                                 subject_definition="independent-reference")
        kind = kernel.identities[
            "https://corpus-structure.dev/semantic/data-operation-assessment/DdoSelectedReference", "kind"]
        reference = authored_fact_selection("independent-reference", body, kind_contract=kind,
                                           context=context, author=body["author"],
                                           selection_id="reference:native-block")
        pending = request(kernel, ("reference.snapshot/declared",), context,
                          originals=(reference,), inference="independent-native-scoring")
        authored = author_selected_references(kernel.purpose("evaluate"), kernel.prepared, request=pending)
        result = execute_data_demand(
            kernel.purpose("evaluate"), authored["demand_id"], project_id=PROJECT,
            source_root=ROOT, admission_engine=kernel.purpose("admit"), purpose="evaluate",
            database_capacity=4,
        )
        assert result.receipt_count == 1
        with kernel.purpose("evaluate").begin() as connection:
            snapshot = read_demand_result(connection, authored["demand_id"], project_id=PROJECT)
            (protected,) = snapshot.members()
            comparison = SelectedReferenceEvaluationRequest(
                project_id=PROJECT, reference_demand_id=authored["demand_id"],
                reference_product_id=protected["product_id"],
                prediction_demand_id=retained["demand_id"],
                prediction_product_id=annotations.row["product_id"],
                prediction_read_id=selected.cut.record["read_id"], prediction_cut_id=selected.cut.identity,
                assignments={name: block["member_id"] for name in questions},
                applicability=ReferenceApplicability(
                    reference_source_release_id=kernel.prepared.release_id,
                    reference_source_cut_id=selected.cut.identity,
                    prediction_release_id=kernel.prepared.release_id,
                    original_source=source.document_key, projection=scope["projection"],
                    selectors=tuple(original.body["selectors"]),
                    basis="the exact same independently selected original block",
                ),
            )
            report = cast(dict[str, Any], evaluate_selected_references(connection, comparison))
            cases = {case["case_id"]: case["native"] for case in report["cases"]}
            assert cases["tokens"]["scores"]["token_f"] == 1.0
            assert cases["tokens"]["coverage"]["reference"]["eligible"] == 3
            assert cases["tokens"]["prediction_reference"]["member_id"] == block["member_id"]
            assert cases["uninspected"]["status"] == "uninspected"
            assert cases["uninspected"]["scores"] == {}
            assert cases["categories"]["status"] == "unavailable"
            assert cases["categories"]["scores"] == {}
            assert report["opportunity_denominator"] == 1
            token = next(packet for packet in annotations.body["members"]
                         if packet["body"]["record_type"] == "native_token")
            # Output-first binding refuses substituting a token before any block expansion.
            with pytest.raises(ValueError, match="frozen prediction population"):
                evaluate_selected_references(connection, comparison.model_copy(update={
                    "assignments": {name: token["member_id"] for name in questions},
                }))
