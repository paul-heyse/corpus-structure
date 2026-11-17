"""Authentic native custody for explicitly authored domain controls and literal readings."""

from dataclasses import replace

import pytest
from evaluate.declared_record_native_support import (
    PROJECT,
    ROOT,
    authored,
    current_record_policy_journey,
    project_context,
    request,
)

from semantic.record_publication_native_support import RichPublication
from semantic.rich_domain_preservation_support import NS


def toy_recipe(directory):
    """Compose the existing authoring route with the actual toy qualifier and rules."""
    import yaml

    from corpus_structure.semantic.composed import (
        data_operation_dependencies,
        read_data_operation_inputs,
    )
    from corpus_structure.semantic.math_context import acquire_analysis_context_profile
    from corpus_structure.semantic.primary_operations import combine_primary_sources
    from corpus_structure.semantic.record_policy_authority import record_policy_kind_declarations
    from corpus_structure.semantic.rich_invocations import rich_knowledge_operation_sources
    from corpus_structure.semantic.rich_knowledge_sources import (
        rich_knowledge_declarations,
        rich_knowledge_schema_inputs,
        rich_policy_inputs,
    )
    from corpus_structure.semantic.types import ResolvedDependencies, SourceArtifact, SourceBundle
    from semantic.current_pdf_source_support import current_pdf_recipe
    from semantic.data_operation_kernel_support import CapturedKernelInputs

    original = current_pdf_recipe(directory)
    captured = original.captured_inputs
    assert captured is not None
    acquired = read_data_operation_inputs(captured.dependencies)
    assert acquired is not None and acquired[1] is not None
    declarations, sources = acquired
    assert sources is not None
    toy_schema = yaml.safe_load((ROOT / "domains/toy/semantic.yaml").read_bytes())
    toy_schema["imports"] = ["core"]
    toy = SourceArtifact("toy_semantic", yaml.safe_dump(toy_schema).encode())
    root = SourceArtifact(
        "toy_native_controls",
        f"id: urn:toy-native-controls\nname: toy_native_controls\nimports: [{captured.bundle.root}, toy_semantic]\n".encode(),
    )
    bundle = SourceBundle(root.name, (*captured.bundle.sources, toy, root))
    deps = ResolvedDependencies(
        tuple(
            artifact
            for artifact in captured.dependencies.artifacts
            if not artifact.name.startswith("data-operations/")
        ),
        captured.dependencies.vocabularies,
        captured.dependencies.ontology_sources,
    )
    bundle, deps = rich_knowledge_schema_inputs(
        bundle, deps, qualification_class="ToyQualification", statement_class="ToySourceStatement"
    )
    deps = rich_policy_inputs(
        deps,
        (ROOT / "domains/toy/schema/rules.yaml").read_bytes(),
        (ROOT / "domains/core/schema/rules.yaml").read_bytes(),
        context_profile=acquire_analysis_context_profile(),
    )
    deps = data_operation_dependencies(
        deps,
        (*declarations, record_policy_kind_declarations(), *rich_knowledge_declarations(deps)),
        combine_primary_sources(sources, rich_knowledge_operation_sources()),
    )
    return replace(
        original,
        name="current-toy-domain-controls",
        captured_inputs=CapturedKernelInputs(bundle, deps, captured.profile),
    )


@pytest.fixture
def toy_publication(scenario_seeds, tmp_path, monkeypatch):
    with current_record_policy_journey(
        scenario_seeds, tmp_path, monkeypatch, recipe=toy_recipe(tmp_path)
    ) as journey:
        yield journey


