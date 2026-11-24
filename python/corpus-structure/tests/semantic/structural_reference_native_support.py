"""Protected A/B/C over actual selected reports; labels remain authored attribution."""

from copy import deepcopy

from corpus_structure.semantic.data_operation_identity import body_identity
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_values import semantic_value
from corpus_structure.semantic.declared_structural_references import DeclaredProductRef
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.structural_admission import POLICIES
from semantic.structural_admission_native_support import ISSUER, PROJECT, authored, request


def original_passes(kernel, report, expected, *, component_id=None, inference):
    """Admit independent original A/B products before authoring C's actual parents."""
    from corpus_structure.evaluate.declared_record_policy import _selected_body
    from corpus_structure.semantic.data_operation_model import json_context_meaning
    from corpus_structure.semantic.demand_results import acquired_selected_relations
    from corpus_structure.serve.interpretation_authoring import author_interpretations

    variant = {
        "qualified_comparison": "comparison",
        "condition_qualification": "condition",
        "definition_components": "definition",
    }[report.body["kind"]]
    frame = dict(
        report=report.reference.model_dump(mode="python"),
        inputs=report.body["inputs"],
        question=report.body["inputs"]["question"],
        case_id="whole",
        operation=report.body["kind"],
        component_id=component_id,
        rubric_version=POLICIES[report.body["kind"]],
        direction="source_first",
        exposed_outputs=[],
    )
    passes = [
        dict(
            version="structural-reference-pass-1",
            frame=deepcopy(frame),
            pass_kind=kind,
            actor=dict(
                principal=inference + ":" + kind,
                session_id=inference + ":session:" + kind,
                basis="authored_attribution",
            ),
            author_assertion=inference + ":" + kind,
            parents=[],
            cases=[
                dict(
                    case_id="whole",
                    facet="public_statement",
                    path=["public_statement"],
                    judgment="supported",
                    expected_meaning_json=canonical_bytes(semantic_value(expected)).decode(),
                    source_passages=[
                        passage["passage_id"] for passage in report.body["inputs"]["passages"]
                    ],
                )
            ],
        )
        for kind in ("A", "B", "C")
    ]
    independent = tuple(
        authored(
            kernel,
            report.context,
            inference + ":pass:" + body["pass_kind"],
            body,
            author=body["author_assertion"],
        )
        for body in passes[:2]
    )
    staged = author_interpretations(
        kernel.purpose("evaluate"),
        kernel.prepared,
        request=request(
            kernel,
            (ISSUER,),
            report.context,
            admission_report=report,
            admission_variant=variant,
            originals=independent,
            inference=inference + ":A-B",
        ),
    )
    parents = []
    with (
        kernel.purpose("evaluate").begin() as connection,
        acquired_selected_relations(
            connection,
            staged["demand_id"],
            project_id=PROJECT,
            scope={"product_ids": [value["product_id"] for value in staged["authored_admissions"]]},
        ) as (_, index),
    ):
        for admitted in staged["authored_admissions"]:
            _, body = _selected_body(index, admitted["product_id"])
            row = next(
                row for row in index.rows("kb.data_product") if row["id"] == admitted["product_id"]
            )
            reference = DeclaredProductRef(
                product_id=row["id"],
                member_id=None,
                kind_contract=row["kind_contract"],
                project_id=PROJECT,
                subject=row["subject"],
                subject_definition=row["subject_definition"],
                original_source=row["original_source"],
                analyzed_scope_meaning=json_context_meaning(
                    json_bytes(row["analyzed_scope"])
                ).decode(),
            )
            parents.append(
                dict(
                    reference=reference.model_dump(mode="python"),
                    body_digest=body_identity(body).key,
                )
            )
    assert len(parents) == 2
    passes[2]["parents"] = parents
    originals = (
        *independent,
        authored(
            kernel,
            report.context,
            inference + ":pass:C",
            passes[2],
            author=passes[2]["author_assertion"],
        ),
    )
    return originals, passes
