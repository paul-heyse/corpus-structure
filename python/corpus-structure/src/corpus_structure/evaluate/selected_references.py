"""Protected reference authorship and comparison across explicit native selections.

Original source selection, independently authored answers, prediction selection and
comparison recipe remain distinct. No retained frame is translated or regraded by
address inference, and this reader grants no public knowledge admission.
"""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict, Field

from corpus_structure.semantic.data_operation_identity import decode_semantic_value
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_model import json_context_meaning
from corpus_structure.semantic.demand_results import CutSelection, selected_record_index
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.native_definition_projection import read_native_definition_projection

_REFERENCE = "https://corpus-structure.dev/semantic/data-operation-assessment/DdoSelectedReference"
_SNAPSHOT = (
    "https://corpus-structure.dev/semantic/data-operation-assessment/DdoSelectedReferenceSnapshot"
)



def _body(index, product, member=None):
    row = (
        index.mapping("kb.data_product", ("id",)).get(product)
        if member is None
        else index.mapping("kb.data_product_member", ("product_id", "member_id")).get(
            (product, member)
        )
    )
    if row is None:
        raise ValueError("reference address is outside the selected native closure")
    return row, decode_semantic_value(row["canonical_body" if member is None else "body"])


def _reference_invariants(body):
    source_cut = CutSelection(json_bytes(source_python(body["source_cut"])))
    pins = source_cut.record
    if (
        source_cut.identity,
        pins["demand_id"],
        pins["read_id"],
        pins["release_id"],
        pins["runtime_id"],
    ) != (
        body["source_cut_id"],
        body["source_demand_id"],
        body["source_read_id"],
        body["source_release_id"],
        body["source_runtime_id"],
    ):
        raise ValueError("reference question differs from its immutable original source cut")
    if body["direction"] == "source_first" and body["output_members"]:
        raise ValueError("source-first reference cannot freeze exposed prediction outputs")
    if body["direction"] == "output_first" and not body["output_members"]:
        raise ValueError("output-first reference requires its exact frozen output population")
    cases = [case["case_id"] for case in body["cases"]]
    if len(set(cases)) != len(cases):
        raise ValueError("independent reference repeats a case identity")
    sources = [(row["product_id"], row.get("member_id")) for row in body["source_members"]]
    if len(set(sources)) != len(sources):
        raise ValueError("independent reference repeats a source identity")
    source_keys = {json_bytes(row) for row in body["source_members"]}
    for case in body["cases"]:
        if not {json_bytes(row) for row in case["source_members"]} <= source_keys:
            raise ValueError("reference case cites outside its frozen source population")
        expected = source_python(case["expected"])
        if not isinstance(expected, Mapping):
            raise ValueError("reference matcher requires an explicit object expectation")
        if case["matcher"] == "graph_full":
            if not {"root", "nodes"} <= expected.keys() or "graph_projection" not in case:
                raise ValueError(
                    "graph reference requires its full rooted graph and explicit comparison projection"
                )
            from .characterization_assessment import project_graph

            project_graph(expected, case["graph_projection"])
    if source_python(body["retained_correspondence"]) is not None:
        correspondence = source_python(body["retained_correspondence"])
        if (
            not isinstance(correspondence, dict)
            or not {
                "original_reference",
                "original_grade",
                "target_reference_name",
                "reviewed_by",
                "basis",
            }
            <= correspondence.keys()
            or correspondence["target_reference_name"] != body["reference_name"]
            or not correspondence["basis"]
            or not correspondence["reviewed_by"]
        ):
            raise ValueError(
                "retained reference requires explicit reviewed identity/question correspondence and its original grade"
            )


