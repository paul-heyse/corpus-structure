"""Current scoped production supplies an exact nomination to its artifact consumer.

The PDF decoder is controlled. Native source acquisition, linguistic and formal producers,
scoped execution, publication, artifact consumption and authenticated reopen are real.
"""

import pytest

from corpus_structure.semantic.data_operation_service import DemandOperationSelection
from corpus_structure.semantic.data_operation_source_sets import (
    FrozenSourceSet,
    SelectedSourceSetEntry,
)
from corpus_structure.semantic.declared_candidate_products import candidate_member_values
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.source_products import selected_source_ranges
from corpus_structure.serve.demand_export import export_demand_result, verified_demand_export
from corpus_structure.serve.structural_products import (
    SelectedStructuralRequest,
    inspect_selected_structures,
)
from semantic.current_artifact_support import ARTIFACT, artifact_recipe
from semantic.current_pdf_source_support import (
    PROJECT,
    _current_pdf_source,
    admit_current_target,
    current_consumer_request,
)
from semantic.structural_admission_native_support import execute, request, selected

SCOPED = "structure.scoped_relations/declared"
SCOPED_KIND = "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoScopedRelationsReport"
SOURCE_KIND = "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource"
CONSTRUCTION_KIND = "https://corpus-structure.dev/semantic/data-operation-constructions/DdoPrimaryConstructionProduct"


def scoped_artifact_content(*, formulas=False):
    from docling_core.types.doc import (
        BoundingBox,
        DocItemLabel,
        DoclingDocument,
        GroupLabel,
        ProvenanceItem,
        Size,
        TableCell,
        TableData,
    )
    from pdf_controlled_support import ControlledPdfContent

    document = DoclingDocument(name="Scoped nomination source")
    document.add_page(page_no=1, size=Size(width=200, height=300))
    group = document.add_group(label=GroupLabel.SECTION, name="Exact scoped table")
    literal = "See Table 2.1."
    document.add_text(
        label=DocItemLabel.TEXT,
        text=literal,
        orig=literal,
        parent=group,
        prov=ProvenanceItem(
            page_no=1, bbox=BoundingBox(l=10, t=20, r=150, b=40), charspan=(0, len(literal))
        ),
    )
    table = document.add_table(
        parent=group,
        data=TableData(
            num_rows=1,
            num_cols=1,
            table_cells=[
                TableCell(
                    text="1.0000000000000000000000000001",
                    start_row_offset_idx=0,
                    end_row_offset_idx=1,
                    start_col_offset_idx=0,
                    end_col_offset_idx=1,
                )
            ],
        ),
        prov=ProvenanceItem(page_no=1, bbox=BoundingBox(l=10, t=60, r=150, b=140), charspan=(0, 0)),
    )
    literal = "Table 2.1 Exact values"
    caption = document.add_text(
        label=DocItemLabel.CAPTION,
        text=literal,
        orig=literal,
        parent=table,
        prov=ProvenanceItem(
            page_no=1, bbox=BoundingBox(l=10, t=45, r=150, b=60), charspan=(0, len(literal))
        ),
    )
    table.captions.append(caption.get_ref())
    outcomes = []
    if formulas:
        from corpus_structure.ingest.pdf_health import FormulaOutcome

        document.add_text(
            label=DocItemLabel.TEXT, text="Let x be count.", orig="Let x be count.", parent=group
        )
        formula = document.add_text(
            label=DocItemLabel.FORMULA, text="x+x=2", orig="x+x=2", parent=group
        )
        outcomes.append(FormulaOutcome(formula.self_ref, "succeeded"))
    return ControlledPdfContent.from_document(document, formula_outcomes=tuple(outcomes))


