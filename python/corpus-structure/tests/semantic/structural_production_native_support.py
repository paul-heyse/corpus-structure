"""Actual source/sentence/construction/structural producers for protected admissions.

Docling source decoding is controlled by the existing source fixture. The sentence
provider and production structural kernels execute normally; these are specific
functional cases, not a population or universal linguistic accuracy claim.
"""

from dataclasses import replace

from semantic.current_pdf_source_support import PROJECT, ROOT, current_pdf_recipe
from semantic.data_operation_kernel_support import split_captured_operations
from semantic.structural_admission_native_support import Product, execute

NAMED = "structure.definition_named_components/declared"
PREDICATES = "structure.predicate_evidence/declared"
CONDITION = "structure.condition_qualification/declared"


def recipe(directory):
    from corpus_structure.evaluate.declared_structural_admission import (
        structural_reference_kind_declarations,
    )
    from corpus_structure.ingest.sentences import SentenceConfig
    from corpus_structure.semantic.characterization_ports import construction_operation_sources
    from corpus_structure.semantic.composed import (
        data_operation_dependencies,
    )
    from corpus_structure.semantic.construction_products import load_construction_options
    from corpus_structure.semantic.declared_structural_admission import (
        structural_admission_kind_declarations,
        structural_admission_sources,
    )
    from corpus_structure.semantic.declared_structural_calls import (
        structural_operation_declarations,
        structural_operation_sources,
    )
    from corpus_structure.semantic.definition_component_products import (
        definition_component_inputs,
        definition_component_operation_sources,
    )
    from corpus_structure.semantic.predicate_products import predicate_operation_sources
    from corpus_structure.semantic.primary_operations import combine_primary_sources
    from corpus_structure.semantic.types import ResolvedDependencies, SourceArtifact
    from semantic.data_operation_kernel_support import CapturedKernelInputs

    original = current_pdf_recipe(directory)
    captured = original.captured_inputs
    assert captured is not None
    base_dependencies, declarations, sources = split_captured_operations(captured)
    deps = ResolvedDependencies(
        (
            *base_dependencies.artifacts,
            SourceArtifact(
                "operation/model-observation.json",
                (
                    ROOT
                    / "python/corpus-structure/src/corpus_structure/methods/model_observation.json"
                ).read_bytes(),
            ),
        ),
        base_dependencies.vocabularies,
        base_dependencies.ontology_sources,
    )
    sources = combine_primary_sources(
        sources,
        construction_operation_sources(
            sentence_configuration=SentenceConfig(exclude=("ner",)),
            construction_options=load_construction_options(ROOT / "domains/statistics"),
        ),
        predicate_operation_sources(),
        definition_component_operation_sources(),
        structural_operation_sources(),
        structural_admission_sources(),
    )
    deps = data_operation_dependencies(
        deps,
        (
            *declarations,
            structural_operation_declarations(),
            structural_reference_kind_declarations(),
            structural_admission_kind_declarations(),
        ),
        sources,
    )
    return replace(
        original,
        name="current-protected-structural-production",
        captured_inputs=CapturedKernelInputs(
            definition_component_inputs(captured.bundle), deps, captured.profile
        ),
    )


def produce_source_reports(source, kernel, target, *, text, discovered_entries=None):
    """One source-discovery demand owns genuine source and primary producer uses."""
    from corpus_structure.semantic.demand_results import read_demand_result
    from corpus_structure.semantic.selected_support import SelectedReadReference
    from semantic.current_pdf_source_support import current_consumer_request

    pending = current_consumer_request(
        source, kernel, (target,), discover=True, discovered_entries=discovered_entries
    )
    retained, execution = execute(kernel, pending)
    assert execution.receipt_count > 0
    with kernel.purpose("read").begin() as connection:
        page = read_demand_result(connection, retained["demand_id"], project_id=PROJECT, limit=1000)
    read = SelectedReadReference.from_cut(page.cut)
    products = tuple(Product(row, row["body"], read) for row in page.members())
    contract = kernel.identities[
        "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
        "kind",
    ]
    originals = [
        item
        for item in products
        if item.row["kind_contract"] == contract
        and item.body["text"] == text
        and item.body["source"]["section_pointer"] == "#/groups/0"
        and item.body["source"]["membership"] == "descendants"
    ]
    assert len(originals) == 1, [
        (
            item.row["kind_contract"],
            item.body.get("source", {}).get("section_pointer"),
            item.body.get("text", "")[:80],
        )
        for item in products
        if isinstance(item.body, dict)
    ]
    (original,) = originals
    return retained, original, products, pending