def _authenticate_reference_sources(connection, body, *, project_id, max_bytes=8388608):
    source_cut = CutSelection(json_bytes(source_python(body["source_cut"])))
    pins = source_cut.record
    if pins["project_id"] != project_id:
        raise ValueError("reference original source belongs to another project")
    with selected_record_index(
        connection,
        body["source_demand_id"],
        project_id=project_id,
        scope=pins["scope"],
        read_id=pins["read_id"],
        expected_cut=source_cut.identity,
        max_bytes=max_bytes,
    ) as (_, index):
        for source in body["source_members"]:
            actual, _ = _body(index, source["product_id"], source.get("member_id"))
            if (
                any(
                    actual[key] != source[key]
                    for key in ("kind_contract", "subject", "subject_definition", "original_source")
                )
                or json_context_meaning(json_bytes(actual["analyzed_scope"])).decode()
                != source["analyzed_scope_meaning"]
            ):
                raise ValueError("reference source member differs from its native source/context")
        for output in body["output_members"]:
            _body(index, output["product_id"], output["member_id"])


def author_selected_references(engine, prepared, *, request):
    """Admit actual protected authored facts after checking their exact source pins."""
    from corpus_structure.semantic.data_operation_identity import decode_semantic_value
    from corpus_structure.serve.interpretation_authoring import author_interpretations

    if request.targets != ("reference.snapshot/declared",):
        raise ValueError("reference authoring requires its dedicated snapshot target")
    contracts = {
        kind["kind_contract"]
        for kind in read_native_definition_projection(prepared)["kinds"]
        if kind["kind"] == _REFERENCE and kind["universe"] == "evaluator"
    }
    if len(contracts) != 1:
        raise ValueError("reference authoring release lacks its protected declared kind")
    for selected in request.original_sources.values():
        reference = selected.reference
        if (
            reference.get("kind") != "authored-fact"
            or reference.get("kind_contract") not in contracts
        ):
            raise ValueError("reference authoring accepts only the protected reference fact kind")
        body = prepared.validate_json(
            "DdoSelectedReference", json_bytes(decode_semantic_value(reference["meaning_body"]))
        ).model_dump(mode="python", exclude_unset=True)
        _reference_invariants(body)
        with engine.begin() as connection:
            _authenticate_reference_sources(connection, body, project_id=request.project_id)
    return author_interpretations(engine, prepared, request=request)