def scoped_math_artifact_recipe(directory):
    from dataclasses import replace

    from corpus_structure.semantic.composed import data_operation_dependencies
    from corpus_structure.semantic.construction_products import load_construction_options
    from corpus_structure.semantic.declared_math_analysis import (
        math_analysis_declarations,
        math_analysis_operation_sources,
    )
    from corpus_structure.semantic.declared_math_products import (
        DeclaredMathOptions,
        math_operation_declarations,
        math_operation_sources,
    )
    from corpus_structure.semantic.primary_operations import combine_primary_sources
    from semantic.current_artifact_support import ROOT
    from semantic.data_operation_kernel_support import (
        CapturedKernelInputs,
        split_captured_operations,
    )

    base = artifact_recipe(directory)
    captured = base.captured_inputs
    assert captured is not None
    dependencies, declarations, sources = split_captured_operations(captured)
    options = DeclaredMathOptions(
        math_scope_binders=load_construction_options(ROOT / "domains/statistics").math_scope_binders
    )
    sources = combine_primary_sources(
        sources, math_operation_sources(options), math_analysis_operation_sources(options)
    )
    dependencies = data_operation_dependencies(
        dependencies,
        (*declarations, math_operation_declarations(), math_analysis_declarations()),
        sources,
    )
    return replace(
        base, captured_inputs=CapturedKernelInputs(captured.bundle, dependencies, captured.profile)
    )