def decimal_source_stream(
    self,
    source,
    *,
    spool_root,
    record_root,
    build_id,
    release_id,
    on_replay,
    check_active,
    text="12.3400",
    **options,
):
    """Controlled Docling output with literal spelling; no PDF recognition accuracy claim."""
    from docling_core.types.doc import DoclingDocument, GroupLabel, TableCell, TableData

    from corpus_structure.ingest.pdf_stream_types import PdfStreamReply
    from corpus_structure.ingest.pdf_streaming import PdfStreamSpool, StreamingPdfResult

    check_active()
    document = DoclingDocument(name="Exact decimal spelling source")
    section = document.add_group(label=GroupLabel.SECTION, name="Measurements")
    document.add_table(
        parent=section,
        data=TableData(
            num_rows=1,
            num_cols=2,
            table_cells=[
                TableCell(
                    text=text,
                    start_row_offset_idx=0,
                    end_row_offset_idx=1,
                    start_col_offset_idx=column,
                    end_col_offset_idx=column + 1,
                )
                for column in range(2)
            ],
        ),
    )
    result = StreamingPdfResult(
        document,
        PdfStreamSpool(spool_root, check_active=check_active),
        "success",
        (),
        self.recipe.to_bytes(),
        (),
    )
    occurrences = result.write_native_occurrence_batches(
        record_root.with_name(record_root.name + "-occurrences"),
        build_id=build_id,
        on_batch=on_replay,
    )
    records = result.write_record_batches(
        record_root,
        build_id=build_id,
        release_id=release_id,
        source_digest=source.digest,
        on_batch=on_replay,
    )
    return PdfStreamReply("success", (), self.recipe.to_bytes(), (), records + occurrences)


def publish_domain(journey, graph, *, inference):
    """Admit the exact authored input before executing the real rich CPU/native chain."""
    from corpus_structure.semantic.data_operation_identity import (
        body_identity,
        contextual_product_identity,
    )
    from corpus_structure.semantic.data_operation_service import execute_data_demand
    from corpus_structure.semantic.data_operation_source_sets import FrozenSourceSet, SourceSetEntry
    from corpus_structure.semantic.data_product_reference import DataProductReference
    from corpus_structure.semantic.rich_knowledge_contracts import (
        DdoRichAdmission,
        DdoRichConsolidation,
    )
    from corpus_structure.semantic.rich_policy_binding import rich_policy_value
    from corpus_structure.serve.interpretation_authoring import author_interpretations

    context = project_context(journey, "rich.consolidate")
    assert graph.context == context
    value = graph.propositions().model_dump(mode="python")
    selector = contextual_product_identity(
        kind=graph.kinds[NS + "DdoRichAuthoredPropositions"],
        context=context,
        body=body_identity(value).key,
    ).key
    pending = request(
        journey,
        ("rich.consolidate", "rich.admit"),
        (context,),
        originals=(
            authored(
                journey,
                inference + ":domain",
                value,
                kind=NS + "DdoRichAuthoredPropositions",
                context=context,
            ),
            authored(
                journey,
                inference + ":policy",
                rich_policy_value(journey.kernel.prepared, journey.kernel.model).model_dump(
                    mode="python"
                ),
                kind=NS + "DdoRichConsolidationPolicy",
                context=context,
            ),
        ),
        source_sets=(
            FrozenSourceSet.unqualified(
                "rich-authored-propositions",
                (
                    SourceSetEntry.from_semantic_source(
                        DataProductReference(selector), context=context
                    ),
                ),
            ),
            *tuple(
                FrozenSourceSet.from_selected(name, ())
                for name in (
                    "rich-proposals",
                    "rich-proposal-contexts",
                    "rich-known-universe",
                    "rich-records",
                    "rich-readings",
                    "rich-policy-authorizations",
                )
            ),
        ),
        inference=inference,
    )
    retained = author_interpretations(
        journey.kernel.purpose("write"), journey.kernel.prepared, request=pending
    )
    assert selector in {item["product_id"] for item in retained["authored_admissions"]}
    execution = execute_data_demand(
        journey.kernel.purpose("write"),
        retained["demand_id"],
        source_root=ROOT,
        admission_engine=journey.kernel.purpose("admit"),
        project_id=PROJECT,
        database_capacity=6,
    )
    assert execution.receipt_count == 2
    cut, products, uses, episodes, _ = journey.selected_products(
        journey.kernel.purpose("read"),
        retained["demand_id"],
        kind=(NS + "DdoRichAdmission", NS + "DdoRichConsolidation"),
    )
    ((product, admission),) = [
        item
        for item in products
        if item[0]["kind_contract"] == graph.kinds[NS + "DdoRichAdmission"]
    ]
    ((private, consolidation),) = [
        item
        for item in products
        if item[0]["kind_contract"] == graph.kinds[NS + "DdoRichConsolidation"]
    ]
    return RichPublication(
        journey,
        retained["demand_id"],
        product,
        DdoRichAdmission.model_validate(admission),
        private,
        DdoRichConsolidation.model_validate(consolidation),
        cut,
        uses,
        episodes,
    )
