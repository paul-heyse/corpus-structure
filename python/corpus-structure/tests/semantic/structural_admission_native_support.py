"""Real selected structural transport over a deliberately controlled finite inventory."""

from dataclasses import dataclass
from typing import Any, Literal

from corpus_structure.semantic.data_operation_json import json_bytes, json_loads
from corpus_structure.semantic.data_operation_model import SubjectContext, json_context_meaning
from corpus_structure.semantic.declared_structural_references import (
    DeclaredProductRef,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.selected_support import SelectedReadReference
from semantic.current_pdf_source_support import PROJECT, current_pdf_recipe
from semantic.data_operation_kernel_support import (
    CapturedKernelInputs,
    KernelRecipe,
    execute_captured_kernel_demand,
    split_captured_operations,
)
from semantic.structural_native_fixture import OPERATION, TEXT, operation_sources

COMPARE = "structure.compare/declared"
ISSUER = "structure.admit"
DOSSIER = "structure.dossier/declared"


def recipe(directory):
    from corpus_structure.evaluate.declared_structural_admission import (
        structural_reference_kind_declarations,
    )
    from corpus_structure.semantic.composed import (
        data_operation_dependencies,
    )
    from corpus_structure.semantic.declared_structural_admission import (
        structural_admission_kind_declarations,
        structural_admission_sources,
    )
    from corpus_structure.semantic.declared_structural_calls import (
        structural_inputs,
        structural_operation_declarations,
        structural_operation_sources,
    )
    from corpus_structure.semantic.dossier_products import dossier_inputs, dossier_operation_sources
    from corpus_structure.semantic.primary_operations import combine_primary_sources

    original = current_pdf_recipe(directory)
    captured = original.captured_inputs
    assert captured is not None
    base_dependencies, declared, sources = split_captured_operations(captured)
    sources = combine_primary_sources(
        sources,
        operation_sources(),
        structural_operation_sources(),
        structural_admission_sources(),
        dossier_operation_sources(),
    )
    dependencies = data_operation_dependencies(
        base_dependencies,
        (
            *declared,
            structural_operation_declarations(),
            structural_admission_kind_declarations(),
            structural_reference_kind_declarations(),
        ),
        sources,
    )
    return KernelRecipe(
        "current-structural-admission",
        "",
        None,
        "",
        project_id=None,
        execution_profile="source-native",
        captured_inputs=CapturedKernelInputs(
            dossier_inputs(structural_inputs(captured.bundle)), dependencies, captured.profile
        ),
    )


@dataclass(frozen=True)
class Product:
    row: dict
    body: dict
    read: SelectedReadReference

    @property
    def context(self):
        row = self.row
        return SubjectContext(
            PROJECT,
            row["subject"],
            row["original_source"],
            json_bytes(row["analyzed_scope"]),
            subject_definition=row["subject_definition"],
        )

    @property
    def reference(self):
        row = self.row
        return DeclaredProductRef(
            product_id=row["product_id"],
            member_id=row["member_id"],
            kind_contract=row["kind_contract"],
            project_id=PROJECT,
            subject=row["subject"],
            subject_definition=row["subject_definition"],
            original_source=row["original_source"],
            analyzed_scope_meaning=json_context_meaning(json_bytes(row["analyzed_scope"])).decode(),
        )

    def entry(self):
        from corpus_structure.semantic.data_operation_source_sets import SelectedSourceSetEntry

        return SelectedSourceSetEntry.from_selected_header(self.row, self.read)

    @property
    def root(self):
        from corpus_structure.serve.selected_structural import SelectedStructuralRoot

        return SelectedStructuralRoot(
            product_id=self.row["product_id"],
            member_id=self.row["member_id"],
            use_id=self.row["use_id"],
            derivation_id=self.row["derivation_id"],
        )


def selected(kernel, demand, *, kind, purpose="read"):
    from corpus_structure.semantic.demand_results import read_demand_result

    contract = kernel.identities[kind, "kind"]
    with kernel.purpose(purpose).begin() as connection:
        page = read_demand_result(connection, demand, project_id=PROJECT, limit=1000)
    read = SelectedReadReference.from_cut(page.cut)
    return tuple(
        Product(row, row["body"], read)
        for row in page.members()
        if row["kind_contract"] == contract
    )


def request(
    kernel,
    targets,
    context,
    *,
    originals=(),
    source_sets=(),
    selections=(),
    inference,
    admission_report=None,
    admission_variant="comparison",
):
    from corpus_structure.semantic.data_operation_service import (
        DemandOperationSelection,
        DemandOriginalSelection,
        DemandRoot,
        NativeDemandRequest,
    )
    from corpus_structure.semantic.data_operation_source_sets import (
        FrozenSourceSet,
        source_sets_record,
    )

    if ISSUER in targets:
        if admission_report is None:
            raise ValueError("structural issuer fixture requires the actual selected report")
        source_sets = (
            *source_sets,
            FrozenSourceSet.from_selected(
                "structural-admission-report", (admission_report.entry(),)
            ),
        )
        selections = (
            *selections,
            DemandOperationSelection(
                operation=ISSUER, choices={"report_variant": admission_variant}
            ),
        )

    return NativeDemandRequest(
        project_id=PROJECT,
        release_id=kernel.prepared.release_id,
        runtime_id=kernel.runtime,
        roots=(
            DemandRoot(
                subject=context.subject,
                original_source=context.original_source,
                analyzed_scope=json_loads(context.analyzed_scope),
            ),
        ),
        targets=targets,
        original_sources={
            item.name: DemandOriginalSelection.model_validate(item.record()) for item in originals
        },
        source_sets=source_sets_record(source_sets),
        selections=selections,
        inference=inference,
        execution_profile="source-native",
    )


def execute(
    kernel,
    pending,
    *,
    purpose: Literal["write", "evaluate"] = "write",
    author=False,
    selection_name: str | None = None,
) -> tuple[dict[str, Any], Any]:
    from corpus_structure.semantic.data_operation_service import (
        advance_demand_selection,
        create_native_demand,
    )
    from corpus_structure.serve.interpretation_authoring import author_interpretations

    retained: dict[str, Any]
    if author:
        retained = dict(
            author_interpretations(kernel.purpose(purpose), kernel.prepared, request=pending)
        )
    else:
        with kernel.purpose(purpose).begin() as connection:
            retained = dict(create_native_demand(connection, pending, prepared=kernel.prepared))
    if selection_name is not None:
        with kernel.purpose("admit").begin() as connection:
            advance_demand_selection(
                connection,
                pending.project_id,
                selection_name,
                retained["demand_id"],
                expected_demand_id=None,
                expected_generation=0,
            )
    result = execute_captured_kernel_demand(kernel, retained["demand_id"], purpose=purpose)
    return retained, result


def authored(
    kernel,
    context,
    name,
    body,
    *,
    author,
    kind="urn:corpus:structural-admission:protected:DdoStructuralReferencePass",
):
    from corpus_structure.semantic.data_operation_support import authored_fact_selection

    return authored_fact_selection(
        name,
        body,
        kind_contract=kernel.identities[kind, "kind"],
        context=context,
        author=author,
        selection_id="native-structural-control:" + name,
    )


def expected_statement(left, right):
    """Independent fixed-case meaning: actual addresses, known literal role extents.

    No comparison output or production statement lowerer supplies these judgments.
    Missing formal/quantity/basis evidence stays unresolved, never equivalent.
    """

    def citation(product):
        pin = product.body["source_pin"]
        return dict(source=pin, start=0, end=9, text=TEXT, scope="selected")

    citations = (citation(left), citation(right))
    dimensions = []
    for dimension in (
        "actor",
        "action",
        "object",
        "modality",
        "condition",
        "threshold_unit",
        "exception",
        "order_dependency",
        "parent",
        "version",
    ):
        groups = []
        for evidence in citations:
            if dimension in {"actor", "action"}:
                start, end, text = (0, 3, "Ada") if dimension == "actor" else (4, 8, "acts")
                span = {**evidence, "start": start, "end": end, "text": text}
                groups.append(
                    dict(
                        state="present",
                        grouping="singleton",
                        members=[
                            dict(
                                dimension=dimension,
                                lexical_value=text,
                                evidence=[evidence],
                                spans=[span],
                            )
                        ],
                        witnesses=[],
                    )
                )
            else:
                groups.append(
                    dict(
                        state="unresolved" if dimension == "threshold_unit" else "absent",
                        members=[],
                        witnesses=[],
                    )
                )
        dimensions.append(
            dict(
                dimension=dimension,
                outcome="same_lexical_value" if dimension in {"actor", "action"} else "unknown",
                typed_outcome="unknown",
                assumptions=[],
                grouping_outcome="unresolved",
                member_comparisons=[],
                left_group=groups[0],
                right_group=groups[1],
            )
        )
    return dict(
        version="structural-public-statement-3",
        kind="qualified_comparison",
        scope="selected",
        inventory_id="independent-native-structural-inputs",
        input_policy_id="exact-native-structural-control-1",
        coverage_limits=[
            "Only retained predicate coverage is used; unavailable formal characterization remains unresolved."
        ],
        exclusions=[],
        comparison=dict(
            left=citations[0],
            right=citations[1],
            dimensions=dimensions,
            equivalence="not_asserted",
            identity_standing="not_asserted",
            applicability="unestablished",
        ),
    )


def source_products(source):
    from corpus_structure.semantic.demand_results import read_demand_result

    contract = source.kernel.identities[
        "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
        "kind",
    ]
    with source.kernel.purpose("read").begin() as connection:
        page = read_demand_result(connection, source.demand_id, project_id=PROJECT, limit=1000)
    read = SelectedReadReference.from_cut(page.cut)
    products = tuple(
        Product(row, row["body"], read)
        for row in page.members()
        if row["kind_contract"] == contract and row["body"]["text"] == TEXT
    )
    # Select the two explicit original sections, never a newest/body-equivalent alias.
    selected_sources = tuple(
        product
        for product in products
        if product.body["source"]["section_pointer"] in {"#/groups/0", "#/groups/1"}
    )
    assert len(selected_sources) == 2
    return tuple(
        sorted(selected_sources, key=lambda product: product.body["source"]["section_pointer"])
    )


def build_inventory(kernel, original):
    from corpus_structure.semantic.data_operation_source_sets import FrozenSourceSet

    pending = request(
        kernel,
        (OPERATION,),
        original.context,
        source_sets=(
            FrozenSourceSet.from_selected("fixture-structural-source", (original.entry(),)),
        ),
        inference="actual-controlled-source-inventory:" + original.row["member_id"],
    )
    retained, result = execute(kernel, pending)
    assert result.receipt_count == 1
    (predicates,) = selected(
        kernel,
        retained["demand_id"],
        kind="https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoPredicateInspectionReport",
    )
    (components,) = selected(
        kernel,
        retained["demand_id"],
        kind="urn:corpus:structural:DeclaredDefinitionComponentsReport",
    )
    assert predicates.body["standing"] == "private_uncalibrated_candidates"
    assert predicates.body["diagnostics_json"].find("finite-Ada-acts-1") >= 0
    return predicates, components


def compare_selection(originals, predicates):
    from corpus_structure.semantic.data_operation_service import DemandOperationSelection

    readings = tuple(
        next(
            packet["body"]["contribution_id"]
            for packet in report.body["members"]
            if packet["body"].get("component", {}).get("kind") == "predicate_reading"
        )
        for report in predicates
    )
    return DemandOperationSelection(
        operation=COMPARE,
        parameters=dict(
            question="Compare exact source-qualified controlled roles",
            scope="selected",
            inventory_id="independent-native-structural-inputs",
            policy_id="exact-native-structural-control-1",
            left_start=0,
            left_end=9,
            right_start=0,
            right_end=9,
            left_passage_id="left",
            right_passage_id="right",
            left_reading=readings[0],
            right_reading=readings[1],
            left_source_reference=canonical_bytes(
                [originals[0].row["product_id"], originals[0].row["member_id"]]
            ).decode(),
            right_source_reference=canonical_bytes(
                [originals[1].row["product_id"], originals[1].row["member_id"]]
            ).decode(),
            left_report_reference=canonical_bytes([predicates[0].row["product_id"], None]).decode(),
            right_report_reference=canonical_bytes(
                [predicates[1].row["product_id"], None]
            ).decode(),
        ),
    )


def comparison_sources(originals, predicates):
    from corpus_structure.semantic.data_operation_source_sets import FrozenSourceSet

    return (
        FrozenSourceSet.from_selected(
            "structural-sources", tuple(item.entry() for item in originals)
        ),
        FrozenSourceSet.from_selected(
            "structural-reports", tuple(item.entry() for item in predicates)
        ),
        FrozenSourceSet.from_selected("structural-formal", ()),
    )