def test_current_scoped_relations_publish_nomination_and_reopen_exact_artifact_consumer(
    scenario_seeds, tmp_path
):
    with _current_pdf_source(
        scenario_seeds,
        tmp_path,
        content=scoped_artifact_content(formulas=True),
        sections=("#/groups/0",),
        math_context=True,
    ) as source:
        kernel = admit_current_target(
            source, scoped_math_artifact_recipe(tmp_path / "recipe"), tmp_path / "consumer"
        )
        pending = current_consumer_request(
            source,
            kernel,
            (SCOPED, "analyze.math/lexical", "resolve.symbol_scope/declared"),
            discover=True,
        )
        from corpus_structure.orchestrate.source_operation import _default_profile_source_sets

        graph = kernel.model.projection_graph(
            "selected-dependencies",
            selected_dependencies=tuple(
                (selection.operation, selection.selected_dependencies)
                for selection in pending.selections
            ),
        )
        requested = set(pending.targets) | {
            operation
            for selection in pending.discovery
            for operation in (selection.producer, selection.target)
        }
        closure = requested.union(*(graph.closure((operation,)) for operation in requested))
        pending = pending.model_copy(
            update={
                "source_sets": {
                    **_default_profile_source_sets(kernel.model, closure),
                    **pending.source_sets,
                }
            }
        )
        selections = {value.operation: value for value in pending.selections}
        selections[SCOPED] = DemandOperationSelection(
            operation=SCOPED, parameters={"source_work": "controlled-book"}
        )
        pending = pending.model_copy(update={"selections": tuple(selections.values())})
        scoped_demand, execution = execute(kernel, pending)
        assert execution.receipt_count > 0
        (scoped,) = selected(kernel, scoped_demand["demand_id"], kind=SCOPED_KIND)
        (original,) = selected(kernel, scoped_demand["demand_id"], kind=SOURCE_KIND)
        (construction,) = selected(kernel, scoped_demand["demand_id"], kind=CONSTRUCTION_KIND)
        contributions = candidate_member_values(scoped.body, candidate_type="contribution")
        assert any(
            source_python(row.get("value", {})).get("role") == "formula_symbol"
            for row in contributions
        )
        assert any(
            row.get("component", {}).get("attachment_kind") == "declares" for row in contributions
        )
        (nomination,) = [
            row
            for row in contributions
            if row.get("component", {}).get("attachment_kind") == "artifact_reference_target"
        ]
        assert nomination["pin"]["source_product"] == original.row["product_id"]
        by_id = {row["contribution_id"]: row for row in contributions}
        mention, caption = [source_python(by_id[key]["value"]) for key in nomination["members"]]
        assert mention["text"] == "Table 2.1" and caption["text"] == "Table 2.1"
        assert mention["source_pointer"] != caption["source_pointer"]
        source_entry = original.entry()
        source_reference = canonical_bytes(
            [original.row["product_id"], original.row["member_id"]]
        ).decode()
        assert (
            source_reference
            == canonical_bytes([source_entry.entry.product, source_entry.entry.member]).decode()
        )
        assert scoped.body["source_pin"]["source"] == source_reference
        assert nomination["pin"]["source"] == source_reference
        assert all(by_id[key]["pin"]["source"] == source_reference for key in nomination["members"])
        assert original.body["text"][mention["start"] : mention["end"]] == "Table 2.1"
        assert original.body["text"][caption["start"] : caption["end"]] == "Table 2.1"
        assert selected_source_ranges(original.body, original.body["selectors"]) == (
            (0, len(original.body["text"])),
        )
        occurrence = "scoped:actual-report"
        report_entry = SelectedSourceSetEntry.from_selected_header(
            scoped.row, scoped.read, occurrence_label=occurrence
        )
        assert report_entry.entry.occurrence_label == occurrence
        parameters = dict(
            selections=[
                dict(
                    source_reference=source_reference,
                    passage_id="controlled-book",
                    start=0,
                    end=len(original.body["text"]),
                    scope="controlled scoped source",
                    source_work="controlled-book",
                    mapping_provenance="explicit native trial source",
                )
            ],
            nomination_selections=[
                dict(report_occurrence=occurrence, contribution_id=nomination["contribution_id"])
            ],
            title_threshold=70.5,
            policy=dict(prior=0.1, code_m=0.9, code_u=0.01, title_m=0.8, title_u=0.05),
        )
        consumer = request(
            kernel,
            (ARTIFACT,),
            original.context,
            source_sets=(
                FrozenSourceSet.from_selected("artifact-sources", (source_entry,)),
                FrozenSourceSet.from_selected("artifact-constructions", (construction.entry(),)),
                FrozenSourceSet.from_selected("artifact-nominations", (report_entry,)),
            ),
            selections=(DemandOperationSelection(operation=ARTIFACT, parameters=parameters),),
            inference="complete-scoped-relational-trial",
        )
        artifact_demand, _execution = execute(kernel, consumer)
        (artifact,) = selected(
            kernel,
            artifact_demand["demand_id"],
            kind="urn:corpus:structural:DeclaredArtifactReport",
        )
        assert artifact.body["inputs"]["dependencies"] == [nomination["contribution_id"]]
        product = artifact.body["artifact_identity"]
        assert product["policy"] == parameters["policy"]
        (external,) = product["external_nominations"]
        assert external["relationship"] == dict(
            variant="member",
            role="nominations",
            occurrence=occurrence,
            member_id="contribution:" + nomination["contribution_id"],
        )
        assert {endpoint["origin_source"] for endpoint in external["endpoints"]} == {
            parameters["selections"][0]["source_reference"]
        }
        with kernel.purpose("read").begin() as connection:
            observed = inspect_selected_structures(
                connection,
                SelectedStructuralRequest(
                    project_id=PROJECT,
                    demand_id=artifact_demand["demand_id"],
                    roots=(artifact.root,),
                    max_graph_bytes=32 * 1024**2,
                ),
            )
            exported = export_demand_result(
                connection,
                artifact_demand["demand_id"],
                project_id=PROJECT,
                destination=tmp_path / "scoped-artifact-export",
                format="parquet",
                scope={"product_ids": [artifact.row["product_id"]]},
            )
        assert observed["reports"][0]["availability"] == "observed"
        assert canonical_bytes(
            observed["reports"][0]["report"]["artifact_identity"]
        ) == canonical_bytes(product)
        with verified_demand_export(
            tmp_path / "scoped-artifact-export", manifest_digest=exported.manifest_digest
        ) as (_, _, _, index):
            products = index.mapping("kb.data_product", ("id",))
            assert {
                scoped.row["product_id"],
                original.row["product_id"],
                artifact.row["product_id"],
            } <= set(products)
            actual_inputs = [
                row
                for row in index.rows("ops.data_derivation_input")
                if row["derivation_id"] == artifact.row["derivation_id"]
                and row["role"] == "nominations"
            ]
            assert (
                len(actual_inputs) == 1
                and actual_inputs[0]["product_id"] == scoped.row["product_id"]
            )


