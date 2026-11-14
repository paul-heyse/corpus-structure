"""Current structural source/ref semantics and original source correspondence.

These pure cases grant no native support or provider qualification. Native publication
and genuine upstream predicate production retain their separate acceptance obligations.
"""

import copy
from functools import lru_cache
from pathlib import Path

import pytest

from corpus_structure.methods.structural_products import produce_structural_comparison
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_model import BoundRoleMember
from corpus_structure.semantic.data_operation_output_witnesses import validate_output_witnesses
from corpus_structure.semantic.data_operation_ports import python_port_identity
from corpus_structure.semantic.declared_structural_calls import (
    structural_inputs,
    structural_operation_declarations,
    structural_operation_sources,
)
from corpus_structure.semantic.declared_structural_references import (
    DeclaredContributionRef,
    DeclaredStructuralSource,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.structural_products import (
    DIMENSIONS,
    DeclaredComparisonReport,
    DeclaredStructuralInput,
    DeclaredStructuralInputPin,
    StructuralPassage,
)
from corpus_structure.semantic.types import SourceArtifact, SourceBundle


@lru_cache(maxsize=1)
def compiled():
    root = Path(__file__).parents[2] / "src/corpus_structure/model/semantic"
    bundle = structural_inputs(
        SourceBundle("core", (SourceArtifact("core", (root / "core.yaml").read_bytes()),))
    )
    sources = structural_operation_sources()
    model = compile_data_operations(bundle, (structural_operation_declarations(),), sources)
    return model, bundle, sources


def test_structural_current_producers_have_closed_original_callable_and_nominal_witnesses():
    model, bundle, sources = compiled()
    assert {operation.semantic_id for operation in model.operations} == {
        "structure.compare/declared",
        "structure.condition_qualification/declared",
    }
    assert all(implementation.complete for implementation in model.implementation_slices)
    for operation in model.operations:
        identity = python_port_identity(model, sources, operation.semantic_id, schema=bundle)
        assert identity.recipe
        assert operation.consumer_selection is not None
        assert operation.capabilities.prepared_factory is not None
        assert operation.dependencies == ()
        assert len(operation.output_witnesses) == 3


def exact_source(document, product, subject):
    return DeclaredStructuralSource(
        format="declared-native-source-v1",
        source=canonical_bytes([product, None]).decode(),
        source_product=product,
        kind_contract="kind:source",
        subject=subject,
        document=document,
        projection_digest="a" * 64,
        section_pointer="#/texts/0",
        membership="direct",
        project_id="p",
        original_source=document,
        analyzed_scope_meaning='["null"]',
    )


def test_original_comparison_kernel_retains_declared_sources_and_native_ref_witnesses():
    model, _, _ = compiled()
    sources = (
        exact_source("original:A", "source:A", "subject:A"),
        exact_source("original:B", "source:B", "subject:B"),
    )
    passages = tuple(
        StructuralPassage(
            passage_id=side,
            source_ref=source.identity,
            start=0,
            end=9,
            text="Ada acts.",
            scope="selected",
        )
        for side, source in zip(("left", "right"), sources, strict=True)
    )
    refs = tuple(
        DeclaredContributionRef(
            product_id="report:" + side,
            contribution_id="source-contribution:" + digit * 64,
            member_id=None,
            kind_contract="kind:inspection",
            project_id="p",
            subject=source.subject,
            original_source=source.original_source,
            analyzed_scope_meaning='["null"]',
        )
        for side, digit, source in zip(("left", "right"), ("b", "c"), sources, strict=True)
    )
    inputs = DeclaredStructuralInput(
        question="Compare exact retained predicate roles",
        scope="selected",
        inventory_id="authored-bounds",
        policy_id="explicit",
        sources=sources,
        passages=passages,
        dependencies=tuple(ref.contribution_id for ref in refs),
    )
    # Independent original-kernel fixture: these are already selected semantic rows,
    # not a claim of genuine native admission or a synthetic provider response.
    retained = []
    for passage, source, ref in zip(passages, sources, refs, strict=True):
        pin = source.model_dump(mode="json", exclude_none=True)
        retained.append(
            {
                "contributions": [
                    {
                        "contribution_id": ref.contribution_id,
                        "pin": pin,
                        "component": {
                            "kind": "predicate_reading",
                            "question_version": "6",
                            "frame": "frame",
                            "scope": passage.passage_id,
                        },
                    },
                    {
                        "contribution_id": "frame",
                        "pin": pin,
                        "component": {
                            "kind": "predicate_frame",
                            "scope": passage.passage_id,
                            "frame_members": [
                                {
                                    "role": "predicate",
                                    "contribution": "action",
                                    "outcome": "complete",
                                    "extents": [{"start": 0, "end": 9}],
                                }
                            ],
                        },
                    },
                ]
            }
        )
    value = produce_structural_comparison(
        inputs,
        left_id="left",
        right_id="right",
        left_reading=refs[0],
        right_reading=refs[1],
        left_retained=retained[0],
        right_retained=retained[1],
        primary_layers=None,
    )
    source_members = tuple(
        BoundRoleMember(
            source.source_product,
            source.kind_contract,
            source.subject,
            source.original_source,
            b"null",
            b"{}",
            (),
            b"{}",
        )
        for source in sources
    )
    report_members = tuple(
        BoundRoleMember(
            ref.product_id,
            ref.kind_contract,
            ref.subject,
            ref.original_source,
            b"null",
            b"{}",
            (),
            b"{}",
        )
        for ref in refs
    )
    current = DeclaredComparisonReport.model_validate(
        {
            **value.model_dump(mode="python"),
            "sources_input": tuple(
                DeclaredStructuralInputPin.from_bound(member, project="p")
                for member in source_members
            ),
            "reports_input": tuple(
                DeclaredStructuralInputPin.from_bound(member, project="p")
                for member in report_members
            ),
        }
    )
    assert current.comparison.left_reading.product_id == "report:left"
    assert current.comparison.left_reading.contribution_id == refs[0].contribution_id
    assert {row.dimension for row in current.comparison.dimensions} == set(DIMENSIONS)
    assert current.comparison.equivalence == current.comparison.identity_standing == "not_asserted"
    assert current.comparison.applicability == "unestablished"

    def header(member, body):
        return {
            "product": member.product,
            "member": member.member,
            "kind_contract": member.kind_contract,
            "project_id": "p",
            "subject": member.subject,
            "original_source": member.original_source,
            "analyzed_scope": None,
            "body": body,
        }

    selected = {
        "sources": tuple(
            header(
                member,
                {
                    "source": {
                        "document": source.document,
                        "projection": source.projection_digest,
                        "section_pointer": source.section_pointer,
                        "membership": source.membership,
                    }
                },
            )
            for member, source in zip(source_members, sources, strict=True)
        ),
        "reports": tuple(header(member, {}) for member in report_members),
    }
    outputs = {"result": (current.model_dump(mode="json"),)}
    validate_output_witnesses(model.operation("structure.compare/declared"), outputs, selected)
    forged = copy.deepcopy(outputs)
    forged["result"][0]["inputs"]["sources"][1]["original_source"] = "original:A"
    with pytest.raises(ValueError, match="no complete selected input"):
        validate_output_witnesses(model.operation("structure.compare/declared"), forged, selected)