class ReferenceApplicability(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    reference_source_release_id: str
    reference_source_cut_id: str
    prediction_release_id: str
    original_source: str
    projection: str
    selectors: tuple[dict, ...]
    basis: str = Field(min_length=1)


class SelectedReferenceEvaluationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    project_id: str = Field(min_length=1)
    reference_demand_id: str = Field(min_length=1)
    reference_product_id: str = Field(min_length=1)
    prediction_demand_id: str = Field(min_length=1)
    prediction_product_id: str = Field(min_length=1)
    assignments: dict[str, str]
    applicability: ReferenceApplicability
    reference_read_id: str | None = None
    reference_cut_id: str | None = None
    prediction_read_id: str | None = None
    prediction_cut_id: str | None = None
    max_bytes: int = Field(default=8388608, ge=1024, le=67108864)


def evaluate_selected_references(connection, request: SelectedReferenceEvaluationRequest):
    """Compare actual selected primary members against independent protected cases.

    The result is a pinned comparison report, with no linguistic truth claim,
    publication authority or hidden inference. Native reference custody remains
    distinct from this report's operator-managed retention.
    """
    from corpus_structure.semantic.data_product_reference import DataProductReference
    from corpus_structure.semantic.declared_formal_readings import (
        SelectedCharacterizationInventories,
    )
    from corpus_structure.semantic.releases import open_release

    from .characterization_assessment import LayerProjection, _matches, graph_equal

    reference_scope = {"product_ids": [request.reference_product_id]}
    prediction_scope = {"product_ids": [request.prediction_product_id]}
    if request.reference_demand_id == request.prediction_demand_id:
        raise ValueError("reference and prediction require their separate native selections")
    with selected_record_index(
        connection,
        request.reference_demand_id,
        project_id=request.project_id,
        scope=reference_scope,
        read_id=request.reference_read_id,
        expected_cut=request.reference_cut_id,
        max_bytes=request.max_bytes,
    ) as (reference_cut, references):
        reference_row, reference = _body(references, request.reference_product_id)
        prepared = open_release(connection, reference_cut.record["release_id"])
        admitted = {
            kind["kind_contract"]
            for kind in read_native_definition_projection(prepared)["kinds"]
            if kind["kind"] in {_REFERENCE, _SNAPSHOT} and kind["universe"] == "evaluator"
        }
        if reference_row["kind_contract"] not in admitted:
            raise ValueError("selected reference is not a protected declared reference kind")
        prepared.validate_json(
            "DdoSelectedReferenceSnapshot"
            if reference_row["kind_contract"]
            in {
                kind["kind_contract"]
                for kind in read_native_definition_projection(prepared)["kinds"]
                if kind["kind"] == _SNAPSHOT
            }
            else "DdoSelectedReference",
            json_bytes(reference),
        )
        _reference_invariants(reference)
        _authenticate_reference_sources(
            connection, reference, project_id=request.project_id, max_bytes=request.max_bytes
        )
        # Native witnesses bind the complete typed authored value; this read
        # comparison independently checks its captured support and whole body.
        snapshot_contracts = {
            kind["kind_contract"]
            for kind in read_native_definition_projection(prepared)["kinds"]
            if kind["kind"] == _SNAPSHOT
        }
        if reference_row["kind_contract"] in snapshot_contracts:
            episodes = {
                row["derivation_id"]
                for row in references.rows("ops.data_derivation_output")
                if row["product_id"] == request.reference_product_id
            }
            originals = [
                row
                for row in references.rows("ops.data_derivation_input")
                if row["derivation_id"] in episodes and row["role"] == "reference"
            ]
            if len(originals) != 1:
                raise ValueError(
                    "reference snapshot requires its exact independently authored input"
                )
            original = originals[0]
            original_row, original_body = _body(
                references, original["product_id"], original.get("member_id")
            )
            source_contracts = {
                kind["kind_contract"]
                for kind in read_native_definition_projection(prepared)["kinds"]
                if kind["kind"] == _REFERENCE
            }
            admissions = {
                row["id"]
                for row in references.rows("ops.original_source_admission")
                if row["product_id"] == original["product_id"]
                and row["evidence"].get("standing") == "authored"
            }
            if (
                original_row["kind_contract"] not in source_contracts
                or json_bytes(original_body) != json_bytes(reference)
                or not any(
                    row["derivation_id"] == original["derivation_id"]
                    and row["role"] == "reference"
                    and row["admission_id"] in admissions
                    for row in references.rows("ops.data_derivation_original_support")
                )
            ):
                raise ValueError(
                    "reference snapshot differs from its authentic independently authored input"
                )
        with selected_record_index(
            connection,
            request.prediction_demand_id,
            project_id=request.project_id,
            scope=prediction_scope,
            read_id=request.prediction_read_id,
            expected_cut=request.prediction_cut_id,
            max_bytes=request.max_bytes,
        ) as (prediction_cut, predictions):
            _, prediction = _body(predictions, request.prediction_product_id)
            applicability = request.applicability
            if (
                reference["source_release_id"],
                reference["source_cut_id"],
                prediction_cut.record["release_id"],
            ) != (
                applicability.reference_source_release_id,
                applicability.reference_source_cut_id,
                applicability.prediction_release_id,
            ):
                raise ValueError(
                    "reference source release and prediction release require exact reviewed applicability"
                )
            producer_episodes = {
                row["derivation_id"]
                for row in predictions.rows("ops.data_derivation_output")
                if row["product_id"] == request.prediction_product_id
            }
            if not producer_episodes or not any(
                row["derivation_id"] in producer_episodes and row["fate"] == "fulfilled"
                for row in predictions.rows("ops.demand_use")
            ):
                raise ValueError("prediction requires its authentic selected producing episode")
            source = prediction["source"]
            if (
                source["document"] != applicability.original_source
                or source["projection"] != applicability.projection
                or json_bytes(prediction["selectors"]) != json_bytes(list(applicability.selectors))
                or not any(
                    row["original_source"] == source["document"]
                    for row in reference["source_members"]
                )
            ):
                raise ValueError("prediction source is outside the independent reference scope")
            expected_cases = {
                case["case_id"] for case in reference["cases"] if case["judgment"] != "unassessed"
            }
            if not set(request.assignments) <= expected_cases or (
                reference["direction"] == "output_first"
                and set(request.assignments) != expected_cases
            ):
                raise ValueError("assessment assignments differ from the frozen assessed cases")
            if reference["direction"] == "output_first":
                frozen = {
                    (row["product_id"], row["member_id"]) for row in reference["output_members"]
                }
                actual = {
                    (request.prediction_product_id, member)
                    for member in request.assignments.values()
                }
                if actual != frozen:
                    raise ValueError(
                        "output-first assessment differs from its frozen prediction population"
                    )
            products = predictions.mapping("kb.data_product", ("id",))
            inventories = SelectedCharacterizationInventories(products)
            projection = LayerProjection(
                lambda pin: inventories[DataProductReference(pin["product_id"])].payload
            )
            payload = inventories[DataProductReference(request.prediction_product_id)].payload
            collections = {
                row["local_id"]: collection
                for collection in (
                    "terms",
                    "annotations",
                    "memberships",
                    "occurrences",
                    "roles",
                    "choices",
                )
                for row in payload.get(collection, ())
            }
            cases = []
            for case in reference["cases"]:
                member = request.assignments.get(case["case_id"])
                if case["judgment"] == "unassessed":
                    cases.append(
                        dict(
                            case_id=case["case_id"],
                            opportunity_id=case["opportunity_id"],
                            outcome="unassessed",
                        )
                    )
                    continue
                if member is not None and not any(
                    row["original_source"] == source["document"] for row in case["source_members"]
                ):
                    raise ValueError(
                        "prediction assignment cites outside the case's independent source question"
                    )
                if member not in collections:
                    cases.append(
                        dict(
                            case_id=case["case_id"],
                            opportunity_id=case["opportunity_id"],
                            outcome="unavailable",
                            reason="selected prediction member is absent",
                        )
                    )
                    continue
                output = dict(
                    product_id=request.prediction_product_id,
                    member_id=member,
                    collection=collections[member],
                )
                actual = projection.project(output, include_graph=case["matcher"] == "graph_full")
                expected = source_python(case["expected"])
                matched = (
                    graph_equal(actual["graph"], expected, case.get("graph_projection"))
                    if case["matcher"] == "graph_full"
                    else _matches(actual, expected)
                )
                cases.append(
                    dict(
                        case_id=case["case_id"],
                        opportunity_id=case["opportunity_id"],
                        prediction=output,
                        judgment=case["judgment"],
                        outcome="match" if matched else "mismatch",
                    )
                )
            report = dict(
                format="selected-reference-comparison-v1",
                reference=dict(
                    product_id=request.reference_product_id,
                    cut=reference_cut.record,
                    cut_id=reference_cut.identity,
                    source_release_id=reference["source_release_id"],
                    source_cut_id=reference["source_cut_id"],
                ),
                prediction=dict(
                    product_id=request.prediction_product_id,
                    cut=prediction_cut.record,
                    cut_id=prediction_cut.identity,
                ),
                applicability=applicability.model_dump(mode="python"),
                direction=reference["direction"],
                opportunity_denominator=len(
                    {case["opportunity_id"] for case in reference["cases"]}
                ),
                cases=cases,
                quality_claim="declared_cases_only",
                publication_authority=False,
                inference="not_run",
            )
            if source_python(reference["retained_correspondence"]) is not None:
                report["retained_correspondence"] = source_python(
                    reference["retained_correspondence"]
                )
            if len(json_bytes(report)) > request.max_bytes:
                raise ValueError("complete selected reference comparison exceeds max_bytes")
            return report