def source_pin(product):
    """Only returned native header/source coordinates supply the source address."""
    from corpus_structure.semantic.data_operation_json import json_bytes
    from corpus_structure.semantic.data_operation_model import json_context_meaning
    from corpus_structure.semantic.declared_structural_references import DeclaredStructuralSource
    from corpus_structure.semantic.identity import canonical_bytes

    row, body = product.row, product.body
    coordinate = body["source"]
    return DeclaredStructuralSource(
        source=canonical_bytes([row["product_id"], row["member_id"]]).decode(),
        source_product=row["product_id"],
        source_member=row["member_id"],
        kind_contract=row["kind_contract"],
        project_id=PROJECT,
        subject=row["subject"],
        subject_definition=row["subject_definition"],
        original_source=row["original_source"],
        analyzed_scope_meaning=json_context_meaning(json_bytes(row["analyzed_scope"])).decode(),
        document=coordinate["document"],
        projection_digest=coordinate["projection"],
        section_pointer=coordinate["section_pointer"],
        membership=coordinate["membership"],
    ).model_dump(mode="json", exclude_none=True)


def selected_for_source(kernel, products, kind, original):
    contract = kernel.identities[kind, "kind"]
    return tuple(
        item
        for item in products
        if item.row["kind_contract"] == contract
        and item.row["subject"] == original.row["subject"]
        and item.row["original_source"] == original.row["original_source"]
        and item.row["analyzed_scope"] == original.row["analyzed_scope"]
    )


def publish_statement(kernel, report, expected, *, inference, component_id=None):
    """Actual protected authorship and command completion, never a fabricated receipt."""
    from semantic.structural_admission_native_support import ISSUER, request, selected
    from semantic.structural_reference_native_support import original_passes

    originals, passes = original_passes(
        kernel, report, expected, component_id=component_id, inference=inference
    )
    variant = {
        "qualified_comparison": "comparison",
        "condition_qualification": "condition",
        "definition_components": "definition",
    }[report.body["kind"]]
    pending = request(
        kernel,
        (ISSUER,),
        report.context,
        originals=originals,
        admission_report=report,
        admission_variant=variant,
        inference=inference + ":issue",
    )
    retained, result = execute(kernel, pending, purpose="evaluate", author=True)
    assert result.receipt_count >= 1
    (admission,) = selected(
        kernel,
        retained["demand_id"],
        kind="urn:corpus:structural-admission:DdoStructuralAdmission",
        purpose="evaluate",
    )
    return retained, admission, originals, passes


def read_statement(kernel, demand, report, admission, *, max_graph_bytes=None):
    from corpus_structure.serve.structural_products import (
        SelectedStructuralAdmissionBinding,
        SelectedStructuralRequest,
        inspect_selected_structures,
    )

    pending = SelectedStructuralRequest(
        demand_id=demand,
        project_id=PROJECT,
        roots=(report.root,),
        admissions=(
            SelectedStructuralAdmissionBinding(report=report.root, admission=admission.root),
        ),
        **({"max_graph_bytes": max_graph_bytes} if max_graph_bytes is not None else {}),
    )
    with kernel.purpose("read").begin() as connection:
        page = inspect_selected_structures(connection, pending)
    return pending, page


def assert_native_transport_parity(kernel, native_settings, pending, page, directory):
    """Installed CLI and actual stdio MCP read the same pinned native cut."""
    import os
    import subprocess
    import sys
    from pathlib import Path

    import anyio
    from fastmcp import Client
    from fastmcp.client.transports import StdioTransport

    from corpus_structure.semantic.data_operation_json import (
        finite_json_bytes,
        finite_result_bytes,
        json_bytes,
    )
    from semantic.companion_export_native_support import read_settings

    settings = read_settings(native_settings, kernel.engine)
    database = settings.database
    env = os.environ | {
        "CORPUS_DATABASE__URL": database.url,
        "CORPUS_DATABASE__READER_URL": database.reader_url or "",
        "CORPUS_RUNTIME__DEFAULT_PROJECT": PROJECT,
    }
    pinned = pending.model_copy(
        update=dict(
            read_id=page["cut"]["read_id"],
            expected_cut=page["cut_id"],
            implementation=page["implementation"],
        )
    )
    path = directory / "selected-condition.json"
    path.write_bytes(json_bytes(pinned.model_dump(mode="python")))
    command = str(Path(sys.executable).with_name("ci"))
    reply = subprocess.run(
        [command, "structure", "list", str(path), "--json"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        check=True,
        timeout=120,
    )
    assert reply.stdout == json_bytes(page) + b"\n", "CLI changed the selected structural page"

    async def inspect():
        transport = StdioTransport(
            command=command,
            args=["mcp", "serve", "--project", PROJECT, "--demand", pending.demand_id],
            cwd=str(ROOT),
            env=env,
            keep_alive=False,
            log_file=directory / "condition-stdio.log",
        )
        async with Client(transport, timeout=120) as client:
            response = await client.call_tool(
                "inspect_structures", {"request": pinned.model_dump(mode="json")}
            )
            assert not response.is_error and response.structured_content is not None
            assert finite_json_bytes(response.structured_content["result"]) == finite_result_bytes(
                page
            ), "MCP changed the selected structural page"

    anyio.run(inspect)
