"""Current structural source/ref semantics and original source correspondence.

These pure cases grant no native support or provider qualification. Native publication
and genuine upstream predicate production retain their separate acceptance obligations.
"""

import copy
from dataclasses import asdict
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace

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
from semantic.test_data_product_admission_programs import product_connection as product_connection


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
    operations = {operation.semantic_id: operation for operation in model.operations}
    assert set(operations) == {
        "structure.compare/declared",
        "structure.condition_qualification/declared",
        "text.formal_evidence/source-native",
    }
    assert all(implementation.complete for implementation in model.implementation_slices)
    for name in ("structure.compare/declared", "structure.condition_qualification/declared"):
        operation = operations[name]
        identity = python_port_identity(model, sources, name, schema=bundle)
        assert identity.recipe
        assert operation.consumer_selection is not None
        assert operation.dependencies == ()
        assert len(operation.output_witnesses) == (4 if name == "structure.compare/declared" else 2)

    (formal,) = (
        role for role in operations["structure.compare/declared"].roles if role.name == "formal"
    )
    assert formal.minimum == 0 and formal.presence == "optional"
    assert set(formal.required_rules) == {
        "text.formal_evidence/examined-scope",
        "text.formal_evidence/lexical-inventory-links",
        "text.formal_evidence/literal-source-geometry",
        "text.formal_evidence/member-local-addresses",
        "text.formal_evidence/inventory-topology",
        "text.formal_evidence/occurrence-origin",
        "text.formal_evidence/symbolic-inventory-positions",
        "text.formal_evidence/numeric-normalization",
    }
    assert {rule.checker_operation for rule in model.rules if rule.id in formal.required_rules} == {
        "text.formal_evidence/source-native"
    }
    condition = model.operation("structure.condition_qualification/declared")
    (attachment,) = condition.reference_targets
    assert (attachment.path, attachment.input_role, attachment.variant) == (
        "/condition_qualification/attachment",
        "report",
        "member",
    )


def test_selected_condition_attachment_keeps_original_binding_separate_from_current_support():
    from corpus_structure.semantic.data_operation_values import semantic_value
    from corpus_structure.semantic.data_product_reference import SemanticReference
    from corpus_structure.semantic.live_reference_resolution import (
        require_selected_output_reference,
    )

    operation = "structure.condition_qualification/declared"
    path = "/condition_qualification/attachment"
    target = {
        "output_role": "result",
        "path": path,
        "input_role": "report",
        "variant": "member",
        "input_kind": "predicate-inspection",
    }
    body = {"candidate_type": "contribution", "semantic_type": "structural.predicate_qualification"}
    maps = {
        "ops.data_derivation": {"episode": {"release_id": "producer-release"}},
        "sem.data_operation_definition": {
            ("producer-release", operation): {"support_contract": {"reference_targets": [target]}},
        },
        "kb.data_product": {"original": {"project_id": "project", "kind_contract": "kind:report"}},
        "kb.data_product_member": {("original", "qualifier"): {"body": semantic_value(body)}},
        "kb.data_product_partition": {},
        "sem.data_kind_contract": {"kind:report": {"kind": target["input_kind"]}},
    }
    original = {"role": "report", "product_id": "original", "position": 0, "multiplicity": 1}
    use = {
        "demand_id": "report-demand",
        "fate": "fulfilled",
        "derivation_id": "episode",
        "selection": {"inputs": [original]},
    }
    maps["ops.demand_use"] = {"use": use}
    selected = SimpleNamespace(
        operation_id=operation, derivation_id="episode", use_id="use", output={"role": "result"}
    )

    def original_edges(relation, **fields):
        assert relation == "ops.data_derivation_input"
        assert fields == {"derivation_id": "episode", "role": "report"}
        return (original,)

    scope = SimpleNamespace(
        cut=SimpleNamespace(record={"project_id": "project", "demand_id": "issuer-demand"}),
        index=SimpleNamespace(
            mapping=lambda relation, fields: maps[relation],
            rows_for=original_edges,
        ),
    )
    reference = SemanticReference.member("report", "qualifier")
    assert require_selected_output_reference(scope, selected, reference, path=path) == body
    use["selection"]["inputs"] = [{**original, "product_id": "equal-content-replacement"}]
    with pytest.raises(ValueError, match="unavailable in the exact selected use"):
        require_selected_output_reference(scope, selected, reference, path=path)