@pytest.mark.provider_evidence
@pytest.mark.gpu
@pytest.mark.prerequisite("pdf_resume_assets")
def test_genuine_selected_pdf_scoped_report_publishes_and_reopens(scenario_seeds, tmp_path):
    """One retained page traverses real Standard capture and the installed scoped producer."""
    from io import BytesIO

    import pypdfium2 as pdfium

    from corpus_structure.ingest.pdf_producer_contract import standard_pdf_contract
    from corpus_structure.semantic.data_operation_values import decode_semantic_value
    from corpus_structure.semantic.demand_results import read_selected_answer
    from semantic.actual_pdf_resume_support import ORIGINAL, prepared_pdf_resume_assets
    from semantic.current_pdf_source_support import (
        CurrentPdfSource,
        _capture_source,
        current_pdf_recipe,
    )
    from semantic.data_operation_kernel_support import Kernel

    recipe, assets = prepared_pdf_resume_assets()
    with pdfium.PdfDocument(ORIGINAL) as retained, pdfium.PdfDocument.new() as panel:
        panel.import_pages(retained, [120])  # Physical page 121 preserves a nonempty math source.
        output = BytesIO()
        panel.save(output)
    capture_recipe = current_pdf_recipe(
        tmp_path, capture_profile=(recipe, assets, standard_pdf_contract())
    )
    with scenario_seeds.build_for_consumer(capture_recipe, tmp_path) as clone:
        stage = clone.stage
        capture = Kernel(clone.admin, stage.preparation, stage.identities, capture_recipe, clone)
        demand, document, original = _capture_source(
            capture,
            tmp_path,
            (),
            original=output.getvalue(),
            source_uri="retained-grinstead-snell-page-121.pdf",
        )
        source = CurrentPdfSource(capture, demand, document, original, ())
        kernel = admit_current_target(
            source, artifact_recipe(tmp_path / "recipe"), tmp_path / "consumer"
        )
        pending = current_consumer_request(source, kernel, (SCOPED,), discover=True)
        scoped_demand, execution = execute(kernel, pending)
        assert execution.receipt_count > 0
        (report,) = selected(kernel, scoped_demand["demand_id"], kind=SCOPED_KIND)
        (selected_source,) = selected(kernel, scoped_demand["demand_id"], kind=SOURCE_KIND)
        assert report.body["source_pin"]["source_product"] == selected_source.row["product_id"]
        with kernel.purpose("read").begin() as connection:
            answer = read_selected_answer(
                connection,
                "read_selected_outputs",
                scoped_demand["demand_id"],
                project_id=PROJECT,
                scope={"operation_id": SCOPED},
                use_id=report.row["use_id"],
                product_id=report.row["product_id"],
                body=True,
            )
            assert canonical_bytes(
                decode_semantic_value(answer["rows"][0]["meaning_body"])
            ) == canonical_bytes(report.body)
            exported = export_demand_result(
                connection,
                scoped_demand["demand_id"],
                project_id=PROJECT,
                destination=tmp_path / "genuine-scoped-export",
                format="parquet",
                scope={"product_ids": [report.row["product_id"]]},
            )
        with verified_demand_export(
            tmp_path / "genuine-scoped-export", manifest_digest=exported.manifest_digest
        ) as (_, _, _, index):
            assert {report.row["product_id"], selected_source.row["product_id"]} <= set(
                index.mapping("kb.data_product", ("id",))
            )