def test_selected_reference_resolves_only_one_exact_declared_occurrence():
    from corpus_structure.semantic.data_operation_values import semantic_value
    from corpus_structure.semantic.data_product_reference import SemanticReference
    from corpus_structure.semantic.live_reference_resolution import (
        require_selected_output_reference,
    )

    def pin(product, member, position):
        return {
            "role": "reports",
            "product_id": product,
            "member_id": member,
            "position": position,
            "multiplicity": 1,
        }

    left = pin("left", "left-member", 0)
    right = pin("right", "right-member", 1)
    body = {"location": {"key": "selected"}, "content": "original right member"}
    products = {row["product_id"]: {"project_id": "project"} for row in (left, right)}
    members = {
        ("left", "left-member"): {"kind_contract": "member-kind", "body": {"invalid": "hidden"}},
        ("right", "right-member"): {"kind_contract": "member-kind", "body": semantic_value(body)},
    }
    path = "/report"
    target = {
        "output_role": "result",
        "path": path,
        "input_role": "reports",
        "variant": "member",
        "input_kind": "report-member",
        "occurrence_field": "/location/key",
    }
    inputs = [right, {**left, "multiplicity": 2}]
    maps = {
        "ops.demand_use": {
            "use": {
                "fate": "fulfilled",
                "derivation_id": "episode",
                "selection": {"inputs": inputs},
            },
        },
        "ops.data_derivation": {"episode": {"release_id": "release"}},
        "sem.data_operation_definition": {
            ("release", "report"): {"support_contract": {"reference_targets": [target]}},
        },
        "kb.data_product": products,
        "kb.data_product_member": members,
        "kb.data_product_partition": {},
        "sem.data_kind_contract": {"member-kind": {"kind": target["input_kind"]}},
    }

    def original_edges(relation, **fields):
        assert relation == "ops.data_derivation_input"
        assert fields == {"derivation_id": "episode", "role": "reports"}
        return right, left

    scope = SimpleNamespace(
        cut=SimpleNamespace(record={"project_id": "project"}),
        index=SimpleNamespace(
            mapping=lambda relation, _: maps[relation],
            rows_for=original_edges,
        ),
    )
    selected = SimpleNamespace(
        operation_id="report", derivation_id="episode", use_id="use", output={"role": "result"}
    )
    reference = SemanticReference.member("reports", "right-member", occurrence="selected")
    assert require_selected_output_reference(scope, selected, reference, path=path) == body

    inputs[0] = {**right, "product_id": "equal-content-substitute"}
    with pytest.raises(ValueError, match="unavailable in the exact selected use"):
        require_selected_output_reference(scope, selected, reference, path=path)

    inputs[:] = [right, left]
    members["left", "left-member"]["body"] = semantic_value({"location": {"key": "selected"}})
    with pytest.raises(ValueError, match="exactly one producing input occurrence"):
        require_selected_output_reference(scope, selected, reference, path=path)

    members["left", "left-member"]["body"] = semantic_value({"location": {}})
    with pytest.raises(ValueError, match="lacks its declared occurrence"):
        require_selected_output_reference(scope, selected, reference, path=path)


def test_native_condition_target_requires_the_actual_bound_report_member(product_connection):
    from sqlalchemy import bindparam, text
    from sqlalchemy.dialects.postgresql import JSONB
    from sqlalchemy.exc import DBAPIError
    from sqlalchemy.schema import CreateTable

    from corpus_structure.semantic.data_completion_settlement_native import (
        completion_settlement_native_programs,
    )
    from corpus_structure.semantic.data_operation_read_native import read_native_programs
    from corpus_structure.semantic.data_operation_reference_native import reference_native_programs
    from corpus_structure.semantic.data_operation_values import semantic_value
    from corpus_structure.semantic.data_product_reference import SemanticReference
    from corpus_structure.semantic.metadata import get_metadata
    from corpus_structure.semantic.native_objects import execute_native_sql
    from semantic.test_data_product_admission_programs import product_packet, realize

    model, _, _ = compiled()
    operation = model.operation("structure.condition_qualification/declared")
    (target,) = operation.reference_targets
    conn = product_connection
    metadata = get_metadata()
    kinds = metadata.tables["sem.data_kind_contract"]
    conn.execute(
        kinds.update().where(kinds.c.kind_contract == "container").values(kind=target.input_kind)
    )
    member_id = "contribution:source-contribution:" + "1" * 64
    context, product = product_packet((member_id,))
    parent = realize(conn, context, product)
    conn.execute(
        CreateTable(metadata.tables["ops.data_request"], include_foreign_key_constraints=[])
    )
    conn.exec_driver_sql(
        "CREATE TABLE sem.data_operation_definition "
        "(release_id text, operation_id text, support_contract jsonb)"
    )
    programs = (
        *completion_settlement_native_programs(metadata),
        *(item.routine for item in read_native_programs(metadata)),
        *reference_native_programs(metadata),
    )
    for name in (
        "ddo_witness_path",
        "ddo_witness_records",
        "ddo_binding_body_access",
        "ddo_assert_output_references",
    ):
        execute_native_sql(
            conn, next(program for program in programs if program.name == name).render()
        )
    conn.execute(
        text(
            "INSERT INTO sem.data_operation_definition VALUES ('release', :operation, :contract)"
        ).bindparams(bindparam("contract", type_=JSONB())),
        {"operation": operation.semantic_id, "contract": {"reference_targets": [asdict(target)]}},
    )
    request = {
        "project_id": context["project_id"],
        "release_id": "release",
        "operation_id": operation.semantic_id,
        "binding": {"inputs": [{"role": "report", "product_id": parent}]},
    }

    def check(reference):
        body = semantic_value({"condition_qualification": {"attachment": reference.member_value()}})
        conn.execute(
            text(
                "SELECT ops.ddo_assert_output_references("
                "jsonb_populate_record(NULL::ops.data_request,:request),:completion)"
            ).bindparams(
                bindparam("request", type_=JSONB()), bindparam("completion", type_=JSONB())
            ),
            {
                "request": request,
                "completion": {"outputs": [{"role": "result", "product": {"body": body}}]},
            },
        )

    check(SemanticReference.member("report", member_id))
    with pytest.raises(DBAPIError, match="does not resolve address"), conn.begin_nested():
        check(SemanticReference.member("report", "contribution:source-contribution:" + "2" * 64))


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
        subject_definition="original-source-view",
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
            subject_definition="original-source-view",
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
    for _passage, source, ref in zip(passages, sources, refs, strict=True):
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
                            "scope": "actual-primary-block",
                        },
                    },
                    {
                        "contribution_id": "frame",
                        "pin": pin,
                        "component": {
                            "kind": "predicate_frame",
                            "scope": "actual-primary-block",
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
            subject_definition=source.subject_definition,
            support_references=(),
        )
        for source in sources
    )
    report_members = tuple(
        BoundRoleMember(
            ref.product_id,
            ref.kind_contract,
            ref.subject,
            source.original_source,
            b"null",
            b"{}",
            (),
            b"{}",
            subject_definition=source.subject_definition,
            support_references=(),
        )
        for ref, source in zip(refs, sources, strict=True)
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
            "subject_definition": member.subject_definition,
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
        "formal": (),
    }
    outputs = {"result": (current.model_dump(mode="json"),)}
    validate_output_witnesses(model.operation("structure.compare/declared"), outputs, selected)
    forged = copy.deepcopy(outputs)
    forged["result"][0]["sources_input"][1]["original_source"] = "original:A"
    with pytest.raises(ValueError, match="no complete selected input"):
        validate_output_witnesses(model.operation("structure.compare/declared"), forged, selected)
